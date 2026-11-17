# The high-level words of fig-FORTH for RISC-V, as Forth definitions.
# tools/listing.py reads this file and writes listings.asm; its first lines
# say what the calls below mean.

emit("""# fig-FORTH for RISC-V: the listings
#
# THIS FILE IS WRITTEN BY tools/listing.py FROM tools/words.py (make listing).
# Change a word there, not here.
#
# The high-level words of the fig-FORTH model (fig-FORTH Installation Manual,
# Release 1), as the assembly listings of the Forth Interest Group gave them:
# every colon definition written out as its thread, one code field address
# per `dw`. The only machine instructions in this file are the model's own:
# the few behind the ;CODE of : CONSTANT VARIABLE USER and DOES>. The CODE
# words are in figforth.asm (the nucleus), the chip in board.asm.
# figforth.asm includes this file at its end, so these words follow the
# nucleus in the dictionary.
#
# Above each word is its definition in Forth. Numbers there are decimal, and
# a name in small letters (origin) is a label of the assembler: its address
# is put on the stack.
# Where a definition is not the model's, the note above it says why. The
# reasons are always the same three:
#
#   the cell     is 4 bytes: a link, code or parameter field is 4 bytes, and
#                a thread steps by 4
#   alignment    @ and ! trap on an address that is not a multiple of 4, so
#                the dictionary pointer is rounded up after a name or a text
#   flash        the kernel cannot be written, so nothing in it may change.
#                The body of the FORTH vocabulary is in RAM (FORTH_VOC).
#
# The disc is the flash above the kernel; see THE DISC below.
#
# A word is its header (tools/header.py makes it), then the thread.
# `last_nfa:` and `last_enfa:` stand on the name fields of the newest words
# of FORTH and of EDITOR.""")

section("COLON AND SEMICOLON, CONSTANT VARIABLE USER",
        "As in the model, each of the four defining words ends in ;CODE: (;CODE)",
        "points the code field of the new word at the machine code that follows it",
        "in the thread. That code gets W = the code field address from NEXT; the",
        "parameter field is at CELL(W). The kernel's own colon words, constants",
        "and user variables have these labels in their code fields.")

colon(":", "colon", "( -- )  start a colon definition", """
?EXEC !CSP CURRENT @ CONTEXT ! CREATE ]""", imm=True, code="""
docol:                          # a colon definition: nest into its thread
    addi RSP, RSP, -CELL
    sw IP, 0(RSP)
    addi IP, W, CELL
    j next""")
colon(";", "semi", "( -- )  end a colon definition", """
?CSP COMPILE ;S SMUDGE [COMPILE] [""", imm=True)
colon("CONSTANT", "con", "( n -- )  n CONSTANT name: name pushes n", """
CREATE SMUDGE ,""", code="""
docon:                          # a CONSTANT: push its parameter
    lw a1, CELL(W)
    j push""")
colon("VARIABLE", "var", "( n -- )  n VARIABLE name: name pushes the address of a cell that holds n", """
CONSTANT""", code="""
dovar:                          # a VARIABLE: push the address of its parameter
    addi a1, W, CELL
    j push""")
colon("USER", "user", "( n -- )  n USER name: name pushes the user area address + n", """
CONSTANT""", code="""
douse:                          # a USER variable: its parameter is an offset
    lw a1, CELL(W)              # into the user area
    add a1, a1, UP
    j push""")

section("CONSTANTS")
con("0", "zero", "0", "( -- 0 )")
con("1", "one", "1", "( -- 1 )")
con("2", "two", "2", "( -- 2 )")
con("3", "three", "3", "( -- 3 )")
con("BL", "bl", "32", "( -- 32 )  the blank")
con("C/L", "csll", "64", "( -- 64 )  characters in a line")
con("FIRST", "first", "FIRST_INIT", "( -- addr )  the first disc buffer")
con("LIMIT", "limit", "LIMIT_INIT", "( -- addr )  the end of the last disc buffer")
con("B/BUF", "bbuf", "B_BUF", "( -- 256 )  bytes in a block: one page of the flash. The model's disc has 128.")
con("B/SCR", "bscr", "1024 // B_BUF", "( -- 4 )  blocks in a screen")
colon("+ORIGIN", "porig", "( n -- addr )  the address n bytes into the origin table (SCR 12 of the nucleus)", """
{origin} +""")

section("USER VARIABLES",
        "The parameter is the offset into the user area: the model's, doubled.")
for name, label, off, what in [
    ("S0", "szero", 0x0C, "where the data stack starts"),
    ("R0", "rzero", 0x10, "where the return stack starts"),
    ("TIB", "tib", 0x14, "the address of the terminal input buffer"),
    ("WIDTH", "width", 0x18, "the most characters kept of a name"),
    ("WARNING", "warn", 0x1C, "0: messages are numbers; below 0: an error runs (ABORT)"),
    ("FENCE", "fence", 0x20, "FORGET does not go below this address"),
    ("DP", "dp", 0x24, "the dictionary pointer"),
    ("VOC-LINK", "vocl", 0x28, "the newest vocabulary"),
    ("BLK", "blk", 0x2C, "the block being interpreted; 0 is the terminal"),
    ("IN", "inn", 0x30, "the offset into the text being interpreted"),
    ("OUT", "out", 0x34, "characters sent; EMIT counts"),
    ("SCR", "scr", 0x38, "the screen last listed"),
    ("OFFSET", "ofset", 0x3C, "added to block numbers"),
    ("CONTEXT", "cont", 0x40, "the vocabulary searched first"),
    ("CURRENT", "curr", 0x44, "the vocabulary new words go into"),
    ("STATE", "state", 0x48, "0 executing, 192 compiling"),
    ("BASE", "base", 0x4C, "the number base"),
    ("DPL", "dpl", 0x50, "digits after the point of the last number, or -1"),
    ("FLD", "fld", 0x54, "field width; not used"),
    ("CSP", "csp", 0x58, "the stack pointer when the definition began"),
    ("R#", "rnum", 0x5C, "the editor's cursor"),
    ("HLD", "hld", 0x60, "the last character of the number being put out")]:
    user(name, label, off, "( -- addr )  " + what)

section("SMALL WORDS")
colon("1+", "onep", "( n -- n+1 )", "1 +")
colon("2+", "twop", "( n -- n+2 )", "2 +")
colon("HERE", "here", "( -- addr )  the next free address of the dictionary", "DP @")
colon("ALLOT", "allot", "( n -- )  take n bytes of the dictionary", "DP +!")
colon("ALIGN", "alignn", "( -- )  round the dictionary pointer up to a cell. Not in the model.", """
HERE 3 + -4 AND DP !""")
colon(",", "comma", "( n -- )  put a cell into the dictionary. The cell is 4.", "HERE ! 4 ALLOT")
colon("C,", "ccomm", "( b -- )  put a byte into the dictionary", "HERE C! 1 ALLOT")
colon("-", "subb", "( n1 n2 -- n1-n2 )", "MINUS +")
colon("=", "equal", "( n1 n2 -- f )", "- 0=")
colon("<", "less", "( n1 n2 -- f )", "- 0<")
colon(">", "great", "( n1 n2 -- f )", "SWAP <")
colon("ROT", "rot", "( n1 n2 n3 -- n2 n3 n1 )", ">R SWAP R> SWAP")
colon("SPACE", "space", "( -- )", "BL EMIT")
colon("-DUP", "ddup", "( n -- n n | 0 )  duplicate if not zero", "DUP IF DUP THEN")

section("THE FIELDS OF A WORD",
        "From the parameter field: the code field is 4 below, the link field 8, and",
        "the last byte of the name field 9. The model's numbers are 2, 4 and 5.")
colon("TRAVERSE", "trav", "( addr n -- addr )  to the other end of a name field; n is 1 or -1", """
SWAP BEGIN OVER + 127 OVER C@ < UNTIL SWAP DROP""")
colon("LATEST", "lates", "( -- nfa )  the newest word of CURRENT", "CURRENT @ @")
colon("LFA", "lfa", "( pfa -- lfa )", "8 -")
colon("CFA", "cfa", "( pfa -- cfa )", "4 -")
colon("NFA", "nfa", "( pfa -- nfa )", "9 - -1 TRAVERSE")
colon("PFA", "pfa", "( nfa -- pfa )", "1 TRAVERSE 9 +")

section("COMPILER SECURITY")
colon("!CSP", "scsp", "( -- )  note the stack pointer", "SP@ CSP !")
colon("?ERROR", "qerr", "( f n -- )  error n if f is true", "SWAP IF ERROR ELSE DROP THEN")
colon("?COMP", "qcomp", "( -- )  error 17 unless compiling", "STATE @ 0= 17 ?ERROR")
colon("?EXEC", "qexec", "( -- )  error 18 unless executing", "STATE @ 18 ?ERROR")
colon("?PAIRS", "qpair", "( n1 n2 -- )  error 19 if the conditionals do not pair", "- 19 ?ERROR")
colon("?CSP", "qcsp", "( -- )  error 20 if the stack moved since !CSP", "SP@ CSP @ - 20 ?ERROR")
colon("?LOADING", "qload", "( -- )  error 22 unless loading from disc", "BLK @ 0= 22 ?ERROR")

section("COMPILE, THE BRACKETS, SMUDGE, THE BASES, ;CODE")
colon("COMPILE", "comp", "( -- )  put the next word of the thread into the dictionary. The step is 4.", """
?COMP R> DUP 4 + >R @ ,""")
colon("[", "lbrac", "( -- )  stop compiling", "0 STATE !", imm=True)
colon("]", "rbrac", "( -- )  compile", "192 STATE !")
colon("SMUDGE", "smudg", "( -- )  hide or show the newest word", "LATEST 32 TOGGLE")
colon("HEX", "hexx", "( -- )", "16 BASE !")
colon("DECIMAL", "decim", "( -- )", "10 BASE !")
colon("(;CODE)", "pscod", "( -- )  point the newest word's code field at what follows in the thread", """
R> LATEST PFA CFA !""")
colon(";CODE", "semic", "( -- )  end a defining word; machine code follows. There is no assembler\n#        vocabulary yet: the code is put in with , by hand.", """
?CSP COMPILE (;CODE) [COMPILE] [ SMUDGE""", imm=True)

section("<BUILDS AND DOES>")
colon("<BUILDS", "build", "( -- )  start the header of a word that DOES> will finish", "0 CONSTANT")
colon("DOES>", "does", "( -- )  the words after it are what the new word does", """
R> LATEST PFA !""", code="""
dodoe:                          # a word made by <BUILDS ... DOES>: its first
    addi RSP, RSP, -CELL        # parameter is the address of the thread after
    sw IP, 0(RSP)               # DOES>. Nest into that, and push the address
    lw IP, CELL(W)              # of the parameters behind it.
    addi a1, W, 2*CELL
    j push""")

section("TEXT OUTPUT")
colon("COUNT", "count", "( addr -- addr+1 n )", "DUP 1+ SWAP C@")
colon("TYPE", "typee", "( addr n -- )", """
-DUP IF OVER + SWAP DO I C@ EMIT LOOP ELSE DROP THEN""")
colon("-TRAILING", "dtrai", "( addr n -- addr n' )  without the blanks at the end", """
DUP 0 DO OVER OVER + 1 - C@ BL - IF LEAVE ELSE 1 - THEN LOOP""")
colon('(.")', "pdotq", "( -- )  type the text that follows in the thread. The thread goes on at\n#        the next cell boundary: 3 + -4 AND, which the model does not have.", """
R COUNT DUP 1+ R> + 3 + -4 AND >R TYPE""")
colon('."', "dotq", "( -- )  type, or compile, the text up to the next quote. ALIGN after the\n#        compiled text is not the model's.", """
34 STATE @ IF COMPILE (.") WORD HERE C@ 1+ ALLOT ALIGN
ELSE WORD HERE COUNT TYPE THEN""", imm=True)

section("TERMINAL INPUT")
colon("EXPECT", "expec", "( addr n -- )  read a line of up to n characters to addr; nulls end it.\n#        20 +ORIGIN holds the backspace key. The model ends with 0 I 1+ ! which\n#        stores a cell at any address: two C! here.", """
OVER + OVER DO
KEY DUP 20 +ORIGIN @ = IF
DROP 8 OVER I = DUP R> 2 - + >R -
ELSE DUP 13 = IF LEAVE DROP BL 0 ELSE DUP THEN
I C! 0 I 1+ C! 0 I 2+ C!
THEN EMIT LOOP DROP""")
colon("QUERY", "query", "( -- )  read a line of 80 characters to the terminal input buffer", """
TIB @ 80 EXPECT 0 IN !""")
colon("\0", "null", "( -- )  the word whose name is a null: the end of the line, or of a block.\n#        From the terminal it leaves INTERPRET. From the disc it goes on with\n#        the next block, and leaves at the end of the screen: 3 is B/SCR - 1,\n#        where the model has 7.", """
BLK @ IF 1 BLK +! 0 IN ! BLK @ 3 AND 0=
IF ?EXEC R> DROP ENDIF
ELSE R> DROP ENDIF""", imm=True)

section("FILL, HOLD, PAD, WORD")
colon("FILL", "fill", "( addr n b -- )  n is at least 1", """
SWAP >R OVER C! DUP 1+ R> 1 - CMOVE""")
colon("ERASE", "erase", "( addr n -- )", "0 FILL")
colon("BLANKS", "blank", "( addr n -- )", "BL FILL")
colon("HOLD", "hold", "( c -- )  put a character in front of the number being put out", """
-1 HLD +! HLD @ C!""")
colon("PAD", "pad", "( -- addr )  a scratch area, 68 bytes above HERE", "HERE 68 +")
colon("WORD", "wordd", "( c -- )  move the next word of the input, c its delimiter, to HERE: a\n#        length byte, the text, blanks. The input is the block BLK, or the\n#        terminal if BLK is 0.", """
BLK @ IF BLK @ BLOCK ELSE TIB @ ENDIF
IN @ + SWAP ENCLOSE HERE 34 BLANKS IN +!
OVER - >R R HERE C! + HERE 1+ R> CMOVE""")

section("NUMBER INPUT, -FIND")
colon("(NUMBER)", "pnumb", "( d1 addr1 -- d2 addr2 )  take digits from addr1 + 1 on into d", """
BEGIN 1+ DUP >R C@ BASE @ DIGIT WHILE
SWAP BASE @ U* DROP ROT BASE @ U* D+
DPL @ 1+ IF 1 DPL +! THEN R> REPEAT R>""")
colon("NUMBER", "numb", "( addr -- d )  the text at addr + 1 as a double number; a point sets DPL", """
0 0 ROT DUP 1+ C@ 45 = DUP >R + -1
BEGIN DPL ! (NUMBER) DUP C@ BL - WHILE
DUP C@ 46 - 0 ?ERROR 0 REPEAT
DROP R> IF DMINUS THEN""")
colon("-FIND", "dfind", "( -- pfa b 1 | 0 )  look the next word of the input up in CONTEXT, then CURRENT", """
BL WORD HERE CONTEXT @ @ (FIND)
DUP 0= IF DROP HERE LATEST (FIND) THEN""")

section("ERRORS, ID.")
colon("(ABORT)", "pabor", "( -- )", "ABORT")
colon("ERROR", "error", "( n -- in blk )  type the word and the message, empty the stack, leave\n#        IN and BLK on it, go to QUIT", """
WARNING @ 0< IF (ABORT) THEN
HERE COUNT TYPE ." ? " MESSAGE SP! IN @ BLK @ QUIT""")
colon("ID.", "iddot", "( nfa -- )  type a name", """
PAD 32 95 FILL DUP PFA LFA OVER - PAD SWAP CMOVE
PAD COUNT 31 AND TYPE SPACE""")

section("CREATE",
        "The first line is the model's test for a full dictionary: the user area is",
        "the first thing above it. The two ALIGN are this port's: one so that the",
        "name field starts on a cell boundary whatever was allotted before, one so",
        "that the link field does. WORD left blanks after the name, and the last",
        "of them takes bit 7. The model's fields are 2 bytes; HERE 4 + here.")
colon("CREATE", "creat", "( -- )  make the header of a word named by the next word of the input;\n#        its code field points at its parameter field", """
TIB HERE 160 + < 2 ?ERROR
ALIGN -FIND IF DROP NFA ID. 4 MESSAGE SPACE THEN
HERE DUP C@ WIDTH @ MIN 1+ ALLOT ALIGN
DUP 160 TOGGLE HERE 1 - 128 TOGGLE
LATEST , CURRENT @ ! HERE 4 + ,""")

section("[COMPILE], LITERAL, ?STACK")
colon("[COMPILE]", "bcomp", "( -- )  compile the next word of the input even if it is immediate", """
-FIND 0= 0 ?ERROR DROP CFA ,""", imm=True)
colon("LITERAL", "liter", "( n -- )  compiling: compile n as a literal", """
STATE @ IF COMPILE LIT , THEN""", imm=True)
colon("DLITERAL", "dlite", "( d -- )  compiling: compile d as two literals", """
STATE @ IF SWAP [COMPILE] LITERAL [COMPILE] LITERAL THEN""", imm=True)
colon("?STACK", "qstac", "( -- )  error 1 if the stack is empty and more, error 7 if it is full.\n#        The model's limits are for its own memory. Here: empty is S0. Full\n#        is 8 cells before the return stack, which lies under the data stack:\n#        the interpreter itself needs that many between two words.", """
SP@ S0 @ SWAP < 1 ?ERROR
SP@ R0 @ 32 + < 7 ?ERROR""")

section("THE TEXT INTERPRETER")
colon("INTERPRET", "inter", "( -- )  execute or compile the words of the input, one after the other,\n#        until the null word leaves", """
BEGIN -FIND IF
STATE @ < IF CFA , ELSE CFA EXECUTE THEN ?STACK
ELSE HERE NUMBER DPL @ 1+ IF [COMPILE] DLITERAL
ELSE DROP [COMPILE] LITERAL THEN ?STACK
THEN AGAIN""")

section("VOCABULARIES",
        "A vocabulary's body is: a name field that holds one blank, the name field",
        "address of its newest word, the link to the vocabulary made before it. A",
        "new vocabulary's newest word is at first the blank name of its parent,",
        "whose link field is the parent's newest word.",
        "",
        "FORTH is made by VOCABULARY in the model. Its body must change with every",
        "new word, so here it is three cells of RAM at FORTH_VOC, which COLD fills,",
        "and FORTH is a colon definition.")
colon("IMMEDIATE", "immed", "( -- )  make the newest word immediate", "LATEST 64 TOGGLE")
colon("VOCABULARY", "vocab", "( -- )  VOCABULARY name: name makes itself the CONTEXT vocabulary.\n#        The blank name is 4 bytes (81 20 20 A0), where the model has A081.", """
<BUILDS {0xA0202081} , CURRENT @ CFA ,
HERE VOC-LINK @ , VOC-LINK !
DOES> 4 + CONTEXT !""")
colon("FORTH", "forth", "( -- )  make FORTH the CONTEXT vocabulary", """
{FORTH_VOC+CELL} CONTEXT !""", imm=True)
colon("DEFINITIONS", "defin", "( -- )  new words go into the CONTEXT vocabulary", "CONTEXT @ CURRENT !")
colon("(", "paren", "( -- )  a comment, up to the right parenthesis", "41 WORD", imm=True)

section("QUIT, ABORT, COLD")
colon("QUIT", "quit", "( -- )  the outer loop: read a line, interpret it, say OK", """
0 BLK ! [COMPILE] [
BEGIN RP! CR QUERY INTERPRET
STATE @ 0= IF ." OK" THEN AGAIN""")
colon("ABORT", "abort", "( -- )  empty the stacks, say who we are, go to QUIT", """
SP! DECIMAL DR0 CR ." fig-FORTH RISC-V"
[COMPILE] FORTH DEFINITIONS QUIT""")
head("COLD", "coldw", "cold", False, "( -- )  the cold start. The code is in the nucleus.")
emit()
raw("""
# What a cold start runs, after its code: EMPTY-BUFFERS FIRST USE ! FIRST PREV !
# ABORT. In the model USE and PREV are variables that hold FIRST when the
# system is built, and the manual has you type EMPTY-BUFFERS before the disc
# is first used. Here it is done at once: a buffer that seemed to be changed
# would be written to the flash.
align 4
coldt:
    dw mtbuf
    dw first
    dw use
    dw store
    dw first
    dw prev
    dw store
    dw abort
""")

section("ARITHMETIC")
colon("+-", "pm", "( n1 n2 -- n3 )  n1 with its sign changed if n2 is negative", "0< IF MINUS THEN")
colon("D+-", "dpm", "( d1 n -- d2 )", "0< IF DMINUS THEN")
colon("ABS", "abss", "( n -- u )", "DUP +-")
colon("DABS", "dabs", "( d -- ud )", "DUP D+-")
colon("MIN", "minn", "( n1 n2 -- n )", "OVER OVER > IF SWAP THEN DROP")
colon("MAX", "maxx", "( n1 n2 -- n )", "OVER OVER < IF SWAP THEN DROP")
colon("M*", "mstar", "( n1 n2 -- d )", "OVER OVER XOR >R ABS SWAP ABS U* R> D+-")
colon("M/", "mslas", "( d n -- remainder quotient )  the remainder has the sign of d", """
OVER >R >R DABS R ABS U/
R> R XOR +- SWAP R> +- SWAP""")
colon("*", "star", "( n1 n2 -- n )", "U* DROP")
colon("/MOD", "slmod", "( n1 n2 -- remainder quotient )", ">R S->D R> M/")
colon("/", "slash", "( n1 n2 -- quotient )", "/MOD SWAP DROP")
colon("MOD", "modd", "( n1 n2 -- remainder )", "/MOD DROP")
colon("*/MOD", "ssmod", "( n1 n2 n3 -- remainder quotient )  n1 * n2 / n3, the product a double number", """
>R M* R> M/""")
colon("*/", "ssla", "( n1 n2 n3 -- n )", "*/MOD SWAP DROP")
colon("M/MOD", "msmod", "( ud1 u2 -- u3 ud4 )  unsigned: remainder u3, double quotient ud4", """
>R 0 R U/ R> SWAP >R U/ R>""")

section("THE DISC: BUFFERS",
        "The disc is the flash from LO to HI, 46 KiB: blocks 0 to 183, screens 0 to",
        "45. A block is 256 bytes, one page of the flash, and a screen is 4 blocks.",
        "",
        "A buffer is the block number in a cell (its top bit says the block was",
        "changed and is to be written), the block, and a cell of nulls. So the 2",
        "of the model is 4 here, its 8000 is 80000000, and a buffer is B/BUF + 8.",
        "",
        "USE and PREV are variables in the model, with their values in the",
        "dictionary. The kernel is in flash, so here they are user variables.")
user("USE", "use", 0x64, "( -- addr )  the buffer to use next, the stalest")
user("PREV", "prev", 0x68, "( -- addr )  the buffer used last")
colon("+BUF", "pbuf", "( addr1 -- addr2 f )  the next buffer; f is false if it is PREV", """
{BUF_SIZE} + DUP LIMIT = IF DROP FIRST ENDIF
DUP PREV @ -""")
colon("UPDATE", "updat", "( -- )  mark the buffer used last as changed", """
PREV @ @ {0x80000000} OR PREV @ !""")
colon("EMPTY-BUFFERS", "mtbuf", "( -- )  clear the buffers; nothing is written", """
FIRST LIMIT OVER - ERASE""")
colon("DR0", "drzer", "( -- )  drive 0. There is one drive: no DR1.", "0 OFFSET !")
colon("BUFFER", "buffe", "( n -- addr )  give block n the stalest buffer, which is first written\n#        to the disc if it was changed; the block is not read", """
USE @ DUP >R
BEGIN +BUF UNTIL USE !
R @ 0< IF R 4 + R @ {0x7FFFFFFF} AND 0 R/W ENDIF
R ! R PREV ! R> 4 +""")
colon("BLOCK", "block", "( n -- addr )  the address of block n in a buffer, read from the disc if\n#        no buffer holds it", """
OFFSET @ + >R
PREV @ DUP @ R - DUP +
IF BEGIN +BUF 0=
IF DROP R BUFFER DUP R 1 R/W 4 - ENDIF
DUP @ R - DUP + 0= UNTIL
DUP PREV ! ENDIF
R> DROP 4 +""")

section("THE DISC: LINES, MESSAGE, LOAD",
        "MESSAGE types line n of screen 4 if WARNING is 1, as in the model. The",
        "messages are not on the disc until someone puts them there.")
colon("(LINE)", "pline", "( line scr -- addr 64 )  a line of a screen, in its buffer", """
>R C/L B/BUF */MOD R> B/SCR * +
BLOCK + C/L""")
colon(".LINE", "dline", "( line scr -- )  type it", "(LINE) -TRAILING TYPE")
colon("MESSAGE", "mess", "( n -- )  type message n: a line of the disc, or its number", """
WARNING @ IF
-DUP IF 4 OFFSET @ B/SCR / - .LINE ENDIF
ELSE ." MSG # " . ENDIF""")
colon("LOAD", "load", "( scr -- )  interpret a screen", """
BLK @ >R IN @ >R 0 IN ! B/SCR * BLK !
INTERPRET R> IN ! R> BLK !""")
colon("-->", "arrow", "( -- )  go on with the next screen", """
?LOADING 0 IN ! B/SCR BLK @ OVER MOD - BLK +!""", imm=True)

section("THE DISC: R/W",
        "The installation dependent part. The model's R/W drives a disc controller;",
        "its manual also gives one that keeps the blocks in memory, between LO and",
        "HI, for a system that has no disc:",
        "",
        "  : R/W  >R B/BUF * LO + DUP HI > 6 ?ERROR  R> IF SWAP ENDIF  B/BUF CMOVE ;",
        "",
        "This is that one. The flash is memory to read, so reading is its CMOVE.",
        "Writing is BLOCK-WRITE, a CODE word: the board erases and programs the",
        "page and reads it back. The range check is for both ends, since below LO",
        "is the kernel.")
con("LO", "dlo", "DISC_LO", "( -- addr )  the start of the disc")
con("HI", "dhi", "DISC_HI", "( -- addr )  its end")
codeword("BLOCK-WRITE", "blkwr", "( from to -- f )  write the 256 bytes at from (RAM, on a cell boundary)\n#        to the block of the disc at to. f is true if the flash does not\n#        hold them afterwards.", """
    lw a0, 0(DSP)
    lw a2, CELL(DSP)
    addi DSP, DSP, CELL
    jal ra, disc_write          # not `call`: bronzebeard gets that wrong beyond 2 KiB
    mv a1, a0
    j put
""")
colon("R/W", "rslw", "( addr blk f -- )  read (f = 1) or write (f = 0) block blk at addr.\n#        Error 6 is DISC RANGE, error 8 DISC ERROR.", """
>R B/BUF * LO + DUP LO < OVER HI B/BUF - > OR 6 ?ERROR
R> IF SWAP B/BUF CMOVE
ELSE BLOCK-WRITE 8 ?ERROR ENDIF""")

section("TICK AND FORGET")
colon("'", "tick", "( -- pfa )  the parameter field of the next word of the input; compiling,\n#        a literal", """
-FIND 0= 0 ?ERROR DROP [COMPILE] LITERAL""", imm=True)
colon("FORGET", "forge", "( -- )  FORGET name: take name and all words after it out of the\n#        dictionary. The kernel is below FENCE.", """
CURRENT @ CONTEXT @ - 24 ?ERROR
[COMPILE] ' DUP FENCE @ < 21 ?ERROR
DUP NFA DP ! LFA @ CURRENT @ !""")

section("THE CONDITIONALS",
        "The 1, 2, 3 and 4 they leave on the stack while compiling are pairing",
        "marks, not sizes: they are the model's.")
colon("BACK", "back", "( addr -- )  compile the distance back to addr", "HERE - ,")
colon("BEGIN", "begin", "", "?COMP HERE 1", imm=True)
colon("ENDIF", "endif", "", "?COMP 2 ?PAIRS HERE OVER - SWAP !", imm=True)
colon("THEN", "then", "", "[COMPILE] ENDIF", imm=True)
colon("DO", "do", "", "COMPILE (DO) HERE 3", imm=True)
colon("LOOP", "loop", "", "3 ?PAIRS COMPILE (LOOP) BACK", imm=True)
colon("+LOOP", "ploop", "", "3 ?PAIRS COMPILE (+LOOP) BACK", imm=True)
colon("UNTIL", "until", "", "1 ?PAIRS COMPILE 0BRANCH BACK", imm=True)
colon("END", "endd", "", "[COMPILE] UNTIL", imm=True)
colon("AGAIN", "again", "", "1 ?PAIRS COMPILE BRANCH BACK", imm=True)
colon("REPEAT", "repea", "", ">R >R [COMPILE] AGAIN R> R> 2 - [COMPILE] ENDIF", imm=True)
colon("IF", "iff", "", "COMPILE 0BRANCH HERE 0 , 2", imm=True)
colon("ELSE", "elsee", "", """
2 ?PAIRS COMPILE BRANCH HERE 0 ,
SWAP 2 [COMPILE] ENDIF 2""", imm=True)
colon("WHILE", "whilee", "", "[COMPILE] IF 2+", imm=True)

section("NUMBER OUTPUT")
colon("SPACES", "spacs", "( n -- )", "0 MAX -DUP IF 0 DO SPACE LOOP THEN")
colon("<#", "bdigs", "( -- )  start a number: it is built downward from PAD", "PAD HLD !")
colon("#>", "edigs", "( d -- addr n )  end it: the text", "DROP DROP HLD @ PAD OVER -")
colon("SIGN", "sign", "( n d -- d )  a minus sign if n is negative", "ROT 0< IF 45 HOLD THEN")
colon("#", "dig", "( d1 -- d2 )  one digit", """
BASE @ M/MOD ROT 9 OVER < IF 7 + THEN 48 + HOLD""")
colon("#S", "digs", "( d -- 0 0 )  all the digits", "BEGIN # OVER OVER OR 0= UNTIL")
colon("D.R", "ddotr", "( d n -- )  type d at the right of a field of n", """
>R SWAP OVER DABS <# #S SIGN #>
R> OVER - SPACES TYPE""")
colon("D.", "ddot", "( d -- )", "0 D.R SPACE")
colon(".R", "dotr", "( n1 n2 -- )  type n1 at the right of a field of n2", ">R S->D R> D.R")
colon(".", "dot", "( n -- )", "S->D D.")
colon("?", "ques", "( addr -- )  type the cell at addr", "@ .")

section("LIST, INDEX, TRIAD")
colon("LIST", "listt", "( scr -- )  type a screen", """
DECIMAL CR DUP SCR !
." SCR # " . 16 0 DO CR I 3 .R SPACE
I SCR @ .LINE LOOP CR""")
colon("INDEX", "index", "( from to -- )  type the first line of each screen", """
12 EMIT CR 1+ SWAP
DO CR I 3 .R SPACE
0 I .LINE
?TERMINAL IF LEAVE ENDIF LOOP""")
colon("TRIAD", "triad", "( scr -- )  type the three screens of the page that holds scr, and\n#        message 15 under them", """
12 EMIT 3 / 3 * 3 OVER + SWAP
DO CR I LIST LOOP CR
15 MESSAGE CR""")

section("VLIST")
colon("VLIST", "vlist", "( -- )  type the names of the CONTEXT vocabulary; a key stops it", """
128 OUT ! CONTEXT @ @
BEGIN OUT @ C/L > IF CR 0 OUT ! THEN
DUP ID. SPACE SPACE PFA LFA @
DUP 0= ?TERMINAL OR UNTIL DROP""")


section("THE EDITOR: TEXT, LINE, WHERE",
        "Screens 87 to 97 of the manual, the sample editor. Its last screen puts the",
        "editor below FENCE and makes it part of the system that a cold start",
        "brings up; this is that system. Three words are in FORTH, the rest in the",
        "EDITOR vocabulary.",
        "",
        "EDITOR is made by VOCABULARY in the model. Like FORTH, its body is three",
        "cells of RAM that COLD fills (EDITOR_VOC), and it is a colon definition.")
colon("TEXT", "text", "( c -- )  take the text up to the delimiter c to PAD, with blanks to\n#        the length of a line", """
HERE C/L 1+ BLANKS WORD HERE PAD C/L 1+ CMOVE""")
colon("LINE", "line", "( n -- addr )  line n of the screen SCR; error 23 unless n is 0 to 15", """
DUP -16 AND 23 ?ERROR SCR @ (LINE) DROP""")
colon("EDITOR", "editor", "( -- )  make EDITOR the CONTEXT vocabulary", """
{EDITOR_VOC+CELL} CONTEXT !""", imm=True)
colon("WHERE", "where", "( in blk -- )  after an error in a LOAD, with the two numbers the error\n#        left: show the screen and the line, mark the place, enter the editor", """
DUP B/SCR / DUP SCR ! ." SCR # " DECIMAL .
SWAP C/L /MOD C/L * ROT BLOCK + CR C/L TYPE
CR HERE C@ - SPACES 94 EMIT [COMPILE] EDITOR QUIT""")

section("THE EDITOR VOCABULARY: LINES",
        "The link field of the first word holds the address of FORTH's blank name,",
        "which is what VOCABULARY puts into a new vocabulary: a search goes on",
        "from there into FORTH.",
        "",
        "Some of these words have the names of FORTH words: I and R. Where the",
        "model writes FORTH I or FORTH R it means the old one, and so does the",
        "thread. R# is the cursor: its offset from the start of the screen.")
voc = "editor"
colon("#LOCATE", "e_locat", "( -- offset line )  where the cursor is", "R# @ C/L /MOD")
colon("#LEAD", "e_lead", "( -- addr offset )  the cursor's line and the offset in it", "#LOCATE LINE SWAP")
colon("#LAG", "e_lag", "( -- addr n )  the cursor's address and the characters after it", """
#LEAD DUP >R + C/L R> -""")
colon("-MOVE", "e_move", "( addr n -- )  move a line from addr to line n", "LINE C/L CMOVE UPDATE")
colon("H", "e_h", "( n -- )  hold line n at PAD", "LINE PAD 1+ C/L DUP PAD C! CMOVE")
colon("E", "e_e", "( n -- )  erase line n with blanks", "LINE C/L BLANKS UPDATE")
colon("S", "e_s", "( n -- )  spread: make line n blank; the lines from n on move down, and\n#        line 15 is lost", """
DUP 1 - 14 DO I LINE I 1+ -MOVE -1 +LOOP E""")
colon("D", "e_d", "( n -- )  delete line n, but hold it at PAD; the lines below move up", """
DUP H 15 DUP ROT DO I 1+ LINE I -MOVE LOOP E""")
colon("M", "e_m", "( n -- )  move the cursor by n and type its line, the cursor shown as _", """
R# +! CR SPACE #LEAD TYPE 95 EMIT
#LAG TYPE #LOCATE . DROP""")
colon("T", "e_t", "( n -- )  type line n, and hold it at PAD", "DUP C/L * R# ! DUP H 0 M")
colon("L", "e_l", "( -- )  list the screen again", "SCR @ LIST 0 M")
colon("R", "e_r", "( n -- )  replace line n by the text at PAD", "PAD 1+ SWAP -MOVE")
colon("P", "e_p", "( n -- )  put the text that follows on line n", "1 TEXT R")
colon("I", "e_i", "( n -- )  insert the text at PAD at line n; the lines below move down", "DUP S R")
colon("TOP", "e_top", "( -- )  the cursor to the top left of the screen", "0 R# !")

section("THE EDITOR VOCABULARY: SCREENS",
        "FLUSH takes every buffer once. The model computes how many there are,",
        "[ LIMIT FIRST - B/BUF 4 + / ] LITERAL, and here that number is NBUF. In",
        "COPY its 2 - is 4 -, the cell that holds the block number.")
colon("CLEAR", "e_clear", "( n -- )  fill screen n with blanks; it becomes SCR", """
SCR ! 16 0 DO FORTH I EDITOR E LOOP""")
colon("FLUSH", "e_flush", "( -- )  write all changed blocks to the disc", """
{NBUF} 0 DO 32767 BUFFER DROP LOOP""")
colon("COPY", "e_copy", "( n1 n2 -- )  copy screen n1 to screen n2", """
B/SCR * OFFSET @ + SWAP B/SCR * B/SCR OVER + SWAP
DO DUP FORTH I BLOCK 4 - ! 1+ UPDATE LOOP
DROP FLUSH""")

section("THE EDITOR VOCABULARY: TEXT IN A LINE",
        "MATCH is the model's one CODE word here, for the 6502; the manual says it",
        "may be translated. It looks for the text at addr2 (n2 characters) in the",
        "n1 characters at addr1. Found: true, and the distance from addr1 to the",
        "character after the text. Not found: false, and n1, which takes the cursor",
        "to the next line.")
codeword("MATCH", "e_match", "( addr1 n1 addr2 n2 -- f n3 )", """
    lw a4, 0(DSP)               # n2
    lw a3, CELL(DSP)            # addr2
    lw a2, 2*CELL(DSP)          # n1, what is left of the line
    lw a1, 3*CELL(DSP)          # addr1
    addi DSP, DSP, 2*CELL
    li a5, 0                    # how far the cursor has gone
e_match1:
    bltu a2, a4, e_match4       # less left than the text is long: not found
    li t0, 0
e_match2:
    beq t0, a4, e_match3        # all of it was equal: found
    add t1, a1, t0
    lbu t1, 0(t1)
    add t2, a3, t0
    lbu t2, 0(t2)
    addi t0, t0, 1
    beq t1, t2, e_match2
    addi a1, a1, 1              # try one character further on
    addi a5, a5, 1
    addi a2, a2, -1
    j e_match1
e_match3:
    add a1, a5, a4              # to the character after the text
    li a2, 1
    sw a2, CELL(DSP)
    j put
e_match4:
    add a1, a5, a2              # to the end of the line
    sw zero, CELL(DSP)
    j put
""")
colon("1LINE", "e_1line", "( -- f )  look for the text at PAD from the cursor to the end of its\n#        line, and move the cursor", "#LAG PAD COUNT MATCH R# +!")
colon("FIND", "e_find", "( -- )  look for the text at PAD from the cursor to the end of the\n#        screen; not there: the cursor to the top, and error 0 with the text", """
BEGIN 1023 R# @ <
IF TOP PAD HERE C/L 1+ CMOVE 0 ERROR ENDIF
1LINE UNTIL""")
colon("DELETE", "e_delete", "( n -- )  delete the n characters before the cursor", """
>R #LAG + FORTH R -
#LAG R MINUS R# +!
#LEAD + SWAP CMOVE
R> BLANKS UPDATE""")
colon("N", "e_n", "( -- )  find the next place the text at PAD occurs", "FIND 0 M")
colon("F", "e_f", "( -- )  find the text that follows", "1 TEXT N")
colon("B", "e_b", "( -- )  the cursor back by the length of the text at PAD", "PAD C@ MINUS M")
colon("X", "e_x", "( -- )  find the text that follows and delete it", """
1 TEXT FIND PAD C@ DELETE 0 M""")
colon("TILL", "e_till", "( -- )  delete from the cursor to the end of the text that follows,\n#        which must be on the cursor's line", """
#LEAD + 1 TEXT 1LINE 0= 0 ?ERROR
#LEAD + SWAP - DELETE 0 M""")
colon("C", "e_c", "( -- )  put the text that follows in at the cursor; what was after the\n#        cursor moves right, and the end of the line is lost", """
1 TEXT PAD COUNT
#LAG ROT OVER MIN >R
FORTH R R# +!
R - >R
DUP HERE R CMOVE
HERE #LEAD + R> CMOVE
R> CMOVE UPDATE
0 M""")
voc = "forth"
