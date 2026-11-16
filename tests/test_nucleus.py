#!/usr/bin/env python3
"""Assemble figforth.asm and test every word of the nucleus in the emulator.

    python3 tests/test_nucleus.py

A test puts a thread into RAM (a list of code field addresses and in-line
cells), sets the stacks, points IP at it and lets NEXT run until IP reaches
the end of the thread. Words are named by their Forth names and looked up by
walking the dictionary of the image, so a wrong header fails here too.

rv32emu.py is the RV32EC emulator of the sixforths repository. It stops on
what the CH32V006 would trap on (a misaligned lw / sw, a register above x15,
an instruction the chip does not have) and that fails the test.
"""
import copy, os, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from rv32emu import Emu

M32 = 0xFFFFFFFF
CELL = 4
RAM = 0x20000000
THREAD = RAM + 0x100            # where a test's thread goes
DATA = RAM + 0x800              # scratch memory for the tests

# ---------------------------------------------------------------- build

def build():
    cmd = ["bronzebeard", "-i", ROOT + os.sep,
           "-l", os.path.join(ROOT, "figforth.labels"),
           "-o", os.path.join(ROOT, "figforth.bin"),
           os.path.join(ROOT, "figforth.asm")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("the assembler failed:\n" + r.stdout + r.stderr)
    labels = {}
    for line in open(os.path.join(ROOT, "figforth.labels")):
        name, value = line.split()
        labels[name] = int(value, 16)
    return open(os.path.join(ROOT, "figforth.bin"), "rb").read(), labels

IMAGE, L = build()

def cell(a):
    return int.from_bytes(IMAGE[a:a + 4], "little")

S0 = cell(L["boot_up"] + 3 * CELL)
R0 = cell(L["boot_up"] + 4 * CELL)
UP = cell(L["boot_up"] + 2 * CELL)

# ---------------------------------------------------------------- results

failed = 0
count = 0

def check(what, got, want):
    global failed, count
    count += 1
    if got != want:
        failed += 1
        def show(v):
            if isinstance(v, int) and not isinstance(v, bool):
                return hex(v)
            if isinstance(v, (list, tuple)):
                return "[" + ", ".join(show(x) for x in v) + "]"
            return repr(v)
        print("FAIL %s\n     got  %s\n     want %s" % (what, show(got), show(want)))

# ---------------------------------------------------------------- the dictionary

def walk(image, nfa):
    """Follow the link fields from nfa. Returns [(name, nfa, cfa, length byte)],
    newest word first, and checks the shape of every header on the way."""
    words = []
    while nfa:
        assert nfa % CELL == 0, "name field at %#x is not on a cell boundary" % nfa
        b = image[nfa]
        assert b & 0x80, "length byte at %#x lacks bit 7" % nfa
        n = b & 0x1F
        end = nfa + 1                       # find the last byte of the field
        while not image[end] & 0x80:
            end += 1
        raw = bytes(c & 0x7F for c in image[nfa + 1:end + 1])
        assert len(raw) >= n and (len(raw) + 1) % CELL == 0, "name field at %#x" % nfa
        assert raw[n:] == b" " * (len(raw) - n), "padding of the name at %#x" % nfa
        lfa = end + 1
        link = int.from_bytes(image[lfa:lfa + 4], "little")
        words.append((raw[:n].decode(), nfa, lfa + CELL, b))
        nfa = link
    return words

# The nucleus ends at S->D; the words after it are tested in test_listings.py.
WORDS = walk(IMAGE, L["n_stod"])
CFA = {name: cfa for name, nfa, cfa, b in WORDS}
NFA = {name: nfa for name, nfa, cfa, b in WORDS}

# ---------------------------------------------------------------- running

def poke(e, a, v):
    e.ram[a - RAM:a - RAM + 4] = (v & M32).to_bytes(4, "little")

def peek(e, a):
    return int.from_bytes(e.ram[a - RAM:a - RAM + 4], "little")

def pokes(e, a, data):
    e.ram[a - RAM:a - RAM + len(data)] = data

def run_to(e, stop, max_steps=2_000_000):
    """Step until stop(e) is true. Any fault of the emulator is an error."""
    for _ in range(max_steps):
        if stop(e):
            return
        try:
            e.step()
        except RuntimeError:
            raise AssertionError("emulator fault %r" % (e.fault,))
    raise AssertionError("no end after %d steps, pc = %#x" % (max_steps, e.pc))

def idle(e):
    return e.pc == L["serial_getc1"] and not e.uart_in

def boot():
    e = Emu(IMAGE, b"")
    run_to(e, idle)
    return e

BOOTED = boot()

def thread(e, cells, at=THREAD):
    """Write a thread; a string is a word's name, a number an in-line cell."""
    for i, c in enumerate(cells):
        poke(e, at + CELL * i, CFA[c] if isinstance(c, str) else c)
    return at + CELL * len(cells)

def run(cells, stack=(), rstack=(), setup=None, keys=b""):
    """Run a thread on a copy of the booted machine.
    Returns (data stack, return stack, output, machine), stacks bottom first."""
    e = copy.deepcopy(BOOTED)
    if setup:
        setup(e)
    end = thread(e, cells)
    for n, (reg, top, items) in enumerate(((8, S0, stack), (4, R0, rstack))):
        p = top
        for v in items:
            p -= CELL
            poke(e, p, v)
        e.x[reg] = p
    e.x[9] = THREAD
    e.pc = L["next"]
    e.uart_in = list(keys)
    out0 = len(e.uart_out)
    run_to(e, lambda e: e.pc == L["next"] and e.x[9] == end)
    ds = [peek(e, a) for a in range(S0 - CELL, e.x[8] - CELL, -CELL)]
    rs = [peek(e, a) for a in range(R0 - CELL, e.x[4] - CELL, -CELL)]
    return ds, rs, bytes(e.uart_out[out0:]), e

def stack_of(cells, stack=(), **kw):
    return run(cells, stack, **kw)[0]

def t(what, cells, stack, want, **kw):
    """A word test: the data stack afterwards, and an empty return stack."""
    ds, rs, out, e = run(cells, stack, **kw)
    check(what, ds, [w & M32 for w in want])
    check(what + " (return stack)", rs, [])

def text(s, total=40):
    """Text as WORD leaves it at HERE: a length byte, the characters, blanks."""
    b = bytes([len(s)]) + s.encode()
    return b + b" " * (total - len(b))

# ---------------------------------------------------------------- boot

check("boot message", bytes(BOOTED.uart_out), b"\r\nfig-FORTH RISC-V\r\n")
check("UP after COLD", BOOTED.x[3], UP)
check("the user area holds boot_up",
      [peek(BOOTED, UP + CELL * i) for i in range(11)],
      [cell(L["boot_up"] + CELL * i) for i in range(11)])
check("the return stack at the prompt: QUIT is in QUERY, in EXPECT, in its loop",
      BOOTED.x[4], R0 - 4 * CELL)
check("the body of FORTH is in RAM",
      [peek(BOOTED, RAM), peek(BOOTED, RAM + CELL), peek(BOOTED, RAM + 2 * CELL)],
      [0xA0202081, L["last_nfa"], 0])
check("and the body of EDITOR",
      [peek(BOOTED, RAM + 3 * CELL), peek(BOOTED, RAM + 4 * CELL), peek(BOOTED, RAM + 5 * CELL)],
      [0xA0202081, L["last_enfa"], RAM + 2 * CELL])
check("mtvec", BOOTED.csr.get(0x305), 3)
check("sp", BOOTED.x[2], R0 - 64 * CELL)

# the RAM map: nothing overlaps
tib, msp = cell(L["boot_up"] + 5 * CELL), R0 - 64 * CELL
check("RAM map order", UP + 128 <= tib and tib + 96 <= msp - 24 * CELL and S0 == RAM + 0x2000 - 8 * CELL, True)

# warm start keeps FENCE, DP and VOC-LINK, and puts the rest back
e = copy.deepcopy(BOOTED)
for i in range(11):
    poke(e, UP + CELL * i, 0x11110000 + i)
e.pc = L["origin"] + 4
e.x[8] = e.x[4] = 0
run_to(e, idle)
check("warm start",
      [peek(e, UP + CELL * i) for i in range(11)],
      [cell(L["boot_up"] + CELL * i) for i in range(8)] + [0x11110008, 0x11110009, 0x1111000A])
e = copy.deepcopy(BOOTED)
poke(e, UP + CELL * 9, 0x12345678)
e.pc = L["origin"]
run_to(e, idle)
check("cold start resets DP", peek(e, UP + CELL * 9), RAM + 6 * CELL)

# the trap handler prints mcause and mepc
e = copy.deepcopy(BOOTED)
e.csr[0x342], e.csr[0x341] = 6, 0x1A4
e.pc = L["trap"]
n0 = len(e.uart_out)
run_to(e, lambda e: e.pc == L["trap6"])
check("trap line", bytes(e.uart_out[n0:]), b"T00000006 000001A4 ")
check("vector table", [cell(8), cell(12)], [L["trap"], L["trap"]])
check("the handler is on a cell boundary", L["trap"] % 4, 0)

# ---------------------------------------------------------------- headers

MODEL = ["LIT", "EXECUTE", "BRANCH", "0BRANCH", "(LOOP)", "(+LOOP)", "(DO)", "I",
         "DIGIT", "(FIND)", "ENCLOSE", "EMIT", "KEY", "?TERMINAL", "CR", "CMOVE",
         "U*", "U/", "AND", "OR", "XOR", "SP@", "SP!", "RP!", ";S", "LEAVE", ">R",
         "R>", "R", "0=", "0<", "+", "D+", "MINUS", "DMINUS", "OVER", "DROP", "SWAP",
         "DUP", "+!", "TOGGLE", "@", "C@", "!", "C!", "S->D"]
check("the words, oldest first", [w[0] for w in reversed(WORDS)], MODEL)
for name, nfa, cfa, b in WORDS:
    want = {"I": CFA["R"] + CELL, "DROP": L["pop"]}.get(name, cfa + CELL)
    check("code field of " + name, cell(cfa), want)
    check("length byte of " + name, b, 0x80 | len(name))

# ---------------------------------------------------------------- SCR 13-15

t("LIT", ["LIT", 0x12345678, "LIT", -1], [], [0x12345678, -1])
t("EXECUTE", ["EXECUTE"], [5, CFA["DUP"]], [5, 5])
t("BRANCH forward", ["BRANCH", 3 * CELL, "LIT", 1, "LIT", 2], [], [2])
t("0BRANCH taken", ["0BRANCH", 3 * CELL, "LIT", 1, "LIT", 2], [0], [2])
t("0BRANCH not taken", ["0BRANCH", 3 * CELL, "LIT", 1, "LIT", 2], [7], [1, 2])
# BEGIN 1 + DUP 5 XOR 0= UNTIL
t("0BRANCH backward", ["LIT", 1, "+", "DUP", "LIT", 5, "XOR", "0=", "0BRANCH", -9 * CELL],
  [0], [5])

# ---------------------------------------------------------------- SCR 16-17

t("(DO) I (LOOP)", ["(DO)", "I", "(LOOP)", -2 * CELL], [5, 0], [0, 1, 2, 3, 4])
t("a loop runs once when limit = index", ["(DO)", "I", "(LOOP)", -2 * CELL], [3, 3], [3])
t("(LOOP) across the sign", ["(DO)", "I", "(LOOP)", -2 * CELL], [1, -2], [-2, -1, 0])
t("(LOOP) over addresses above 0x80000000", ["(DO)", "I", "(LOOP)", -2 * CELL],
  [0xE000F002, 0xE000F000], [0xE000F000, 0xE000F001])
t("(+LOOP) up", ["(DO)", "I", "LIT", 3, "(+LOOP)", -4 * CELL], [10, 0], [0, 3, 6, 9])
t("(+LOOP) down", ["(DO)", "I", "LIT", -3, "(+LOOP)", -4 * CELL], [0, 10], [10, 7, 4, 1])
t("(+LOOP) down stops at the limit", ["(DO)", "I", "LIT", -1, "(+LOOP)", -4 * CELL],
  [0, 3], [3, 2, 1])
t("(+LOOP) with 0 added", ["(DO)", "LIT", 0, "(+LOOP)", -3 * CELL, "LIT", 9], [0, 5], [9])
# 10 0 DO I I 3 XOR 0= IF LEAVE ENDIF LOOP
t("LEAVE", ["(DO)", "I", "I", "LIT", 3, "XOR", "0=", "0BRANCH", 2 * CELL, "LEAVE",
            "(LOOP)", -10 * CELL], [10, 0], [0, 1, 2, 3])
ds, rs, out, e = run(["(DO)"], [7, 2])
check("(DO) puts the index on top of the limit", (ds, rs), ([], [7, 2]))
ds, rs, out, e = run(["LEAVE"], [], [7, 2])
check("LEAVE sets the limit to the index", rs, [2, 2])
ds, rs, out, e = run(["I"], [], [7, 2])
check("I", (ds, rs), ([2], [7, 2]))

# ---------------------------------------------------------------- SCR 18

for c, base, want in [("5", 10, [5, 1]), ("0", 2, [0, 1]), ("9", 10, [9, 1]), ("9", 8, []),
                      ("A", 16, [10, 1]), ("F", 16, [15, 1]), ("G", 16, []), ("Z", 36, [35, 1]),
                      (":", 16, []), ("@", 16, []), ("/", 10, []), (" ", 10, []), ("a", 16, []),
                      ("2", 2, []), ("\x00", 10, [])]:
    t("DIGIT %r base %d" % (c, base), ["DIGIT"], [ord(c), base], want or [0])

# ---------------------------------------------------------------- SCR 19

TOP = WORDS[0][1]

def find(s, nfa=TOP, setup=None, raw=None):
    def put(e):
        pokes(e, DATA, raw if raw is not None else text(s))
        if setup:
            setup(e)
    return stack_of(["(FIND)"], [DATA, nfa], setup=put)

for name, nfa, cfa, b in WORDS:
    check("(FIND) " + name, find(name), [cfa + CELL, b, 1])
check("(FIND) reaches the first word from any later one", find("LIT", NFA["SWAP"]),
      [CFA["LIT"] + CELL, 0x83, 1])
check("(FIND) does not look at newer words", find("S->D", NFA["DUP"]), [0])
for s in ["NOPE", "DU", "DUPE", "DUP ", "dup", "DUQ", "LIS", "X", "(FIND", "CMOVF", "S->E", "0",
          "+!!", "R>>"]:
    check("(FIND) %r is not there" % s, find(s), [0])
check("(FIND) a name of 31 characters is not there", find("A" * 31), [0])

def ram_word(e, at, name, link, flags=0, code=None):
    """Build a header in RAM as CREATE will; returns the code field address."""
    n = len(name)
    f = bytearray(bytes([0x80 | flags | n]) + name.encode())
    f += b" " * (-len(f) % CELL)
    f[-1] |= 0x80
    pokes(e, at, bytes(f))
    lfa = at + len(f)
    poke(e, lfa, link)
    poke(e, lfa + CELL, code if code is not None else lfa + 2 * CELL)
    return lfa + CELL

NEW = RAM + 0x400
for name in ["A", "AB", "ABC", "ABCD", "ABCDE", "NAME-OF-THIRTY-ONE-CHARACTERS-X"]:
    box = {}
    def make(e, name=name):
        box["cfa"] = ram_word(e, NEW, name, TOP)
    got = find(name, NEW, make)
    check("(FIND) %s in RAM" % name, got, [box["cfa"] + CELL, 0x80 | len(name), 1])
    check("(FIND) goes on from RAM into the kernel", find("SWAP", NEW, make)[2:], [1])
check("(FIND) an immediate word, with its length byte",
      find("IMM", NEW, lambda e: ram_word(e, NEW, "IMM", TOP, 0x40))[1:], [0xC3, 1])
check("(FIND) skips a smudged word",
      find("SMU", NEW, lambda e: ram_word(e, NEW, "SMU", TOP, 0x20)), [0])
check("(FIND) finds the older word of two with one name, behind a smudged one",
      find("DUP", NEW, lambda e: ram_word(e, NEW, "DUP", TOP, 0x20)), [CFA["DUP"] + CELL, 0x83, 1])
def two(e):
    a = ram_word(e, NEW, "TWIN", TOP)
    ram_word(e, NEW + 0x40, "TWIN", NEW)
check("(FIND) finds the newer word of two with one name", find("TWIN", NEW + 0x40, two)[0],
      NEW + 0x40 + 8 + 2 * CELL)
check("(FIND) with a link of 0", find("QQ", NEW, lambda e: ram_word(e, NEW, "ZZ", 0)), [0])

# ---------------------------------------------------------------- SCR 20

def enclose(s, delim=" "):
    return stack_of(["ENCLOSE"], [DATA, ord(delim)], setup=lambda e: pokes(e, DATA, s))[1:]

for s, d, want in [(b"ABC DE\0", " ", [0, 3, 4]), (b"  ABC  DE\0", " ", [2, 5, 6]),
                   (b"ABC\0", " ", [0, 3, 3]), (b"\0", " ", [0, 1, 0]),
                   (b"   \0", " ", [3, 4, 3]), (b"A B\0", " ", [0, 1, 2]),
                   (b" x y)z\0", ")", [0, 4, 5]), (b"))a)\0", ")", [2, 3, 4]),
                   (b"A\0", " ", [0, 1, 1]), (b"WORD \0", " ", [0, 4, 5])]:
    check("ENCLOSE %r" % s, enclose(s, d), want)
check("ENCLOSE keeps the address", stack_of(["ENCLOSE"], [DATA, 32],
      setup=lambda e: pokes(e, DATA, b"A \0"))[0], DATA)

# ---------------------------------------------------------------- SCR 21

OUT = UP + 0x34
ds, rs, out, e = run(["EMIT", "EMIT", "EMIT"], [0xC1, ord("b"), 0x141],
                     setup=lambda e: poke(e, OUT, 10))
check("EMIT sends seven bits", (ds, out), ([], b"AbA"))
check("EMIT counts in OUT", peek(e, OUT), 13)
ds, rs, out, e = run(["KEY", "KEY"], keys=b"x\xE1")
check("KEY", (ds, out), ([ord("x"), ord("a")], b""))
ds, rs, out, e = run(["?TERMINAL", "?TERMINAL", "?TERMINAL"], keys=b"q")
check("?TERMINAL takes the key", (ds, e.uart_in), ([1, 0, 0], []))
ds, rs, out, e = run(["CR"], [4])
check("CR", (ds, out), ([4], b"\r\n"))

# ---------------------------------------------------------------- SCR 22

def cmove(src, dst, n, init):
    ds, rs, out, e = run(["CMOVE"], [1, DATA + src, DATA + dst, n],
                         setup=lambda e: pokes(e, DATA, init))
    return ds, bytes(e.ram[DATA - RAM:DATA - RAM + len(init)])

check("CMOVE", cmove(0, 8, 5, b"HELLO...________"), ([1], b"HELLO...HELLO___"))
check("CMOVE of nothing", cmove(0, 8, 0, b"HELLO...________"), ([1], b"HELLO...________"))
check("CMOVE upward over itself repeats the first byte (FILL counts on it)",
      cmove(0, 1, 6, b"x......_"), ([1], b"xxxxxxx_"))
check("CMOVE downward over itself", cmove(2, 0, 5, b"..abcde_"), ([1], b"abcdede_"))
check("CMOVE to an odd address", cmove(1, 9, 3, b"0123456789abcdef"), ([1], b"012345678123cdef"))

# ---------------------------------------------------------------- SCR 23-24

random.seed(1979)
EDGE = [0, 1, 2, 3, 0x7FFFFFFF, 0x80000000, 0x80000001, 0xFFFFFFFE, 0xFFFFFFFF, 0xFFFF, 0x10000]
pairs = [(a, b) for a in EDGE for b in EDGE]
pairs += [(random.getrandbits(32), random.getrandbits(random.choice([4, 16, 31, 32])))
          for _ in range(150)]
bad = [(a, b) for a, b in pairs
       if stack_of(["U*"], [9, a, b]) != [9, (a * b) & M32, (a * b) >> 32]]
check("U* in %d cases" % len(pairs), bad, [])

cases = []
for _ in range(250):
    u = random.choice(EDGE[1:] + [random.getrandbits(random.choice([3, 16, 31, 32])) or 1])
    q = random.getrandbits(random.choice([1, 8, 32]))
    r = random.randrange(u)
    cases.append((q * u + r, u))
cases += [(0, 1), (0, M32), (M32, 1), (M32 * M32 + M32 - 1, M32),
          (0x7FFFFFFF_FFFFFFFF, 0x80000000), (5, 0x80000001)]
bad = []
for d, u in cases:
    got = stack_of(["U/"], [9, d & M32, d >> 32, u])
    if got != [9, d % u, d // u]:
        bad.append((d, u))
check("U/ in %d cases" % len(cases), bad, [])
check("U/ by zero ends", stack_of(["U/"], [9, 5, 0, 0])[::2], [9, M32])

# ---------------------------------------------------------------- SCR 25-28

t("AND", ["AND"], [9, 0xFF00FF00, 0x0FF00FF0], [9, 0x0F000F00])
t("OR", ["OR"], [9, 0xFF00FF00, 0x0FF00FF0], [9, 0xFFF0FFF0])
t("XOR", ["XOR"], [9, 0xFF00FF00, 0x0FF00FF0], [9, 0xF0F0F0F0])
t("SP@", ["SP@"], [1, 2], [1, 2, S0 - 2 * CELL])
t("SP@ on an empty stack", ["SP@"], [], [S0])
t("SP!", ["SP!"], [1, 2, 3], [])
ds, rs, out, e = run(["RP!"], [1], [5, 6, 7])
check("RP!", (ds, rs), ([1], []))
ds, rs, out, e = run(["SP!", "RP!"], [1], [5], setup=lambda e: (poke(e, UP + 0x0C, S0 - 64),
                                                              poke(e, UP + 0x10, R0 - 32)))
check("SP! and RP! read S0 and R0", (e.x[8], e.x[4]), (S0 - 64, R0 - 32))
ds, rs, out, e = run([">R"], [1, 2], [8])
check(">R", (ds, rs), ([1], [8, 2]))
ds, rs, out, e = run(["R>"], [1], [8, 2])
check("R>", (ds, rs), ([1, 2], [8]))
ds, rs, out, e = run(["R"], [1], [8, 2])
check("R", (ds, rs), ([1, 2], [8, 2]))
for n, z, neg in [(0, 1, 0), (1, 0, 0), (-1, 0, 1), (0x80000000, 0, 1), (0x7FFFFFFF, 0, 0)]:
    t("0= of %#x" % (n & M32), ["0="], [9, n], [9, z])
    t("0< of %#x" % (n & M32), ["0<"], [9, n], [9, neg])

# ---------------------------------------------------------------- SCR 29

t("+", ["+"], [9, 3, 4], [9, 7])
t("+ wraps", ["+"], [9, 0xFFFFFFFF, 2], [9, 1])
def d(x):
    return [x & M32, (x >> 32) & M32]
for a, b in [(1, 2), (0xFFFFFFFF, 1), (0xFFFFFFFF, 0xFFFFFFFF), (-1, 1), (-1, -1),
             (0x1_00000000, -1), (0x7FFFFFFF_FFFFFFFF, 1), (0x12345678_9ABCDEF0, 0x0FEDCBA9_87654321)]:
    t("D+ %#x %#x" % (a, b), ["D+"], [9] + d(a) + d(b), [9] + d(a + b))
for n in [0, 1, -1, 0x80000000, 5]:
    t("MINUS %#x" % (n & M32), ["MINUS"], [9, n], [9, -n])
for n in [0, 1, -1, 0x1_00000000, 0x8000_0000, 0x7FFFFFFF_FFFFFFFF, -0x1_00000000, 0x12345678_00000000]:
    t("DMINUS %#x" % n, ["DMINUS"], [9] + d(n), [9] + d(-n))

# ---------------------------------------------------------------- SCR 30-32

t("OVER", ["OVER"], [1, 2], [1, 2, 1])
t("DROP", ["DROP"], [1, 2], [1])
t("SWAP", ["SWAP"], [9, 1, 2], [9, 2, 1])
t("DUP", ["DUP"], [1, 2], [1, 2, 2])
ds, rs, out, e = run(["+!", "+!"], [9, -7, DATA, 5, DATA], setup=lambda e: poke(e, DATA, 100))
check("+!", (ds, peek(e, DATA)), ([9], 98))
ds, rs, out, e = run(["TOGGLE", "TOGGLE"], [9, DATA + 1, 0x20, DATA + 3, 0x80],
                     setup=lambda e: poke(e, DATA, 0x11223344))
check("TOGGLE", (ds, peek(e, DATA)), ([9], 0x91221344))
t("@", ["@"], [9, DATA], [9, 0xCAFE1234], setup=lambda e: poke(e, DATA, 0xCAFE1234))
t("@ from flash", ["@"], [9, L["boot_up"] + 3 * CELL], [9, S0])
t("C@", ["C@", "SWAP", "C@"], [DATA + 3, DATA + 1], [0x12, 0xCA],
  setup=lambda e: poke(e, DATA, 0xCAFE1234))
ds, rs, out, e = run(["!"], [9, 0xDEADBEEF, DATA])
check("!", (ds, peek(e, DATA)), ([9], 0xDEADBEEF))
ds, rs, out, e = run(["C!", "C!"], [9, 0x1AB, DATA + 1, 0xCD, DATA + 2],
                     setup=lambda e: poke(e, DATA, 0x11223344))
check("C!", (ds, peek(e, DATA)), ([9], 0x11CDAB44))
for n in [0, 1, 0x7FFFFFFF, -1, 0x80000000]:
    t("S->D %#x" % (n & M32), ["S->D"], [9, n], [9, n, -1 if n & 0x80000000 else 0])

# a misaligned @ is a trap on the chip, and a fault here
try:
    run(["@"], [DATA + 2])
    check("@ at an odd address faults", "no fault", "fault")
except AssertionError as err:
    check("@ at an odd address faults", "misaligned-load" in str(err), True)

# ---------------------------------------------------------------- SCR 33, 34, 43

W1, W2 = RAM + 0x500, RAM + 0x600
def colon(e):
    # : DOUBLE  DUP + ;      : QUAD  DOUBLE DOUBLE ;
    poke(e, W1, L["docol"]); thread(e, ["DUP", "+", ";S"], W1 + CELL)
    poke(e, W2, L["docol"])
    for i, c in enumerate([W1, W1, CFA[";S"]]):
        poke(e, W2 + CELL * (i + 1), c)
t("a colon definition (docol, ;S)", [W1], [9, 21], [9, 42], setup=colon)
t("nested colon definitions", [W2, "LIT", 1], [9, 5], [9, 20, 1], setup=colon)
t("EXECUTE of a colon definition", ["EXECUTE"], [3, W2], [12], setup=colon)
t("a CONSTANT (docon)", [W1], [9], [9, 1234],
  setup=lambda e: (poke(e, W1, L["docon"]), poke(e, W1 + CELL, 1234)))
t("a VARIABLE (dovar)", [W1, "@"], [9], [9, 77],
  setup=lambda e: (poke(e, W1, L["dovar"]), poke(e, W1 + CELL, 77)))
t("a USER variable (douse)", [W1, W1, "@"], [9], [9, UP + 0x0C, S0],
  setup=lambda e: (poke(e, W1, L["douse"]), poke(e, W1 + CELL, 0x0C)))
def does(e):
    # : CONST  <BUILDS ,  DOES> @ ;     5 CONST FIVE
    thread(e, ["@", ";S"], W2)                          # the thread after DOES>
    poke(e, W1, L["dodoe"]); poke(e, W1 + CELL, W2); poke(e, W1 + 2 * CELL, 5)
t("a <BUILDS DOES> word (dodoe)", [W1, "LIT", 1], [9], [9, 5, 1], setup=does)
def does2(e):
    thread(e, [";S"], W2)
    poke(e, W1, L["dodoe"]); poke(e, W1 + CELL, W2)
t("dodoe pushes the address behind the DOES> pointer", [W1], [], [W1 + 2 * CELL], setup=does2)

# ---------------------------------------------------------------- the image

# every word above has been run; none may need more than the chip has
check("the image fits the first 16 KiB", len(IMAGE) < 16384, True)

print("%d checks, %d failed; image %d bytes, %d words" % (count, failed, len(IMAGE), len(WORDS)))
sys.exit(1 if failed else 0)
