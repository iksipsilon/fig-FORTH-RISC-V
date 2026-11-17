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

# The error messages are on screens 4 and 5 of the disc, as on the board:
# message n is line n counted from the top of screen 4. WARNING starts at 1.
MESSAGES = ["( ERROR MESSAGES )", "EMPTY STACK", "DICTIONARY FULL", "", "ISN'T UNIQUE", "",
            "DISC RANGE ?", "FULL STACK", "DISC ERROR", "", "", "", "", "", "",
            "FORTH INTEREST GROUP",
            "( ERROR MESSAGES )", "COMPILATION ONLY, USE IN DEFINITION", "EXECUTION ONLY",
            "CONDITIONALS NOT PAIRED", "DEFINITION NOT FINISHED", "IN PROTECTED DICTIONARY",
            "USE ONLY WHEN LOADING", "OFF CURRENT EDITING SCREEN", "DECLARE VOCABULARY",
            "", "", "", "", "", "", "FORTH INTEREST GROUP"]
BOOTED = Emu(IMAGE, b"")
BOOTED.f[0x4000 + 4 * 1024:0x4000 + 6 * 1024] = b"".join(l.encode().ljust(64) for l in MESSAGES)
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
    ':', ';', 'CONSTANT', 'VARIABLE', 'USER', '0', '1', '2', '3', 'BL', 'C/L', 'FIRST',
    'LIMIT', 'B/BUF', 'B/SCR', '+ORIGIN', 'S0', 'R0', 'TIB', 'WIDTH', 'WARNING', 'FENCE', 'DP',
    'VOC-LINK', 'BLK', 'IN', 'OUT', 'SCR', 'OFFSET', 'CONTEXT', 'CURRENT', 'STATE', 'BASE',
    'DPL', 'FLD', 'CSP', 'R#', 'HLD', '1+', '2+', 'HERE', 'ALLOT', 'ALIGN', ',', 'C,', '-',
    '=', '<', '>', 'ROT', 'SPACE', '-DUP', 'TRAVERSE', 'LATEST', 'LFA', 'CFA', 'NFA', 'PFA',
    '!CSP', '?ERROR', '?COMP', '?EXEC', '?PAIRS', '?CSP', '?LOADING', 'COMPILE', '[', ']',
    'SMUDGE', 'HEX', 'DECIMAL', '(;CODE)', ';CODE', '<BUILDS', 'DOES>', 'COUNT', 'TYPE',
    '-TRAILING', '(.")', '."', 'EXPECT', 'QUERY', '\x00', 'FILL', 'ERASE', 'BLANKS', 'HOLD',
    'PAD', 'WORD', '(NUMBER)', 'NUMBER', '-FIND', '(ABORT)', 'ERROR', 'ID.', 'CREATE',
    '[COMPILE]', 'LITERAL', 'DLITERAL', '?STACK', 'INTERPRET', 'IMMEDIATE', 'VOCABULARY',
    'FORTH', 'DEFINITIONS', '(', 'QUIT', 'ABORT', 'COLD', '+-', 'D+-', 'ABS', 'DABS', 'MIN',
    'MAX', 'M*', 'M/', '*', '/MOD', '/', 'MOD', '*/MOD', '*/', 'M/MOD', 'USE', 'PREV', '+BUF',
    'UPDATE', 'EMPTY-BUFFERS', 'DR0', 'BUFFER', 'BLOCK', '(LINE)', '.LINE', 'MESSAGE', 'LOAD',
    '-->', 'LO', 'HI', 'BLOCK-WRITE', 'R/W', "'", 'FORGET', 'BACK', 'BEGIN', 'ENDIF', 'THEN',
    'DO', 'LOOP', '+LOOP', 'UNTIL', 'END', 'AGAIN', 'REPEAT', 'IF', 'ELSE', 'WHILE', 'SPACES',
    '<#', '#>', 'SIGN', '#', '#S', 'D.R', 'D.', '.R', '.', '?', 'LIST', 'INDEX', 'TRIAD',
    'VLIST', 'TEXT', 'LINE', 'EDITOR', 'WHERE'
]

EDITOR_NAMES = [
    '#LOCATE', '#LEAD', '#LAG', '-MOVE', 'H', 'E', 'S', 'D', 'M', 'T', 'L', 'R', 'P', 'I',
    'TOP', 'CLEAR', 'FLUSH', 'COPY', 'MATCH', '1LINE', 'FIND', 'DELETE', 'N', 'F', 'B', 'X',
    'TILL', 'C'
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
        if nfa == RAM:                      # the blank name of FORTH: the end of
            break                           # another vocabulary
    return words

WORDS = walk(IMAGE, L["last_nfa"])
check("the words after the nucleus, oldest first", [w[0] for w in reversed(WORDS)][47:], NAMES)
check("the nucleus is under them", len(WORDS), 47 + len(NAMES))
IMMEDIATE = {":", ";", "[", ";CODE", '."', "\0", "[COMPILE]", "LITERAL", "DLITERAL", "FORTH", "(",
             "'", "BEGIN", "ENDIF", "THEN", "DO", "LOOP", "+LOOP", "UNTIL", "END", "AGAIN",
             "REPEAT", "IF", "ELSE", "WHILE", "-->", "EDITOR"}
check("the immediate words", {w[0] for w in WORDS if w[2] & 0x40}, IMMEDIATE)
check("no thread or header is off the cell", len(IMAGE) % CELL, 0)
EWORDS = walk(IMAGE, L["last_enfa"])
check("the words of EDITOR, oldest first", [w[0] for w in reversed(EWORDS)], EDITOR_NAMES)
check("none of them is immediate", [w[0] for w in EWORDS if w[2] & 0x40], [])

# ---------------------------------------------------------------- the prompt

check("cold start", bytes(BOOTED.uart_out), b"\r\nfig-FORTH RISC-V\r\n")
t("", "", "an empty line")
t("1 2 + .", "3 ")
err("FOO", "FOO? ")
err("foo", "FOO? ", "the word of an error is shown in capitals")

# small letters: -FIND turns a word into capitals before it looks it up
t("1 dup + .", "2 ", "a name in small letters")
t("3 Dup + .", "6 ", "a name in mixed letters")
t([": sq dup * ;", "7 sq . 8 SQ . 9 Sq ."], "49 64 81 ", "a word defined in small letters")
t([": sq dup * ;", "LATEST ID."], "SQ ", "the name is kept in capitals")
t("hex ff . decimal", "FF ", "hex digits in small letters")
t("hex 0a0 1+ . decimal", "A1 ")
t('." Hello, world"', "Hello, world", "text after .\" keeps its letters")
t([': hi ." Mixed Case" ;', "hi"], "Mixed Case", "and so does text compiled by .\"")
t("5 variable v v @ . 6 v ! V @ .", "5 6 ")
t("' dup ' DUP = .", "1 ", "' finds the word in either case")
t([": twice dup + ;", "forget twice", "1 2 + ."], "3 ", "FORGET in small letters")
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
err("12G", "12G? ")
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
err([": T 3 0 DO 2 0 DO J? LOOP LOOP ;"], "J?? ", "an unknown word while compiling")
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
t([": DUP ;"], "DUP ISN'T UNIQUE ", "a name that is there already")
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

err("DROP", "DROP? EMPTY STACK", "an empty stack")
e = copy.deepcopy(BOOTED)                   # what . prints here is whatever the free cell holds
check(". on an empty stack", say(e, ".").split(" ", 1)[1], ".? EMPTY STACK\r\n")
e = t([": PUSHES 0 DO I LOOP ;", "56 PUSHES"], "", "56 numbers fit on the stack")
ask = lambda e, line, want, what=None, ok="OK": check(what or line, say(e, line), want + ok + "\r\n")
ask(e, "+ DROP . 12345678 . -1. D.", "53 12345678 -1 ", "and the interpreter still has room to work")
err([": PUSHES 0 DO I LOOP ;", "57 PUSHES"], "PUSHES? FULL STACK", "one more is a full stack")
e = err([": PUSHES 0 DO I LOOP ;", "60 PUSHES"], "PUSHES? FULL STACK")
ask(e, "DROP DROP 1 2 + .", "3 ", "and the machine goes on after it")
err("IF", "IF? COMPILATION ONLY, USE IN DEFINITION", "compilation only")
err([": T : ;"], ":? EXECUTION ONLY", "execution only")
err([": T 1 IF ;"], ";? DEFINITION NOT FINISHED", "a definition not finished")
err([": T THEN ;"], "THEN? CONDITIONALS NOT PAIRED", "conditionals not paired")
err([": T BEGIN LOOP ;"], "LOOP? CONDITIONALS NOT PAIRED")
t([": T 1", "2 + . ;", "T"], "3 ", "a definition over two lines")
t([": T FOO", "1 2 + ."], "3 ", "an error leaves the compiler")
err("-->", "-->? USE ONLY WHEN LOADING", "--> is for a screen that is being loaded")
err("' NOPE", "NOPE? ")
err(["-1 WARNING !", "FOO"], "\r\nfig-FORTH RISC-V", "WARNING below 0: an error aborts")

# ---------------------------------------------------------------- FORGET, vocabularies

e = t([": A 1 ;", "HERE", ": B 2 ;", "FORGET B", "HERE = . A ."], "1 1 ")
check("FORGET takes the word out", say(e, "B"), "B? \r\n")
err("FORGET DUP", "DUP? IN PROTECTED DICTIONARY", "the kernel is below FENCE")
err("FORGET NOPE", "NOPE? ")
err(["VOCABULARY V IMMEDIATE", "V DEFINITIONS", ": X 7 ;", "X . 2 DUP + .", "FORTH DEFINITIONS X"],
  "X? ", "a word of another vocabulary is not seen from FORTH")
t(["VOCABULARY V IMMEDIATE", "V DEFINITIONS", ": X 7 ;", "FORTH DEFINITIONS", ": Y V X FORTH ;",
   "Y ."], "7 ")
err(["VOCABULARY V IMMEDIATE", "V DEFINITIONS", "FORTH", "FORGET DUP"], "FORGET? DECLARE VOCABULARY",
    "FORGET wants CONTEXT and CURRENT the same")
t(["VOCABULARY V IMMEDIATE", "VOC-LINK @ ' V 12 + = . ' V 12 + @ %d = ." % (RAM + 5 * CELL)],
  "1 1 ", "the vocabulary link")

e = copy.deepcopy(BOOTED)
out = say(e, "VLIST")
check("VLIST starts with the newest word", out.split()[:3], ["WHERE", "EDITOR", "LINE"])
check("VLIST ends with the oldest", out.split()[-3:], ["EXECUTE", "LIT", "OK"])
check("VLIST shows every word", len(out.split()), len(WORDS) + 1)  # and OK
check("VLIST keeps to the line", max(len(l) for l in out.split("\r\n")) < 80, True)
check("a key stops VLIST", len(keys(e, b"VLIST\rX").split()) < 12, True)

# ---------------------------------------------------------------- the disc

LO, HI, B_BUF = 0x4000, 0xF800, 256

def screen(e, n, lines):
    """Put a screen on the disc: 16 lines of 64 characters."""
    text = b"".join(l.encode().ljust(64) for l in lines).ljust(1024)
    assert len(text) == 1024
    e.f[LO + 1024 * n:LO + 1024 * (n + 1)] = text

def disc(*screens):
    """A machine with these (number, lines) screens on its disc."""
    e = copy.deepcopy(BOOTED)
    for n, lines in screens:
        screen(e, n, lines)
    return e

def block(e, n):
    return bytes(e.f[LO + B_BUF * n:LO + B_BUF * (n + 1)])

def ask(e, line, want, what=None, ok="OK"):
    check(what or line, say(e, line), want + ok + "\r\n")

FLUSH = "EDITOR"                            # FLUSH is a word of the editor

check("the disc starts above the kernel", len(IMAGE) <= LO, True)
t("B/BUF . B/SCR . LIMIT FIRST - B/BUF 8 + / . LO . HI .", "256 4 3 16384 63488 ")
t("USE @ FIRST = . PREV @ FIRST = . OFFSET @ .", "1 1 0 ")

e = copy.deepcopy(BOOTED)
e.f[LO + 256] = 65
ask(e, "1 BLOCK C@ . 1 BLOCK 255 + C@ .", "65 255 ", "BLOCK reads the flash")
before = bytes(e.f)
ask(e, "66 1 BLOCK C! UPDATE", "")
ask(e, "2 BLOCK DROP 1 BLOCK C@ .", "66 ", "a changed block stays in its buffer")
check("and is not on the disc yet", bytes(e.f), before)
ask(e, "2 BLOCK DROP 3 BLOCK DROP 4 BLOCK DROP 5 BLOCK DROP", "")
check("until its buffer is wanted: then it is written", block(e, 1), b"B" + b"\xff" * 255)
check("and nothing else is", bytes(e.f[:LO + 256]) + bytes(e.f[LO + 512:]),
      before[:LO + 256] + before[LO + 512:])
ask(e, "1 BLOCK C@ .", "66 ", "and read again")

e = copy.deepcopy(BOOTED)
say(e, FLUSH)
ask(e, "1 BLOCK B/BUF BLANKS 67 1 BLOCK C! UPDATE", "")
ask(e, "183 BLOCK B/BUF 68 FILL UPDATE FLUSH", "")
check("FLUSH writes the changed buffers", (block(e, 1), block(e, 183)),
      (b"C" + b" " * 255, b"D" * 256))
check("the kernel is as it was", bytes(e.f[:len(IMAGE)]), IMAGE)
flash = bytes(e.f)
e = Emu(IMAGE, b"")                         # power off and on: the RAM is gone
e.f[:] = flash
e.ram[:] = b"\xa5" * len(e.ram)
run_to_idle(e)
ask(e, "1 BLOCK C@ . 183 BLOCK C@ .", "67 68 ", "the disc keeps it without power")
ask(e, "2 BLOCK DROP 3 BLOCK DROP 4 BLOCK DROP 5 BLOCK DROP 6 BLOCK DROP", "")
check("a cold start empties the buffers: nothing is written from them", bytes(e.f), flash)

err("184 BLOCK", "BLOCK? DISC RANGE ?", "past the end of the disc")
err("-1 BLOCK", "BLOCK? DISC RANGE ?", "before its start is the kernel")
e = copy.deepcopy(BOOTED)
before = bytes(e.f)
ask(e, "FIRST 4 + 0 BLOCK-WRITE . FIRST 4 + LO 1+ BLOCK-WRITE .", "1 1 ",
    "BLOCK-WRITE refuses what is not a block of the disc")
ask(e, "FIRST 4 + HI BLOCK-WRITE . FIRST 4 + LO B/BUF - BLOCK-WRITE .", "1 1 ")
ask(e, "FIRST 5 + LO BLOCK-WRITE .", "1 ", "and a source that is off the cell")
check("and writes nothing", bytes(e.f), before)
ask(e, "FIRST 4 + LO BLOCK-WRITE .", "0 ")
for first in ["", "2 BLOCK DROP", "2 BLOCK DROP 3 BLOCK DROP", "2 BLOCK DROP 3 BLOCK DROP 4 BLOCK DROP"]:
    e = copy.deepcopy(BOOTED)
    say(e, FLUSH)
    say(e, first)
    say(e, "69 9 BLOCK C! UPDATE FLUSH")
    check("FLUSH after: " + first, block(e, 9)[0], 69)
e = copy.deepcopy(BOOTED)
e.flash_stuck = {LO + 256: 0}               # a worn-out byte
say(e, FLUSH)
ask(e, "67 1 BLOCK C! UPDATE FLUSH", "FLUSH? DISC ERROR", "the flash did not take the block", ok="")

SQ = [": SQ DUP * ;", "7 SQ .", "", "( THE LAST LINE OF THE FIRST BLOCK ) 1 .", "2 .", "", "", "",
      "", "", "", "", "", "", "", "3 ."]
e = disc((1, SQ))
ask(e, "1 LOAD", "49 1 2 3 ", "LOAD goes through the four blocks of a screen")
ask(e, "BLK @ . 9 SQ .", "0 81 ", "and comes back to the terminal")
e = disc((1, ["1 .", "-->"] + [""] * 13 + ["99 ."]), (2, ["2 ."]))
ask(e, "1 LOAD", "1 2 ", "--> goes on with the next screen")
e = disc((1, [": A 3 LOAD ; A 5 ."]), (3, ["4 ."]))
ask(e, "1 LOAD", "4 5 ", "a screen may load another")
e = disc((3, ["1 .", " FOO"]))
ask(e, "3 LOAD", "1 FOO? ", "an error on a screen", ok="")
ask(e, ". . BLK @ .", "12 69 0 ", "leaves where it was: BLK and IN")

e = disc((1, SQ))
want = "\r\nSCR # 1 " + "".join("\r\n%3d %s" % (i, l) for i, l in enumerate(SQ)) + "\r\n"
ask(e, "1 LIST", want)
ask(e, "SCR @ .", "1 ")
ask(e, "1 1 .LINE", "7 SQ .")
e = disc((1, ["( ONE )"]), (2, ["( TWO )"]), (3, ["( THREE )"]))
ask(e, "1 3 INDEX", "\x0c\r\n\r\n  1 ( ONE )\r\n  2 ( TWO )\r\n  3 ( THREE )")
out = say(e, "4 TRIAD")
check("TRIAD lists the three screens of the page", [l for l in out.split("\r\n") if "SCR #" in l],
      ["SCR # 3 ", "SCR # 4 ", "SCR # 5 "])
check("and ends with message 15", out.endswith("\r\nFORTH INTEREST GROUP\r\nOK\r\n"), True)

e = copy.deepcopy(BOOTED)
ask(e, "WARNING @ .", "1 ", "the system starts with WARNING 1")
ask(e, "DROP", "DROP? EMPTY STACK", "with WARNING 1 a message is a line of screen 4", ok="")
ask(e, "IF", "IF? COMPILATION ONLY, USE IN DEFINITION", "and message 17 is line 1 of screen 5", ok="")
ask(e, ": DUP ;", "DUP ISN'T UNIQUE ")
ask(e, "FOO", "FOO? ", "message 0 is nothing", ok="")
e = copy.deepcopy(BOOTED)
ask(e, "0 WARNING !", "")
ask(e, "DROP", "DROP? MSG # 1 ", "with WARNING 0 a message is its number", ok="")
ask(e, "FOO", "FOO? MSG # 0 ", ok="")

# ---------------------------------------------------------------- the editor

def edit(lines, e=None):
    """Type the lines at the editor; returns the machine and the last answer."""
    e = e or copy.deepcopy(BOOTED)
    say(e, "EDITOR")
    for line in lines:
        out = say(e, line)
    return e, out

def shown(text, n):
    """What M types: the line with _ at the cursor, and the line number."""
    return "\r\n " + text.ljust(65) + "%d OK\r\n" % n

def lines_of(e, n):
    """The lines of screen n as they are on the disc, without the blanks at the end."""
    scr = bytes(e.f[LO + 1024 * n:LO + 1024 * (n + 1)])
    return [scr[i:i + 64].decode("latin-1").rstrip(" ") for i in range(0, 1024, 64)]

err("FLUSH", "FLUSH? ", "the editor's words are not seen from FORTH")

START = ["1 CLEAR", "0 P : SQ DUP * ;", "1 P 7 SQ ."]
e, out = edit(START + ["FLUSH"])
check("CLEAR, P and FLUSH: the screen is on the disc", lines_of(e, 1), [": SQ DUP * ;", "7 SQ ."] + [""] * 14)
check("the kernel is as it was after editing", bytes(e.f[:len(IMAGE)]), IMAGE)
ask(e, "1 LOAD", "49 ", "and can be loaded")
e, out = edit(START + ["L"])
check("L lists the screen and shows the cursor",
      out, "\r\nSCR # 1 " + "".join("\r\n%3d %s" % (i, l) for i, l in enumerate([": SQ DUP * ;", "7 SQ ."] + [""] * 14))
      + "\r\n" + shown("_: SQ DUP * ;", 0))
e, out = edit(START + ["1 T"])
check("T types a line", out, shown("_7 SQ .", 1))
e, out = edit(START + ["TOP 5 M"])
check("M moves the cursor", out, shown(": SQ _DUP * ;", 0))
e, out = edit(START + ["TOP F DUP"])
check("F finds a text: the cursor is after it", out, shown(": SQ DUP_ * ;", 0))
e, out = edit(START + ["TOP F SQ", "N"])
check("N finds the next one", out, shown("7 SQ_ .", 1))
e, out = edit(START + ["TOP F DUP", "B"])
check("B goes back over it", out, shown(": SQ _DUP * ;", 0))
e, out = edit(START + ["TOP F DUP", "C  ROT"])
check("C puts text in at the cursor", out, shown(": SQ DUP ROT_ * ;", 0))
e, out = edit(START + ["TOP X DUP "])
check("X finds a text and deletes it", out, shown(": SQ _* ;", 0))
e, out = edit(START + ["TOP F SQ", "TILL *"])
check("TILL deletes from the cursor to the end of a text", out, shown(": SQ_ ;", 0))
e, out = edit(START + ["TOP F NOPE"])
check("a text that is not on the screen", out, "NOPE? \r\n")
ask(e, "DROP DROP R# @ .", "0 ", "leaves the cursor at the top")
e, out = edit(START + ["0 D", "FLUSH"])
check("D deletes a line", lines_of(e, 1), ["7 SQ ."] + [""] * 15)
e, out = edit(START + ["0 D", "1 I", "FLUSH"])
check("and I inserts the line that was held", lines_of(e, 1), ["7 SQ .", ": SQ DUP * ;"] + [""] * 14)
e, out = edit(START + ["0 H 3 R", "FLUSH"])
check("H holds a line and R replaces one with it", lines_of(e, 1),
      [": SQ DUP * ;", "7 SQ .", "", ": SQ DUP * ;"] + [""] * 12)
e, out = edit(START + ["15 P LAST", "0 S", "FLUSH"])
check("S spreads the lines; the last is lost", lines_of(e, 1), ["", ": SQ DUP * ;", "7 SQ ."] + [""] * 13)
e, out = edit(START + ["1 E", "FLUSH"])
check("E erases a line", lines_of(e, 1), [": SQ DUP * ;"] + [""] * 15)
e, out = edit(START + ["FLUSH", "1 2 COPY"])
check("COPY copies a screen, and flushes", lines_of(e, 2), lines_of(e, 1))
check("and the first is there too", lines_of(e, 1), [": SQ DUP * ;", "7 SQ ."] + [""] * 14)
e, out = edit(START + ["16 T"])
check("a line that is not on the screen", out, "T? OFF CURRENT EDITING SCREEN\r\n")
e, out = edit(["PAD 20 BLANKS 65 PAD C! 66 PAD 1+ C! 67 PAD 9 + C!",
               "PAD 10 PAD 1 MATCH . . PAD 10 PAD 9 + 1 MATCH . . PAD 10 HERE 0 MATCH . ."])
check("MATCH finds a text", out, "1 1 10 1 0 1 OK\r\n")
e, out = edit(["PAD 20 BLANKS 65 PAD C! 66 PAD 1+ C! 67 PAD 10 + C!",
               "PAD 10 PAD 10 + 1 MATCH . . PAD 1 PAD 2 MATCH . ."])
check("MATCH does not look past the characters it was given", out, "10 0 1 0 OK\r\n")

e = disc((3, ["1 .", "2 . FOO 3 ."]))
say(e, "3 LOAD")
check("WHERE shows the place of an error in a LOAD", say(e, "WHERE"),
      "SCR # 3 \r\n2 . FOO 3 ." + " " * 53 + "\r\n" + " " * 3 + "^\r\n")
# (the mark is under the end of FOO less the length of the word at HERE, which
# the model takes to be the word in error: typed at the terminal it is WHERE)
ask(e, "SCR @ . 1 T", "3 " + shown("_2 . FOO 3 .", 1)[:-len("OK\r\n")], "and enters the editor")

# ---------------------------------------------------------------- the assembler in Forth

# tools/forth-assembler.f goes on the last four screens, as on the board
# (MANUAL.txt section 16). Each instruction is compared with what bronzebeard
# makes of the same instruction, and the manual's examples are run.
import re, tempfile
ASM = open(os.path.join(ROOT, "tools", "forth-assembler.f")).read().rstrip("\n").split("\n")
ASM_SCR = 42
check("forth-assembler.f is four screens", len(ASM), 64)
check("no line of it runs into the next on a screen", max(len(l) for l in ASM) <= 63, True)
check("each of the first three ends in -->", [ASM[16 * k + 15] for k in range(3)], ["-->"] * 3)
e = disc(*[(ASM_SCR + k, ASM[16 * k:16 * k + 16]) for k in range(4)])
ask(e, "%d LOAD" % ASM_SCR, ";CODE ISN'T UNIQUE ", "the assembler loads from the disc")
ask(e, "BASE @ . CONTEXT @ CURRENT @ = .", "10 1 ", "and leaves DECIMAL and FORTH")
ASMED = e

# (Forth, bronzebeard); {k} is the address of instruction k
CASES = [
    ("A1 A2 A3 ADD,", "add a1, a2, a3"), ("A1 A2 A3 SUB,", "sub a1, a2, a3"),
    ("A1 A2 A3 SLL,", "sll a1, a2, a3"), ("A1 A2 A3 SLT,", "slt a1, a2, a3"),
    ("A1 A2 A3 SLTU,", "sltu a1, a2, a3"), ("A1 A2 A3 XOR,", "xor a1, a2, a3"),
    ("A1 A2 A3 SRL,", "srl a1, a2, a3"), ("A1 A2 A3 SRA,", "sra a1, a2, a3"),
    ("A1 A2 A3 OR,", "or a1, a2, a3"), ("T0 A5 IP AND,", "and t0, a5, s1"),
    ("A1 A2 -5 ADDI,", "addi a1, a2, -5"), ("A1 A2 7FF SLTI,", "slti a1, a2, 0x7ff"),
    ("A1 A2 -800 SLTIU,", "sltiu a1, a2, -2048"), ("A1 A2 -1 XORI,", "xori a1, a2, -1"),
    ("A1 A2 F0 ORI,", "ori a1, a2, 0xf0"), ("A1 A2 FF ANDI,", "andi a1, a2, 0xff"),
    ("A1 A2 3 SLLI,", "slli a1, a2, 3"), ("A1 A2 1F SRLI,", "srli a1, a2, 31"),
    ("A1 A2 1F SRAI,", "srai a1, a2, 31"), ("RA A1 8 JALR,", "jalr ra, a1, 8"),
    ("A1 -1 A2 LB,", "lb a1, -1(a2)"), ("A1 2 A2 LH,", "lh a1, 2(a2)"),
    ("A1 7FC DSP LW,", "lw a1, 2044(s0)"), ("A1 3 A2 LBU,", "lbu a1, 3(a2)"),
    ("A1 -2 A2 LHU,", "lhu a1, -2(a2)"),
    ("A1 -800 A2 SB,", "sb a1, -2048(a2)"), ("A1 7FE A2 SH,", "sh a1, 2046(a2)"),
    ("IP 4 RSP SW,", "sw s1, 4(tp)"),
    ("A1 A2 {0} BEQ,", "beq a1, a2, L0"), ("A1 A2 {40} BNE,", "bne a1, a2, L40"),
    ("A1 A2 {3} BLT,", "blt a1, a2, L3"), ("A1 A2 {33} BGE,", "bge a1, a2, L33"),
    ("A1 A2 {5} BLTU,", "bltu a1, a2, L5"), ("A1 A2 {35} BGEU,", "bgeu a1, a2, L35"),
    ("A1 40013 LUI,", "lui a1, 0x40013"), ("A1 FFFFF AUIPC,", "auipc a1, 0xfffff"),
    ("RA {1} JAL,", "jal ra, L1"), ("ZERO {40} JAL,", "jal zero, L40"),
    ("{20} J,", "jal zero, L20"), ("T0 JR,", "jalr zero, t0, 0"),
    ("A1 A2 MV,", "addi a1, a2, 0"),
]
with tempfile.TemporaryDirectory() as d:
    src = "".join("L%d:\n    %s\n" % (k, b) for k, (_, b) in enumerate(CASES)) + "L%d:\n" % len(CASES)
    open(os.path.join(d, "cases.asm"), "w").write(src)
    r = subprocess.run(["bronzebeard", "-o", os.path.join(d, "cases.bin"), os.path.join(d, "cases.asm")],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("bronzebeard failed on the cases:\n" + r.stdout + r.stderr)
    want = open(os.path.join(d, "cases.bin"), "rb").read()
e = copy.deepcopy(ASMED)
say(e, "0 VARIABLE B0  HERE B0 !  ASSEMBLER HEX")
start = int(say(e, "DECIMAL HERE . HEX").split()[0])
for f, b in CASES:      # a hex address is written 0A0, not A0: that is the register
    say(e, re.sub(r"\{(\d+)\}", lambda m: "B0 @ 0%X +" % (4 * int(m.group(1))), f))
for k, (f, b) in enumerate(CASES):
    check("%s is %s" % (f, b), "%08X" % peek(e, start + 4 * k),
          "%08X" % int.from_bytes(want[4 * k:4 * k + 4], "little"))

def asm(lines, want, what):
    """Type the lines at the machine with the assembler loaded."""
    e = copy.deepcopy(ASMED)
    for line in lines[:-1]:
        check(what + ": " + line, say(e, line), "OK\r\n")
    check(what, say(e, lines[-1]), want + "OK\r\n")

asm(["CODE 2*  A1 0 DSP LW,  A1 A1 A1 ADD,  A1 PUT,  END-CODE", "21 2* ."], "42 ", "a CODE word")
asm(["CODE TWO  A1 ZERO 2 ADDI,  A1 PUSH,  END-CODE", "TWO TWO + ."], "4 ", "PUSH,")
asm(["CODE SGN  A1 0 DSP LW,",
     "  A1 ZERO LT IF,  A1 ZERO -1 ADDI,  ELSE,  A1 ZERO 1 ADDI,  THEN,",
     "  A1 PUT,  END-CODE", "-5 SGN . 5 SGN ."], "-1 1 ", "IF, ELSE, THEN,")
asm(["CODE SUMTO ( n -- 1+2+...+n )  A1 0 DSP LW,  A2 ZERO MV,",
     "  BEGIN,  A2 A2 A1 ADD,  A1 A1 -1 ADDI,  A1 ZERO EQ UNTIL,",
     "  A2 PUT,  END-CODE", "10 SUMTO ."], "55 ", "BEGIN, UNTIL,")
asm(["CODE BITS ( n -- the number of 1 bits )",
     "  A1 0 DSP LW,  A2 ZERO MV,",
     "  BEGIN,  A1 ZERO NE WHILE,",
     "    A3 A1 1 ANDI,  A2 A2 A3 ADD,  A1 A1 1 SRLI,",
     "  REPEAT,  A2 PUT,  END-CODE", "255 BITS . -1 BITS . 0 BITS ."], "8 32 0 ", "WHILE, REPEAT,")
asm([": CON  CREATE SMUDGE ,  ;CODE  A1 4 W LW,  A1 PUSH,  END-CODE",
     "1234 CON X", "X . CONTEXT @ CURRENT @ = ."], "1234 1 ", ";CODE ... END-CODE")
e = copy.deepcopy(ASMED)
check("an IF, without THEN, is error 20 at END-CODE",
      say(e, "CODE BAD  A1 ZERO NE IF,  END-CODE"), "END-CODE? DEFINITION NOT FINISHED\r\n")

# ---------------------------------------------------------------- cold and warm

e = err([": T 5 ;", "COLD"], "\r\nfig-FORTH RISC-V", "COLD")
check("COLD forgets the new words", say(e, "T"), "T? \r\n")
check("COLD puts the dictionary pointer back", say(e, "HERE ."), "%d OK\r\n" % (RAM + 6 * CELL))
e = t([": T 5 ;", "HEX"], "")
e.pc = L["origin"] + 4
run_to_idle(e)
check("a warm start keeps the new words and sets the base", say(e, "T 16 + ."), "21 OK\r\n")

# ---------------------------------------------------------------- the image

check("the image fits the first 16 KiB", len(IMAGE) < 16384, True)
print("%d checks, %d failed; image %d bytes, %d words" % (count, failed, len(IMAGE), len(WORDS)))
sys.exit(1 if failed else 0)
