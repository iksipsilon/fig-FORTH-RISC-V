#!/usr/bin/env python3
"""Print the header of a word for figforth.asm.

bronzebeard has no macros, so every header is written out. This prints one,
ready to paste:

    python3 tools/header.py NAME LABEL PREVIOUS [CODE] [-i]

NAME      the Forth name, e.g. '(+LOOP)'  (quote it for the shell)
LABEL     the label of the code field, e.g. xploo  (the name field is n_xploo)
PREVIOUS  the label of the code field of the word before it in the
          dictionary, or 0 for the first word
CODE      what the code field holds: docol, docon, dovar, douse, dodoe, or
          another label; left out, the word is a CODE word and the code
          field points at its own parameter field
-i        the word is IMMEDIATE

The name field is the fig-FORTH one, padded to the cell: a length byte with
bit 7 set (bit 6 = immediate, bit 5 = smudge), the characters, then blanks up
to a cell boundary, and bit 7 set on the last byte.
"""
import sys

CELL = 4

def header(name, label, prev, code=None, immediate=False):
    n = len(name)
    if not 1 <= n <= 31:
        raise SystemExit("a name has 1 to 31 characters")
    if "\\" in name or name != name.strip():
        raise SystemExit("bronzebeard's `string` cannot hold a backslash or outer blanks")
    out = ["align %d" % CELL, "n_%s:" % label]
    out.append("    db 0x%02X" % (0x80 | (0x40 if immediate else 0) | n))
    pad = -(1 + n) % CELL                   # blanks after the name
    if pad == 0:                            # the last character ends the field
        if n > 1:
            out.append("    string %s" % name[:-1])
        out.append("    db 0x%02X%s# %s + 0x80" % (ord(name[-1]) | 0x80, " " * 17, name[-1]))
    else:
        out.append("    string %s" % name)
        blanks = ["0x20"] * (pad - 1) + ["0xA0"]
        out.append("    bytes %s" % " ".join(blanks))
    out.append("    dw %s" % ("0" if prev == "0" else "n_" + prev))
    out.append("%s:" % label)
    out.append("    dw %s" % (code if code else label + " + CELL"))
    return "\n".join(out)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "-i"]
    if len(args) not in (3, 4):
        raise SystemExit(__doc__)
    print(header(*args, immediate="-i" in sys.argv[1:]))
