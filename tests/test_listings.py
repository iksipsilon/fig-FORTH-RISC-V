#!/usr/bin/env python3
"""Assemble figforth.asm and test the words of listings.asm in the emulator.

    python3 tests/test_listings.py

The machine is started, and lines are typed at it as at the terminal. A test
is what comes back after the echo of the line. Each test starts from a copy
of the machine as it is after a cold start.
"""
import copy, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from rv32emu import Emu

CELL = 4
RAM = 0x20000000

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

failed = 0
count = 0

def check(what, got, want):
    global failed, count
    count += 1
    if got != want:
        failed += 1
        print("FAIL %s\n     got  %r\n     want %r" % (what, got, want))

# ---------------------------------------------------------------- the machine

def idle(e):
    return e.pc == L["serial_getc1"] and not e.uart_in

def run_to_idle(e, max_steps=20_000_000):
    for _ in range(max_steps):
        if idle(e):
            return
        try:
            e.step()
        except RuntimeError:
            raise AssertionError("emulator fault %r after %r" % (e.fault, bytes(e.uart_out)[-80:]))
    raise AssertionError("no end after %d steps, pc = %#x" % (max_steps, e.pc))

BOOTED = Emu(IMAGE, b"")
run_to_idle(BOOTED)

def keys(e, data):
    """Type the bytes; returns everything the machine sends until it waits again."""
    n = len(e.uart_out)
    e.uart_in = list(data)
    run_to_idle(e)
    return bytes(e.uart_out[n:])

def say(e, line):
    """Type a line and Enter; returns what comes after the echo, as text."""
    out = keys(e, line.encode() + b"\r")
    echo = line.encode() + b" "
    assert out.startswith(echo), "echo of %r: %r" % (line, out)
    return out[len(echo):].decode("latin-1")

def t(lines, want, what=None, ok="OK"):
    """Type the lines at a fresh machine. The last one must answer with the
    text `want` and then OK."""
    e = copy.deepcopy(BOOTED)
    if isinstance(lines, str):
        lines = [lines]
    for line in lines[:-1]:
        say(e, line)
    check(what or lines[-1], say(e, lines[-1]), want + ok + "\r\n")
    return e

def err(lines, want, what=None):
    """The same, for a line that ends in an error: there is no OK."""
    return t(lines, want, what, ok="")

def peek(e, a):
    return int.from_bytes(e.ram[a - RAM:a - RAM + 4], "little")

# ---------------------------------------------------------------- the dictionary

NAMES = [
    ':', ';', 'CONSTANT', 'VARIABLE', 'USER', '0', '1', '2', '3', 'BL', 'C/L', '+ORIGIN', 'S0',
    'R0', 'TIB', 'WIDTH', 'WARNING', 'FENCE', 'DP', 'VOC-LINK', 'BLK', 'IN', 'OUT', 'SCR',
    'OFFSET', 'CONTEXT', 'CURRENT', 'STATE', 'BASE', 'DPL', 'FLD', 'CSP', 'R#', 'HLD', '1+',
    '2+', 'HERE', 'ALLOT', 'ALIGN', ',', 'C,', '-', '=', '<', '>', 'ROT', 'SPACE',
    '-DUP', 'TRAVERSE', 'LATEST', 'LFA', 'CFA', 'NFA', 'PFA', '!CSP', '?ERROR', '?COMP',
    '?EXEC', '?PAIRS', '?CSP', '?LOADING', 'COMPILE', '[', ']', 'SMUDGE', 'HEX', 'DECIMAL',
    '(;CODE)', ';CODE', '<BUILDS', 'DOES>', 'COUNT', 'TYPE', '-TRAILING', '(.")', '."',
    'EXPECT', 'QUERY', '\x00', 'FILL', 'ERASE', 'BLANKS', 'HOLD', 'PAD', 'WORD', '(NUMBER)',
    'NUMBER', '-FIND', '(ABORT)', 'ERROR', 'ID.', 'CREATE', '[COMPILE]', 'LITERAL', 'DLITERAL',
    '?STACK', 'INTERPRET', 'IMMEDIATE', 'VOCABULARY', 'FORTH', 'DEFINITIONS', '(', 'QUIT',
    'ABORT', 'COLD', '+-', 'D+-', 'ABS', 'DABS', 'MIN', 'MAX', 'M*', 'M/', '*', '/MOD', '/',
    'MOD', '*/MOD', '*/', 'M/MOD', 'MESSAGE', "'", 'FORGET', 'BACK', 'BEGIN', 'ENDIF', 'THEN',
    'DO', 'LOOP', '+LOOP', 'UNTIL', 'END', 'AGAIN', 'REPEAT', 'IF', 'ELSE', 'WHILE', 'SPACES',
    '<#', '#>', 'SIGN', '#', '#S', 'D.R', 'D.', '.R', '.', '?', 'VLIST'
]

def walk(image, nfa):
    """Follow the link fields from nfa: [(name, nfa, length byte)], newest
    first. Checks the shape of every header on the way."""
    words = []
    while nfa:
        assert nfa % CELL == 0, "name field at %#x is not on a cell boundary" % nfa
        b = image[nfa]
        assert b & 0x80, "length byte at %#x lacks bit 7" % nfa
        n = b & 0x1F
        end = nfa + 1
        while not image[end] & 0x80:
            end += 1
        raw = bytes(c & 0x7F for c in image[nfa + 1:end + 1])
        assert len(raw) >= n and (len(raw) + 1) % CELL == 0, "name field at %#x" % nfa
        assert raw[n:] == b" " * (len(raw) - n), "padding of the name at %#x" % nfa
        words.append((raw[:n].decode(), nfa, b))
        nfa = int.from_bytes(image[end + 1:end + 5], "little")
    return words

WORDS = walk(IMAGE, L["last_nfa"])
check("the words after the nucleus, oldest first", [w[0] for w in reversed(WORDS)][46:], NAMES)
check("the nucleus is under them", len(WORDS), 46 + len(NAMES))
IMMEDIATE = {":", ";", "[", ";CODE", '."', "\0", "[COMPILE]", "LITERAL", "DLITERAL", "FORTH", "(",
             "'", "BEGIN", "ENDIF", "THEN", "DO", "LOOP", "+LOOP", "UNTIL", "END", "AGAIN",
             "REPEAT", "IF", "ELSE", "WHILE"}
check("the immediate words", {w[0] for w in WORDS if w[2] & 0x40}, IMMEDIATE)
check("no thread or header is off the cell", len(IMAGE) % CELL, 0)

# ---------------------------------------------------------------- the prompt

check("cold start", bytes(BOOTED.uart_out), b"\r\nfig-FORTH RISC-V\r\n")
t("", "", "an empty line")
t("1 2 + .", "3 ")
err("FOO", "FOO? MSG # 0 ")
err("dup", "dup? MSG # 0 ", "lower case is not upper case")
t(["1 2 FOO", ". . SP@ S0 @ = ."], "0 7 1 ",
  "an error empties the stack, then leaves IN and BLK on it")
t("( A COMMENT ) 5 .", "5 ")
t("       7     .   ", "7 ", "blanks")

e = copy.deepcopy(BOOTED)
check("backspace", keys(e, b"12\x7f3 .\r"), b"12\x083 . 13 OK\r\n")
check("backspace at the start of the line rings the bell", keys(e, b"\x7f1 .\r"), b"\x071 . 1 OK\r\n")
line = b" " * 77 + b"5 ."
check("a full line of 80 needs no Enter", keys(e, line), line + b"5 OK\r\n")

# ---------------------------------------------------------------- numbers

t("-5 .", "-5 ")
t("2147483647 . -2147483648 .", "2147483647 -2147483648 ")
t("HEX FF DECIMAL .", "255 ")
t("HEX -1 . 7FFFFFFF . DECIMAL", "-1 7FFFFFFF ")
t("255 HEX . DECIMAL", "FF ")
t("5 2 BASE ! . DECIMAL", "101 ")
err("12G", "12G? MSG # 0 ")
t("1.5 D. DPL @ .", "15 1 ", "a point makes a double number")
t("15 DPL @ .", "-1 ")
t("-123456789012. D.", "-123456789012 ")
t("HEX FFFFFFFF. DECIMAL D.", "4294967295 ")
t("123 8 .R", "     123")
t("-5 6 .R", "    -5")
t("123456 3 .R", "123456")
t("-1. 4 D.R", "  -1")
t("3 SPACES", "   ")
t("0 SPACES -2 SPACES", "")
t([": T <# # # 46 HOLD #S #> TYPE ;", "12345. T"], "123.45")
t("1000000007. 10 M/MOD D. .", "100000000 7 ")
t("20 +ORIGIN @ .", "127 ", "the backspace key in the origin table")

# ---------------------------------------------------------------- arithmetic

t("7 3 - . 3 7 - .", "4 -4 ")
t("6 7 * . -6 7 * .", "42 -42 ")
t("100000 100000 * .", "1410065408 ", "* keeps the low cell")
t("7 2 / . -7 2 / . 7 -2 / .", "3 -3 -3 ")
t("7 2 MOD . -7 2 MOD . 7 -2 MOD .", "1 -1 1 ")
t("-7 2 /MOD . .", "-3 -1 ")
t("100000 100000 1000 */ .", "10000000 ", "*/ keeps a double product")
t("7 5 3 */MOD . .", "11 2 ")
t("-100000 100000 M* D.", "-10000000000 ")
t("-10000000001. 100000 M/ . .", "-100000 -1 ")
t("-9 ABS . 9 ABS . -9. DABS D.", "9 9 9 ")
t("3 5 MIN . 3 5 MAX . -3 5 MIN . -3 -5 MAX .", "3 5 -3 -3 ")
t("5 -1 +- . -5. 1 D+- D.", "-5 -5 ")
t("5 5 = . 5 6 = .", "1 0 ")
t("1 2 < . 2 1 < . 2 2 < . -1 1 < .", "1 0 0 1 ")
t("1 2 > . 2 1 > .", "0 1 ")
t("1 2 3 ROT . . .", "1 3 2 ")
t("0 -DUP . 5 -DUP . .", "0 5 5 ")
t("5 1+ . 5 2+ .", "6 7 ")
t("0 . 1 . 2 . 3 . BL . C/L .", "0 1 2 3 32 64 ")

# ---------------------------------------------------------------- definitions

t([": SQ DUP * ;", "7 SQ ."], "49 ")
t([": A 1 ;", ": B A A + ;", ": C B B + ;", "C ."], "4 ")
t([": T IF 1 ELSE 2 THEN . ;", "0 T 5 T"], "2 1 ")
t([": T IF 1 . ENDIF 2 . ;", "0 T 5 T"], "2 1 2 ")
t([": T 0 BEGIN 1+ DUP 5 = UNTIL . ;", "T"], "5 ")
t([": T 0 BEGIN 1+ DUP 5 = END . ;", "T"], "5 ")
t([": T 0 BEGIN DUP 3 < WHILE DUP . 1+ REPEAT DROP ;", "T"], "0 1 2 ")
t([": T 0 BEGIN 1+ DUP 4 = IF . ;S THEN AGAIN ;", "T"], "4 ")
t([": T 10 0 DO I . LOOP ;", "T"], "0 1 2 3 4 5 6 7 8 9 ")
t([": T 10 0 DO I . 3 +LOOP ;", "T"], "0 3 6 9 ")
t([": T 0 10 DO I . -4 +LOOP ;", "T"], "10 6 2 ")
err([": T 3 0 DO 2 0 DO J? LOOP LOOP ;"], "J?? MSG # 0 ", "an unknown word while compiling")
t([": T 3 0 DO 12 10 DO I . LOOP I . LOOP ;", "T"], "10 11 0 10 11 1 10 11 2 ")
t([": T 10 0 DO I 3 = IF LEAVE THEN I . LOOP ;", "T"], "0 1 2 3 ",
  "LEAVE ends the loop at LOOP")
t([": T -12 ;", "T ."], "-12 ", "a literal")
t([": T 100000. ;", "T D."], "100000 ", "a double literal")
t([": T [ 3 4 + ] LITERAL . ;", "T"], "7 ")
t([": T ( N -- ) . ;", "5 T"], "5 ", "a comment in a definition")
t(["42 CONSTANT A", "A . A A + ."], "42 84 ")
t(["7 VARIABLE V", "V @ . 9 V ! V ? 1 V +! V ?"], "7 9 10 ")
t(["76 USER B", "B @ . HEX B @ . DECIMAL"], "10 10 ", "76 is the offset of BASE")
# ;CODE without an assembler: the two instructions of a constant, by hand
LW_A1_4_A0 = (4 << 20) | (10 << 15) | (2 << 12) | (11 << 7) | 0x03     # lw a1, 4(a0)
J_PUSH = (L["push"] << 20) | 0x67                                      # jalr zero, push(zero)
t([": KON CREATE SMUDGE , ;CODE", "%d , %d ," % (LW_A1_4_A0, J_PUSH), "5 KON FIVE", "FIVE FIVE + ."],
  "10 ", ";CODE: the code field of the new word points behind (;CODE)")
t([": CON <BUILDS , DOES> @ ;", "5 CON FIVE 6 CON SIX", "FIVE . SIX . FIVE SIX + ."], "5 6 11 ")
t([": ARR <BUILDS 4 * ALLOT DOES> SWAP 4 * + ;", "3 ARR X", "11 0 X ! 22 1 X ! 33 2 X !",
   "0 X @ . 1 X @ . 2 X @ ."], "11 22 33 ")
t([": T 5 ;", ": T T 1 + ;", "T ."], "6 ", "a word may use the one it replaces")
t([": DUP ;"], "DUP MSG # 4  ", "a name that is there already")
t(["3 ALLOT", ": T 5 ;", "T ."], "5 ", "CREATE puts the header on a cell boundary")
t("HERE 1 C, ALIGN HERE SWAP - .", "4 ")
t("HERE 5 , HERE OVER - . @ .", "4 5 ")
t([": T ;", "LATEST ID. LATEST PFA NFA LATEST = ."], "T 1 ")
t("' DUP NFA ID. ' VOCABULARY NFA ID. ' I NFA ID.", "DUP VOCABULARY I ")
t("' DUP LFA @ ID.", "SWAP ")
t("3 ' DUP CFA EXECUTE . .", "3 3 ")
t([": T ' DUP CFA EXECUTE ;", "4 T . ."], "4 4 ", "' in a definition takes its word from the input")
t([": MYIF [COMPILE] IF ; IMMEDIATE", ": T MYIF 1 . THEN 2 . ;", "0 T 1 T"], "2 1 2 ")
t([": T 7 . ; IMMEDIATE", ": U T ;"], "7 ", "an immediate word runs while compiling")
t([": T COMPILE DUP ; IMMEDIATE", ": U T * ;", "5 U ."], "25 ")

# ---------------------------------------------------------------- text

t('." HI THERE"', "HI THERE")
t([': T ." A" 1 . ." AB" 2 . ." ABC" 3 . ." ABCD" 4 . ." ABCDE" 5 . ;', "T"],
  "A1 AB2 ABC3 ABCD4 ABCDE5 ", "the thread goes on at a cell after a text of any length")
t([': T ." HELLO, WORLD" CR ;', "T"], "HELLO, WORLD\r\n")
t("PAD 10 BLANKS 65 PAD C! PAD 10 -TRAILING . PAD - .", "1 0 ")
t("PAD 8 66 FILL PAD 8 TYPE", "BBBBBBBB")
t("PAD 8 66 FILL PAD 4 ERASE PAD @ . PAD 4 + C@ .", "0 66 ")
t("HERE COUNT TYPE", "TYPE ", "WORD leaves the last word at HERE")
t("PAD HERE - .", "68 ")

# ---------------------------------------------------------------- errors

err("DROP", "DROP? MSG # 1 ", "an empty stack")
err(". ", "0 .? MSG # 1 ")
err("IF", "IF? MSG # 17 ", "compilation only")
err([": T : ;"], ":? MSG # 18 ", "execution only")
err([": T 1 IF ;"], ";? MSG # 20 ", "a definition not finished")
err([": T THEN ;"], "THEN? MSG # 19 ", "conditionals not paired")
err([": T BEGIN LOOP ;"], "LOOP? MSG # 19 ")
t([": T 1", "2 + . ;", "T"], "3 ", "a definition over two lines")
t([": T FOO", "1 2 + ."], "3 ", "an error leaves the compiler")
err("-->", "-->? MSG # 0 ", "no disc words")
err("' NOPE", "NOPE? MSG # 0 ")
err(["-1 WARNING !", "FOO"], "\r\nfig-FORTH RISC-V", "WARNING below 0: an error aborts")

# ---------------------------------------------------------------- FORGET, vocabularies

e = t([": A 1 ;", "HERE", ": B 2 ;", "FORGET B", "HERE = . A ."], "1 1 ")
check("FORGET takes the word out", say(e, "B"), "B? MSG # 0 \r\n")
err("FORGET DUP", "DUP? MSG # 21 ", "the kernel is below FENCE")
err("FORGET NOPE", "NOPE? MSG # 0 ")
err(["VOCABULARY V IMMEDIATE", "V DEFINITIONS", ": X 7 ;", "X . 2 DUP + .", "FORTH DEFINITIONS X"],
  "X? MSG # 0 ", "a word of another vocabulary is not seen from FORTH")
t(["VOCABULARY V IMMEDIATE", "V DEFINITIONS", ": X 7 ;", "FORTH DEFINITIONS", ": Y V X FORTH ;",
   "Y ."], "7 ")
err(["VOCABULARY V IMMEDIATE", "V DEFINITIONS", "FORTH", "FORGET DUP"], "FORGET? MSG # 24 ",
    "FORGET wants CONTEXT and CURRENT the same")
t(["VOCABULARY V IMMEDIATE", "VOC-LINK @ ' V 12 + = . ' V 12 + @ %d = ." % (RAM + 2 * CELL)],
  "1 1 ", "the vocabulary link")

e = copy.deepcopy(BOOTED)
out = say(e, "VLIST")
check("VLIST starts with the newest word", out.split()[:3], ["VLIST", "?", "."])
check("VLIST ends with the oldest", out.split()[-3:], ["EXECUTE", "LIT", "OK"])
check("VLIST shows every word", len(out.split()), len(WORDS) + 1)  # and OK
check("VLIST keeps to the line", max(len(l) for l in out.split("\r\n")) < 80, True)
check("a key stops VLIST", len(keys(e, b"VLIST\rX").split()) < 12, True)

# ---------------------------------------------------------------- cold and warm

e = err([": T 5 ;", "COLD"], "\r\nfig-FORTH RISC-V", "COLD")
check("COLD forgets the new words", say(e, "T"), "T? MSG # 0 \r\n")
check("COLD puts the dictionary pointer back", say(e, "HERE ."), "%d OK\r\n" % (RAM + 3 * CELL))
e = t([": T 5 ;", "HEX"], "")
e.pc = L["origin"] + 4
run_to_idle(e)
check("a warm start keeps the new words and sets the base", say(e, "T 16 + ."), "21 OK\r\n")

# ---------------------------------------------------------------- the image

check("the image fits the first 16 KiB", len(IMAGE) < 16384, True)
print("%d checks, %d failed; image %d bytes, %d words" % (count, failed, len(IMAGE), len(WORDS)))
sys.exit(1 if failed else 0)
