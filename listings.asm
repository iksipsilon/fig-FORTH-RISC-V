# fig-FORTH for RISC-V: the listings
#
# The high-level words of the model: colon definitions, written as threads.
# No machine instructions here; those are in figforth.asm (the nucleus) and in
# the board file. figforth.asm includes this file at its end, so the words
# here follow the nucleus in the dictionary.
#
# A word is its header (python3 tools/header.py NAME label previous docol),
# then one code field address per `dw`, and %offset(label) after each branch.
# When a word with a header is added at the end, move `last_nfa:` from
# figforth.asm to the name field of that word.


# ------------------------------------------------------------------------
# A STAND-IN FOR ABORT
#
# The model's ABORT (SCR 54) ends in QUIT, the text interpreter. Until the
# high-level words are here, this prints a line and echoes the keys, which
# shows that the inner interpreter runs on the chip. It is also an example of
# a colon definition written by hand: docol in the code field, one code field
# address per cell, and %offset after each branch.
#
#   : ABORT  SP!  CR  banner1 banner DO  I C@ EMIT  LOOP  CR
#            BEGIN  KEY DUP EMIT  13 XOR 0=  IF  10 EMIT  ENDIF  AGAIN ;

align 4
abort:
    dw docol
    dw spsto
    dw cr
    dw lit
    dw banner1
    dw lit
    dw banner
    dw xdo
abort1:
    dw ido
    dw cat
    dw emit
    dw xloop
    dw %offset(abort1)
    dw cr
abort2:
    dw key
    dw dup
    dw emit
    dw lit
    dw 13
    dw xorr
    dw zequ
    dw zbran
    dw %offset(abort2)
    dw lit
    dw 10
    dw emit
    dw bran
    dw %offset(abort2)

banner:
    string fig-FORTH RISC-V nucleus
banner1:
