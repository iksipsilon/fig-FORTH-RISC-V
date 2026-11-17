#!/usr/bin/env python3
"""Write listings.asm from tools/words.py.

    python3 tools/listing.py            (or: make listing)
    python3 tools/listing.py --names    also print the names, for the tests

tools/words.py holds every high-level word as its Forth definition, in the
order of the dictionary. This turns each definition into its thread, one
code field address per `dw`, with the header in front and the definition as
a comment above it, and writes listings.asm. To add or change a word, change
words.py and run this; do not edit listings.asm.

In words.py:

    section(title, notes ...)                 a heading
    colon(name, label, what, text)            a colon definition
    colon(..., imm=True)                      an IMMEDIATE one
    colon(..., code=assembly)                 one that ends in ;CODE: the
                                              machine code follows the thread
    con(name, label, value, what)             a CONSTANT
    user(name, label, offset, what)           a USER variable
    codeword(name, label, what, assembly)     a CODE word
    raw(text)                                 lines for the assembler, as given
    voc = "editor"  /  voc = "forth"          the vocabulary of what follows

In the text of a definition: IF ELSE ENDIF (or THEN), BEGIN UNTIL AGAIN
WHILE REPEAT, DO LOOP +LOOP, ." text", COMPILE x and [COMPILE] x are done
here, as the compiler would. A number is LIT and the number; {expression}
is LIT and an expression of the assembler (a label, a constant). Any other
word must be a word of the nucleus or of words.py; it may come later in the
file. In a word of the EDITOR vocabulary a name is looked up among the
editor words before it, then in FORTH, and FORTH in the text turns that
round, as it does at the terminal.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from header import header, PLAIN

# Forth name -> label of the code field: the nucleus
LAB = {"LIT": "lit", "EXECUTE": "exec", "BRANCH": "bran", "0BRANCH": "zbran",
       "(LOOP)": "xloop", "(+LOOP)": "xploo", "(DO)": "xdo", "I": "ido", "DIGIT": "digit",
       "(FIND)": "pfind", "UPPER": "upper", "ENCLOSE": "encl", "EMIT": "emit", "KEY": "key",
       "?TERMINAL": "qterm", "CR": "cr", "CMOVE": "cmove", "U*": "ustar", "U/": "uslas",
       "AND": "andd", "OR": "orr", "XOR": "xorr", "SP@": "spat", "SP!": "spsto",
       "RP!": "rpsto", ";S": "semis", "LEAVE": "leave", ">R": "tor", "R>": "fromr",
       "R": "rr", "0=": "zequ", "0<": "zless", "+": "plus", "D+": "dplus",
       "MINUS": "minus", "DMINUS": "dminu", "OVER": "over", "DROP": "drop",
       "SWAP": "swap", "DUP": "dup", "+!": "pstor", "TOGGLE": "toggl", "@": "at",
       "C@": "cat", "!": "store", "C!": "cstor", "S->D": "stod"}

out = []
prev = "stod"
names = []
voc = "forth"       # the vocabulary the words being written go into
ELAB = {}           # the EDITOR vocabulary: name -> label
enames = []
eprev = None

def emit(s=""):
    out.append(s)

def section(title, *notes):
    emit()
    emit("# " + "-" * 72)
    emit("# " + title)
    if notes:
        emit("#")
        for n in notes:
            emit(("# " + n).rstrip())
    emit()

def head(name, label, code, imm, what, src=()):
    global prev, eprev
    shown = "null" if name == "\0" else name
    emit("# %s  %s" % (shown, what))
    for line in src:
        emit("#   " + line)
    if voc == "editor":
        assert name not in ELAB, name
        for l in header(name, label, eprev or "@@", code, imm).split('\n'):
            emit(l.replace("dw n_@@", "dw FORTH_VOC                # the blank name of FORTH: on into FORTH"))
        ELAB[name] = label
        enames.append(name)
        eprev = label
        return
    assert name not in LAB, name
    for l in header(name, label, prev, code, imm).split('\n'):
        emit(l)
    LAB[name] = label
    names.append(name)
    prev = label

def con(name, label, value, what):
    head(name, label, "docon", False, what)
    emit("    dw %s" % value)
    emit()

def user(name, label, offset, what):
    head(name, label, "douse", False, what)
    emit("    dw 0x%02X" % offset)
    emit()

def codeword(name, label, what, asm):
    head(name, label, None, False, what)
    for l in asm.strip("\n").split("\n"):
        emit(l)
    emit()

def raw(text):
    for l in text.strip("\n").split("\n"):
        emit(l)
    emit()

pending = []      # colon bodies are compiled after all labels are known

def colon(name, label, what, src, imm=False, code=None):
    lines = [l.strip() for l in src.strip().split("\n")]
    shown = "null" if name == "\0" else name
    first = ": %s  " % shown
    lines_shown = [re.sub(r"\{([^}]*)\}", r"\1", l) for l in lines]
    disp = [first + lines_shown[0]] + [" " * len(first) + l for l in lines_shown[1:]]
    disp[-1] += ("  ;CODE  the code below" if code else " ;") + ("  IMMEDIATE" if imm else "")
    head(name, label, "docol", imm, what, disp)
    pending.append((len(out), label, " ".join(lines), code, dict(ELAB) if voc == "editor" else None))
    emit()

def body(label, src, code=None, ed=None):
    """Compile a definition's text to dw lines. For a word of the EDITOR
    vocabulary, ed holds the editor words that were there before it: a name
    is looked up there first, then in FORTH, and the other way round after a
    FORTH in the text, as CONTEXT and CURRENT do it."""
    res = []
    ctx = ["editor"]
    def find(t):
        if ed is None:
            return LAB.get(t)
        a, b = (ed, LAB) if ctx[0] == "editor" else (LAB, ed)
        return a.get(t) or b.get(t)
    n = [0]
    def new():
        n[0] += 1
        return "%s%d" % (label, n[0])
    def dw(x):
        res.append("    dw %s" % x)
    def lab(l):
        res.append("%s:" % l)
    cs = []
    toks = src.split(" ")
    i = 0
    while i < len(toks):
        t = toks[i]
        i += 1
        if t == "":
            continue
        if t == '."':                       # text up to the closing quote
            j = i
            while not toks[j].endswith('"'):
                j += 1
            s = " ".join(toks[i:j + 1])[:-1]
            i = j + 1
            dw("pdotq")
            res.append("    db %d" % len(s))
            if set(s) <= PLAIN | {" "}:
                core = s.strip(" ")
                lead = len(s) - len(s.lstrip(" "))
                trail = len(s) - len(s.rstrip(" "))
                if lead:
                    res.append("    bytes %s" % " ".join(["0x20"] * lead))
                res.append("    string %s" % core)
                if trail:
                    res.append("    bytes %s" % " ".join(["0x20"] * trail))
            else:
                res.append("    bytes %s" % " ".join("0x%02X" % ord(c) for c in s))
                res[-1] += "    # " + s
            res.append("align 4")
        elif t.startswith("{"):             # an address or a number of the assembler
            dw("lit"); dw(t[1:-1])
        elif t == "COMPILE":
            dw("comp"); dw(find(toks[i])); i += 1
        elif t == "[COMPILE]":
            dw(find(toks[i])); i += 1
        elif ed is not None and t in ("FORTH", "EDITOR"):
            ctx[0] = t.lower()              # immediate: nothing is compiled
        elif t == "IF":
            l = new(); dw("zbran"); dw("%%offset(%s)" % l); cs.append(("if", l))
        elif t == "ELSE":
            k, l = cs.pop(); assert k == "if"
            l2 = new(); dw("bran"); dw("%%offset(%s)" % l2); lab(l); cs.append(("if", l2))
        elif t in ("THEN", "ENDIF"):
            k, l = cs.pop(); assert k == "if"; lab(l)
        elif t == "BEGIN":
            l = new(); lab(l); cs.append(("begin", l))
        elif t == "UNTIL":
            k, l = cs.pop(); assert k == "begin"; dw("zbran"); dw("%%offset(%s)" % l)
        elif t == "AGAIN":
            k, l = cs.pop(); assert k == "begin"; dw("bran"); dw("%%offset(%s)" % l)
        elif t == "WHILE":
            l = new(); dw("zbran"); dw("%%offset(%s)" % l); cs.append(("while", l))
        elif t == "REPEAT":
            k, l = cs.pop(); assert k == "while"
            k2, l2 = cs.pop(); assert k2 == "begin"
            dw("bran"); dw("%%offset(%s)" % l2); lab(l)
        elif t == "DO":
            l = new(); dw("xdo"); lab(l); cs.append(("do", l))
        elif t in ("LOOP", "+LOOP"):
            k, l = cs.pop(); assert k == "do"
            dw("xloop" if t == "LOOP" else "xploo"); dw("%%offset(%s)" % l)
        elif t == "DOES>":
            dw(LAB["DOES>"])
        elif find(t):
            dw(find(t))
        else:
            v = int(t, 0)                   # a number
            dw("lit"); dw(t)
    assert not cs, (label, cs)
    if code:                                # ;CODE: the machine code follows
        dw("pscod")
        res.extend(code.strip("\n").split("\n"))
    else:
        dw("semis")
    return res

exec(compile(open(os.path.join(ROOT, "tools", "words.py")).read(), "words.py", "exec"))

# compile the bodies, last first so the insert positions stay right
for pos, label, src, code, ed in reversed(pending):
    out[pos:pos] = body(label, src, code, ed)

# last_nfa stands on the newest word
i = max(k for k, l in enumerate(out) if l == "n_%s:" % prev)
out.insert(i + 1, "last_nfa:")
if eprev:
    i = max(k for k, l in enumerate(out) if l == "n_%s:" % eprev)
    out.insert(i + 1, "last_enfa:")

text = "\n".join(l.rstrip() for l in "\n".join(out).split("\n")).rstrip() + "\n"
open(os.path.join(ROOT, "listings.asm"), "w").write(text)
print("listings.asm: %d words in FORTH, %d in EDITOR" % (len(names), len(enames)))
if "--names" in sys.argv:
    print("NAMES =", names)
    print("EDITOR_NAMES =", enames)
