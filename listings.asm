# fig-FORTH for RISC-V: the listings
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
# A word is its header (python3 tools/header.py NAME label previous docol),
# then the thread. `last_nfa:` stands on the name field of the newest word:
# move that line when a word is added at the end.

# ------------------------------------------------------------------------
# COLON AND SEMICOLON, CONSTANT VARIABLE USER
#
# As in the model, each of the four defining words ends in ;CODE: (;CODE)
# points the code field of the new word at the machine code that follows it
# in the thread. That code gets W = the code field address from NEXT; the
# parameter field is at CELL(W). The kernel's own colon words, constants
# and user variables have these labels in their code fields.

# :  ( -- )  start a colon definition
#   : :  ?EXEC !CSP CURRENT @ CONTEXT ! CREATE ]  ;CODE  the code below  IMMEDIATE
align 4
n_colon:
    db 0xC1
    string :
    bytes 0x20 0xA0
    dw n_stod
colon:
    dw docol
    dw qexec
    dw scsp
    dw curr
    dw at
    dw cont
    dw store
    dw creat
    dw rbrac
    dw pscod
docol:                          # a colon definition: nest into its thread
    addi RSP, RSP, -CELL
    sw IP, 0(RSP)
    addi IP, W, CELL
    j next

# ;  ( -- )  end a colon definition
#   : ;  ?CSP COMPILE ;S SMUDGE [COMPILE] [ ;  IMMEDIATE
align 4
n_semi:
    db 0xC1
    string ;
    bytes 0x20 0xA0
    dw n_colon
semi:
    dw docol
    dw qcsp
    dw comp
    dw semis
    dw smudg
    dw lbrac
    dw semis

# CONSTANT  ( n -- )  n CONSTANT name: name pushes n
#   : CONSTANT  CREATE SMUDGE ,  ;CODE  the code below
align 4
n_con:
    db 0x88
    string CONSTANT
    bytes 0x20 0x20 0xA0
    dw n_semi
con:
    dw docol
    dw creat
    dw smudg
    dw comma
    dw pscod
docon:                          # a CONSTANT: push its parameter
    lw a1, CELL(W)
    j push

# VARIABLE  ( n -- )  n VARIABLE name: name pushes the address of a cell that holds n
#   : VARIABLE  CONSTANT  ;CODE  the code below
align 4
n_var:
    db 0x88
    string VARIABLE
    bytes 0x20 0x20 0xA0
    dw n_con
var:
    dw docol
    dw con
    dw pscod
dovar:                          # a VARIABLE: push the address of its parameter
    addi a1, W, CELL
    j push

# USER  ( n -- )  n USER name: name pushes the user area address + n
#   : USER  CONSTANT  ;CODE  the code below
align 4
n_user:
    db 0x84
    string USER
    bytes 0x20 0x20 0xA0
    dw n_var
user:
    dw docol
    dw con
    dw pscod
douse:                          # a USER variable: its parameter is an offset
    lw a1, CELL(W)              # into the user area
    add a1, a1, UP
    j push


# ------------------------------------------------------------------------
# CONSTANTS

# 0  ( -- 0 )
align 4
n_zero:
    db 0x81
    string 0
    bytes 0x20 0xA0
    dw n_user
zero:
    dw docon
    dw 0

# 1  ( -- 1 )
align 4
n_one:
    db 0x81
    string 1
    bytes 0x20 0xA0
    dw n_zero
one:
    dw docon
    dw 1

# 2  ( -- 2 )
align 4
n_two:
    db 0x81
    string 2
    bytes 0x20 0xA0
    dw n_one
two:
    dw docon
    dw 2

# 3  ( -- 3 )
align 4
n_three:
    db 0x81
    string 3
    bytes 0x20 0xA0
    dw n_two
three:
    dw docon
    dw 3

# BL  ( -- 32 )  the blank
align 4
n_bl:
    db 0x82
    string BL
    bytes 0xA0
    dw n_three
bl:
    dw docon
    dw 32

# C/L  ( -- 64 )  characters in a line
align 4
n_csll:
    db 0x83
    string C/
    db 0xCC                 # L + 0x80
    dw n_bl
csll:
    dw docon
    dw 64

# FIRST  ( -- addr )  the first disc buffer
align 4
n_first:
    db 0x85
    string FIRST
    bytes 0x20 0xA0
    dw n_csll
first:
    dw docon
    dw FIRST_INIT

# LIMIT  ( -- addr )  the end of the last disc buffer
align 4
n_limit:
    db 0x85
    string LIMIT
    bytes 0x20 0xA0
    dw n_first
limit:
    dw docon
    dw LIMIT_INIT

# B/BUF  ( -- 256 )  bytes in a block: one page of the flash. The model's disc has 128.
align 4
n_bbuf:
    db 0x85
    string B/BUF
    bytes 0x20 0xA0
    dw n_limit
bbuf:
    dw docon
    dw B_BUF

# B/SCR  ( -- 4 )  blocks in a screen
align 4
n_bscr:
    db 0x85
    string B/SCR
    bytes 0x20 0xA0
    dw n_bbuf
bscr:
    dw docon
    dw 1024 // B_BUF

# +ORIGIN  ( n -- addr )  the address n bytes into the origin table (SCR 12 of the nucleus)
#   : +ORIGIN  origin + ;
align 4
n_porig:
    db 0x87
    string +ORIGI
    db 0xCE                 # N + 0x80
    dw n_bscr
porig:
    dw docol
    dw lit
    dw origin
    dw plus
    dw semis


# ------------------------------------------------------------------------
# USER VARIABLES
#
# The parameter is the offset into the user area: the model's, doubled.

# S0  ( -- addr )  where the data stack starts
align 4
n_szero:
    db 0x82
    string S0
    bytes 0xA0
    dw n_porig
szero:
    dw douse
    dw 0x0C

# R0  ( -- addr )  where the return stack starts
align 4
n_rzero:
    db 0x82
    string R0
    bytes 0xA0
    dw n_szero
rzero:
    dw douse
    dw 0x10

# TIB  ( -- addr )  the address of the terminal input buffer
align 4
n_tib:
    db 0x83
    string TI
    db 0xC2                 # B + 0x80
    dw n_rzero
tib:
    dw douse
    dw 0x14

# WIDTH  ( -- addr )  the most characters kept of a name
align 4
n_width:
    db 0x85
    string WIDTH
    bytes 0x20 0xA0
    dw n_tib
width:
    dw douse
    dw 0x18

# WARNING  ( -- addr )  0: messages are numbers; below 0: an error runs (ABORT)
align 4
n_warn:
    db 0x87
    string WARNIN
    db 0xC7                 # G + 0x80
    dw n_width
warn:
    dw douse
    dw 0x1C

# FENCE  ( -- addr )  FORGET does not go below this address
align 4
n_fence:
    db 0x85
    string FENCE
    bytes 0x20 0xA0
    dw n_warn
fence:
    dw douse
    dw 0x20

# DP  ( -- addr )  the dictionary pointer
align 4
n_dp:
    db 0x82
    string DP
    bytes 0xA0
    dw n_fence
dp:
    dw douse
    dw 0x24

# VOC-LINK  ( -- addr )  the newest vocabulary
align 4
n_vocl:
    db 0x88
    string VOC-LINK
    bytes 0x20 0x20 0xA0
    dw n_dp
vocl:
    dw douse
    dw 0x28

# BLK  ( -- addr )  the block being interpreted; 0 is the terminal
align 4
n_blk:
    db 0x83
    string BL
    db 0xCB                 # K + 0x80
    dw n_vocl
blk:
    dw douse
    dw 0x2C

# IN  ( -- addr )  the offset into the text being interpreted
align 4
n_inn:
    db 0x82
    string IN
    bytes 0xA0
    dw n_blk
inn:
    dw douse
    dw 0x30

# OUT  ( -- addr )  characters sent; EMIT counts
align 4
n_out:
    db 0x83
    string OU
    db 0xD4                 # T + 0x80
    dw n_inn
out:
    dw douse
    dw 0x34

# SCR  ( -- addr )  the screen last listed
align 4
n_scr:
    db 0x83
    string SC
    db 0xD2                 # R + 0x80
    dw n_out
scr:
    dw douse
    dw 0x38

# OFFSET  ( -- addr )  added to block numbers
align 4
n_ofset:
    db 0x86
    string OFFSET
    bytes 0xA0
    dw n_scr
ofset:
    dw douse
    dw 0x3C

# CONTEXT  ( -- addr )  the vocabulary searched first
align 4
n_cont:
    db 0x87
    string CONTEX
    db 0xD4                 # T + 0x80
    dw n_ofset
cont:
    dw douse
    dw 0x40

# CURRENT  ( -- addr )  the vocabulary new words go into
align 4
n_curr:
    db 0x87
    string CURREN
    db 0xD4                 # T + 0x80
    dw n_cont
curr:
    dw douse
    dw 0x44

# STATE  ( -- addr )  0 executing, 192 compiling
align 4
n_state:
    db 0x85
    string STATE
    bytes 0x20 0xA0
    dw n_curr
state:
    dw douse
    dw 0x48

# BASE  ( -- addr )  the number base
align 4
n_base:
    db 0x84
    string BASE
    bytes 0x20 0x20 0xA0
    dw n_state
base:
    dw douse
    dw 0x4C

# DPL  ( -- addr )  digits after the point of the last number, or -1
align 4
n_dpl:
    db 0x83
    string DP
    db 0xCC                 # L + 0x80
    dw n_base
dpl:
    dw douse
    dw 0x50

# FLD  ( -- addr )  field width; not used
align 4
n_fld:
    db 0x83
    string FL
    db 0xC4                 # D + 0x80
    dw n_dpl
fld:
    dw douse
    dw 0x54

# CSP  ( -- addr )  the stack pointer when the definition began
align 4
n_csp:
    db 0x83
    string CS
    db 0xD0                 # P + 0x80
    dw n_fld
csp:
    dw douse
    dw 0x58

# R#  ( -- addr )  the editor's cursor
align 4
n_rnum:
    db 0x82
    bytes 0x52 0x23 0xA0    # R#
    dw n_csp
rnum:
    dw douse
    dw 0x5C

# HLD  ( -- addr )  the last character of the number being put out
align 4
n_hld:
    db 0x83
    string HL
    db 0xC4                 # D + 0x80
    dw n_rnum
hld:
    dw douse
    dw 0x60


# ------------------------------------------------------------------------
# SMALL WORDS

# 1+  ( n -- n+1 )
#   : 1+  1 + ;
align 4
n_onep:
    db 0x82
    string 1+
    bytes 0xA0
    dw n_hld
onep:
    dw docol
    dw one
    dw plus
    dw semis

# 2+  ( n -- n+2 )
#   : 2+  2 + ;
align 4
n_twop:
    db 0x82
    string 2+
    bytes 0xA0
    dw n_onep
twop:
    dw docol
    dw two
    dw plus
    dw semis

# HERE  ( -- addr )  the next free address of the dictionary
#   : HERE  DP @ ;
align 4
n_here:
    db 0x84
    string HERE
    bytes 0x20 0x20 0xA0
    dw n_twop
here:
    dw docol
    dw dp
    dw at
    dw semis

# ALLOT  ( n -- )  take n bytes of the dictionary
#   : ALLOT  DP +! ;
align 4
n_allot:
    db 0x85
    string ALLOT
    bytes 0x20 0xA0
    dw n_here
allot:
    dw docol
    dw dp
    dw pstor
    dw semis

# ALIGN  ( -- )  round the dictionary pointer up to a cell. Not in the model.
#   : ALIGN  HERE 3 + -4 AND DP ! ;
align 4
n_alignn:
    db 0x85
    string ALIGN
    bytes 0x20 0xA0
    dw n_allot
alignn:
    dw docol
    dw here
    dw three
    dw plus
    dw lit
    dw -4
    dw andd
    dw dp
    dw store
    dw semis

# ,  ( n -- )  put a cell into the dictionary. The cell is 4.
#   : ,  HERE ! 4 ALLOT ;
align 4
n_comma:
    db 0x81
    bytes 0x2C 0x20 0xA0    # ,
    dw n_alignn
comma:
    dw docol
    dw here
    dw store
    dw lit
    dw 4
    dw allot
    dw semis

# C,  ( b -- )  put a byte into the dictionary
#   : C,  HERE C! 1 ALLOT ;
align 4
n_ccomm:
    db 0x82
    bytes 0x43 0x2C 0xA0    # C,
    dw n_comma
ccomm:
    dw docol
    dw here
    dw cstor
    dw one
    dw allot
    dw semis

# -  ( n1 n2 -- n1-n2 )
#   : -  MINUS + ;
align 4
n_subb:
    db 0x81
    string -
    bytes 0x20 0xA0
    dw n_ccomm
subb:
    dw docol
    dw minus
    dw plus
    dw semis

# =  ( n1 n2 -- f )
#   : =  - 0= ;
align 4
n_equal:
    db 0x81
    string =
    bytes 0x20 0xA0
    dw n_subb
equal:
    dw docol
    dw subb
    dw zequ
    dw semis

# <  ( n1 n2 -- f )
#   : <  - 0< ;
align 4
n_less:
    db 0x81
    string <
    bytes 0x20 0xA0
    dw n_equal
less:
    dw docol
    dw subb
    dw zless
    dw semis

# >  ( n1 n2 -- f )
#   : >  SWAP < ;
align 4
n_great:
    db 0x81
    string >
    bytes 0x20 0xA0
    dw n_less
great:
    dw docol
    dw swap
    dw less
    dw semis

# ROT  ( n1 n2 n3 -- n2 n3 n1 )
#   : ROT  >R SWAP R> SWAP ;
align 4
n_rot:
    db 0x83
    string RO
    db 0xD4                 # T + 0x80
    dw n_great
rot:
    dw docol
    dw tor
    dw swap
    dw fromr
    dw swap
    dw semis

# SPACE  ( -- )
#   : SPACE  BL EMIT ;
align 4
n_space:
    db 0x85
    string SPACE
    bytes 0x20 0xA0
    dw n_rot
space:
    dw docol
    dw bl
    dw emit
    dw semis

# -DUP  ( n -- n n | 0 )  duplicate if not zero
#   : -DUP  DUP IF DUP THEN ;
align 4
n_ddup:
    db 0x84
    string -DUP
    bytes 0x20 0x20 0xA0
    dw n_space
ddup:
    dw docol
    dw dup
    dw zbran
    dw %offset(ddup1)
    dw dup
ddup1:
    dw semis


# ------------------------------------------------------------------------
# THE FIELDS OF A WORD
#
# From the parameter field: the code field is 4 below, the link field 8, and
# the last byte of the name field 9. The model's numbers are 2, 4 and 5.

# TRAVERSE  ( addr n -- addr )  to the other end of a name field; n is 1 or -1
#   : TRAVERSE  SWAP BEGIN OVER + 127 OVER C@ < UNTIL SWAP DROP ;
align 4
n_trav:
    db 0x88
    string TRAVERSE
    bytes 0x20 0x20 0xA0
    dw n_ddup
trav:
    dw docol
    dw swap
trav1:
    dw over
    dw plus
    dw lit
    dw 127
    dw over
    dw cat
    dw less
    dw zbran
    dw %offset(trav1)
    dw swap
    dw drop
    dw semis

# LATEST  ( -- nfa )  the newest word of CURRENT
#   : LATEST  CURRENT @ @ ;
align 4
n_lates:
    db 0x86
    string LATEST
    bytes 0xA0
    dw n_trav
lates:
    dw docol
    dw curr
    dw at
    dw at
    dw semis

# LFA  ( pfa -- lfa )
#   : LFA  8 - ;
align 4
n_lfa:
    db 0x83
    string LF
    db 0xC1                 # A + 0x80
    dw n_lates
lfa:
    dw docol
    dw lit
    dw 8
    dw subb
    dw semis

# CFA  ( pfa -- cfa )
#   : CFA  4 - ;
align 4
n_cfa:
    db 0x83
    string CF
    db 0xC1                 # A + 0x80
    dw n_lfa
cfa:
    dw docol
    dw lit
    dw 4
    dw subb
    dw semis

# NFA  ( pfa -- nfa )
#   : NFA  9 - -1 TRAVERSE ;
align 4
n_nfa:
    db 0x83
    string NF
    db 0xC1                 # A + 0x80
    dw n_cfa
nfa:
    dw docol
    dw lit
    dw 9
    dw subb
    dw lit
    dw -1
    dw trav
    dw semis

# PFA  ( nfa -- pfa )
#   : PFA  1 TRAVERSE 9 + ;
align 4
n_pfa:
    db 0x83
    string PF
    db 0xC1                 # A + 0x80
    dw n_nfa
pfa:
    dw docol
    dw one
    dw trav
    dw lit
    dw 9
    dw plus
    dw semis


# ------------------------------------------------------------------------
# COMPILER SECURITY

# !CSP  ( -- )  note the stack pointer
#   : !CSP  SP@ CSP ! ;
align 4
n_scsp:
    db 0x84
    string !CSP
    bytes 0x20 0x20 0xA0
    dw n_pfa
scsp:
    dw docol
    dw spat
    dw csp
    dw store
    dw semis

# ?ERROR  ( f n -- )  error n if f is true
#   : ?ERROR  SWAP IF ERROR ELSE DROP THEN ;
align 4
n_qerr:
    db 0x86
    string ?ERROR
    bytes 0xA0
    dw n_scsp
qerr:
    dw docol
    dw swap
    dw zbran
    dw %offset(qerr1)
    dw error
    dw bran
    dw %offset(qerr2)
qerr1:
    dw drop
qerr2:
    dw semis

# ?COMP  ( -- )  error 17 unless compiling
#   : ?COMP  STATE @ 0= 17 ?ERROR ;
align 4
n_qcomp:
    db 0x85
    string ?COMP
    bytes 0x20 0xA0
    dw n_qerr
qcomp:
    dw docol
    dw state
    dw at
    dw zequ
    dw lit
    dw 17
    dw qerr
    dw semis

# ?EXEC  ( -- )  error 18 unless executing
#   : ?EXEC  STATE @ 18 ?ERROR ;
align 4
n_qexec:
    db 0x85
    string ?EXEC
    bytes 0x20 0xA0
    dw n_qcomp
qexec:
    dw docol
    dw state
    dw at
    dw lit
    dw 18
    dw qerr
    dw semis

# ?PAIRS  ( n1 n2 -- )  error 19 if the conditionals do not pair
#   : ?PAIRS  - 19 ?ERROR ;
align 4
n_qpair:
    db 0x86
    string ?PAIRS
    bytes 0xA0
    dw n_qexec
qpair:
    dw docol
    dw subb
    dw lit
    dw 19
    dw qerr
    dw semis

# ?CSP  ( -- )  error 20 if the stack moved since !CSP
#   : ?CSP  SP@ CSP @ - 20 ?ERROR ;
align 4
n_qcsp:
    db 0x84
    string ?CSP
    bytes 0x20 0x20 0xA0
    dw n_qpair
qcsp:
    dw docol
    dw spat
    dw csp
    dw at
    dw subb
    dw lit
    dw 20
    dw qerr
    dw semis

# ?LOADING  ( -- )  error 22 unless loading from disc
#   : ?LOADING  BLK @ 0= 22 ?ERROR ;
align 4
n_qload:
    db 0x88
    string ?LOADING
    bytes 0x20 0x20 0xA0
    dw n_qcsp
qload:
    dw docol
    dw blk
    dw at
    dw zequ
    dw lit
    dw 22
    dw qerr
    dw semis


# ------------------------------------------------------------------------
# COMPILE, THE BRACKETS, SMUDGE, THE BASES, ;CODE

# COMPILE  ( -- )  put the next word of the thread into the dictionary. The step is 4.
#   : COMPILE  ?COMP R> DUP 4 + >R @ , ;
align 4
n_comp:
    db 0x87
    string COMPIL
    db 0xC5                 # E + 0x80
    dw n_qload
comp:
    dw docol
    dw qcomp
    dw fromr
    dw dup
    dw lit
    dw 4
    dw plus
    dw tor
    dw at
    dw comma
    dw semis

# [  ( -- )  stop compiling
#   : [  0 STATE ! ;  IMMEDIATE
align 4
n_lbrac:
    db 0xC1
    string [
    bytes 0x20 0xA0
    dw n_comp
lbrac:
    dw docol
    dw zero
    dw state
    dw store
    dw semis

# ]  ( -- )  compile
#   : ]  192 STATE ! ;
align 4
n_rbrac:
    db 0x81
    string ]
    bytes 0x20 0xA0
    dw n_lbrac
rbrac:
    dw docol
    dw lit
    dw 192
    dw state
    dw store
    dw semis

# SMUDGE  ( -- )  hide or show the newest word
#   : SMUDGE  LATEST 32 TOGGLE ;
align 4
n_smudg:
    db 0x86
    string SMUDGE
    bytes 0xA0
    dw n_rbrac
smudg:
    dw docol
    dw lates
    dw lit
    dw 32
    dw toggl
    dw semis

# HEX  ( -- )
#   : HEX  16 BASE ! ;
align 4
n_hexx:
    db 0x83
    string HE
    db 0xD8                 # X + 0x80
    dw n_smudg
hexx:
    dw docol
    dw lit
    dw 16
    dw base
    dw store
    dw semis

# DECIMAL  ( -- )
#   : DECIMAL  10 BASE ! ;
align 4
n_decim:
    db 0x87
    string DECIMA
    db 0xCC                 # L + 0x80
    dw n_hexx
decim:
    dw docol
    dw lit
    dw 10
    dw base
    dw store
    dw semis

# (;CODE)  ( -- )  point the newest word's code field at what follows in the thread
#   : (;CODE)  R> LATEST PFA CFA ! ;
align 4
n_pscod:
    db 0x87
    string (;CODE
    db 0xA9                 # ) + 0x80
    dw n_decim
pscod:
    dw docol
    dw fromr
    dw lates
    dw pfa
    dw cfa
    dw store
    dw semis

# ;CODE  ( -- )  end a defining word; machine code follows. There is no assembler
#        vocabulary yet: the code is put in with , by hand.
#   : ;CODE  ?CSP COMPILE (;CODE) [COMPILE] [ SMUDGE ;  IMMEDIATE
align 4
n_semic:
    db 0xC5
    string ;CODE
    bytes 0x20 0xA0
    dw n_pscod
semic:
    dw docol
    dw qcsp
    dw comp
    dw pscod
    dw lbrac
    dw smudg
    dw semis


# ------------------------------------------------------------------------
# <BUILDS AND DOES>

# <BUILDS  ( -- )  start the header of a word that DOES> will finish
#   : <BUILDS  0 CONSTANT ;
align 4
n_build:
    db 0x87
    string <BUILD
    db 0xD3                 # S + 0x80
    dw n_semic
build:
    dw docol
    dw zero
    dw con
    dw semis

# DOES>  ( -- )  the words after it are what the new word does
#   : DOES>  R> LATEST PFA !  ;CODE  the code below
align 4
n_does:
    db 0x85
    string DOES>
    bytes 0x20 0xA0
    dw n_build
does:
    dw docol
    dw fromr
    dw lates
    dw pfa
    dw store
    dw pscod
dodoe:                          # a word made by <BUILDS ... DOES>: its first
    addi RSP, RSP, -CELL        # parameter is the address of the thread after
    sw IP, 0(RSP)               # DOES>. Nest into that, and push the address
    lw IP, CELL(W)              # of the parameters behind it.
    addi a1, W, 2*CELL
    j push


# ------------------------------------------------------------------------
# TEXT OUTPUT

# COUNT  ( addr -- addr+1 n )
#   : COUNT  DUP 1+ SWAP C@ ;
align 4
n_count:
    db 0x85
    string COUNT
    bytes 0x20 0xA0
    dw n_does
count:
    dw docol
    dw dup
    dw onep
    dw swap
    dw cat
    dw semis

# TYPE  ( addr n -- )
#   : TYPE  -DUP IF OVER + SWAP DO I C@ EMIT LOOP ELSE DROP THEN ;
align 4
n_typee:
    db 0x84
    string TYPE
    bytes 0x20 0x20 0xA0
    dw n_count
typee:
    dw docol
    dw ddup
    dw zbran
    dw %offset(typee1)
    dw over
    dw plus
    dw swap
    dw xdo
typee2:
    dw ido
    dw cat
    dw emit
    dw xloop
    dw %offset(typee2)
    dw bran
    dw %offset(typee3)
typee1:
    dw drop
typee3:
    dw semis

# -TRAILING  ( addr n -- addr n' )  without the blanks at the end
#   : -TRAILING  DUP 0 DO OVER OVER + 1 - C@ BL - IF LEAVE ELSE 1 - THEN LOOP ;
align 4
n_dtrai:
    db 0x89
    string -TRAILING
    bytes 0x20 0xA0
    dw n_typee
dtrai:
    dw docol
    dw dup
    dw zero
    dw xdo
dtrai1:
    dw over
    dw over
    dw plus
    dw one
    dw subb
    dw cat
    dw bl
    dw subb
    dw zbran
    dw %offset(dtrai2)
    dw leave
    dw bran
    dw %offset(dtrai3)
dtrai2:
    dw one
    dw subb
dtrai3:
    dw xloop
    dw %offset(dtrai1)
    dw semis

# (.")  ( -- )  type the text that follows in the thread. The thread goes on at
#        the next cell boundary: 3 + -4 AND, which the model does not have.
#   : (.")  R COUNT DUP 1+ R> + 3 + -4 AND >R TYPE ;
align 4
n_pdotq:
    db 0x84
    bytes 0x28 0x2E 0x22 0x29 0x20 0x20 0xA0 # (.")
    dw n_dtrai
pdotq:
    dw docol
    dw rr
    dw count
    dw dup
    dw onep
    dw fromr
    dw plus
    dw three
    dw plus
    dw lit
    dw -4
    dw andd
    dw tor
    dw typee
    dw semis

# ."  ( -- )  type, or compile, the text up to the next quote. ALIGN after the
#        compiled text is not the model's.
#   : ."  34 STATE @ IF COMPILE (.") WORD HERE C@ 1+ ALLOT ALIGN
#         ELSE WORD HERE COUNT TYPE THEN ;  IMMEDIATE
align 4
n_dotq:
    db 0xC2
    bytes 0x2E 0x22 0xA0    # ."
    dw n_pdotq
dotq:
    dw docol
    dw lit
    dw 34
    dw state
    dw at
    dw zbran
    dw %offset(dotq1)
    dw comp
    dw pdotq
    dw wordd
    dw here
    dw cat
    dw onep
    dw allot
    dw alignn
    dw bran
    dw %offset(dotq2)
dotq1:
    dw wordd
    dw here
    dw count
    dw typee
dotq2:
    dw semis


# ------------------------------------------------------------------------
# TERMINAL INPUT

# EXPECT  ( addr n -- )  read a line of up to n characters to addr; nulls end it.
#        20 +ORIGIN holds the backspace key. The model ends with 0 I 1+ ! which
#        stores a cell at any address: two C! here.
#   : EXPECT  OVER + OVER DO
#             KEY DUP 20 +ORIGIN @ = IF
#             DROP 8 OVER I = DUP R> 2 - + >R -
#             ELSE DUP 13 = IF LEAVE DROP BL 0 ELSE DUP THEN
#             I C! 0 I 1+ C! 0 I 2+ C!
#             THEN EMIT LOOP DROP ;
align 4
n_expec:
    db 0x86
    string EXPECT
    bytes 0xA0
    dw n_dotq
expec:
    dw docol
    dw over
    dw plus
    dw over
    dw xdo
expec1:
    dw key
    dw dup
    dw lit
    dw 20
    dw porig
    dw at
    dw equal
    dw zbran
    dw %offset(expec2)
    dw drop
    dw lit
    dw 8
    dw over
    dw ido
    dw equal
    dw dup
    dw fromr
    dw two
    dw subb
    dw plus
    dw tor
    dw subb
    dw bran
    dw %offset(expec3)
expec2:
    dw dup
    dw lit
    dw 13
    dw equal
    dw zbran
    dw %offset(expec4)
    dw leave
    dw drop
    dw bl
    dw zero
    dw bran
    dw %offset(expec5)
expec4:
    dw dup
expec5:
    dw ido
    dw cstor
    dw zero
    dw ido
    dw onep
    dw cstor
    dw zero
    dw ido
    dw twop
    dw cstor
expec3:
    dw emit
    dw xloop
    dw %offset(expec1)
    dw drop
    dw semis

# QUERY  ( -- )  read a line of 80 characters to the terminal input buffer
#   : QUERY  TIB @ 80 EXPECT 0 IN ! ;
align 4
n_query:
    db 0x85
    string QUERY
    bytes 0x20 0xA0
    dw n_expec
query:
    dw docol
    dw tib
    dw at
    dw lit
    dw 80
    dw expec
    dw zero
    dw inn
    dw store
    dw semis

# null  ( -- )  the word whose name is a null: the end of the line, or of a block.
#        From the terminal it leaves INTERPRET. From the disc it goes on with
#        the next block, and leaves at the end of the screen: 3 is B/SCR - 1,
#        where the model has 7.
#   : null  BLK @ IF 1 BLK +! 0 IN ! BLK @ 3 AND 0=
#           IF ?EXEC R> DROP ENDIF
#           ELSE R> DROP ENDIF ;  IMMEDIATE
align 4
n_null:
    db 0xC1
    bytes 0x00 0x20 0xA0    # ^@
    dw n_query
null:
    dw docol
    dw blk
    dw at
    dw zbran
    dw %offset(null1)
    dw one
    dw blk
    dw pstor
    dw zero
    dw inn
    dw store
    dw blk
    dw at
    dw three
    dw andd
    dw zequ
    dw zbran
    dw %offset(null2)
    dw qexec
    dw fromr
    dw drop
null2:
    dw bran
    dw %offset(null3)
null1:
    dw fromr
    dw drop
null3:
    dw semis


# ------------------------------------------------------------------------
# FILL, HOLD, PAD, WORD

# FILL  ( addr n b -- )  n is at least 1
#   : FILL  SWAP >R OVER C! DUP 1+ R> 1 - CMOVE ;
align 4
n_fill:
    db 0x84
    string FILL
    bytes 0x20 0x20 0xA0
    dw n_null
fill:
    dw docol
    dw swap
    dw tor
    dw over
    dw cstor
    dw dup
    dw onep
    dw fromr
    dw one
    dw subb
    dw cmove
    dw semis

# ERASE  ( addr n -- )
#   : ERASE  0 FILL ;
align 4
n_erase:
    db 0x85
    string ERASE
    bytes 0x20 0xA0
    dw n_fill
erase:
    dw docol
    dw zero
    dw fill
    dw semis

# BLANKS  ( addr n -- )
#   : BLANKS  BL FILL ;
align 4
n_blank:
    db 0x86
    string BLANKS
    bytes 0xA0
    dw n_erase
blank:
    dw docol
    dw bl
    dw fill
    dw semis

# HOLD  ( c -- )  put a character in front of the number being put out
#   : HOLD  -1 HLD +! HLD @ C! ;
align 4
n_hold:
    db 0x84
    string HOLD
    bytes 0x20 0x20 0xA0
    dw n_blank
hold:
    dw docol
    dw lit
    dw -1
    dw hld
    dw pstor
    dw hld
    dw at
    dw cstor
    dw semis

# PAD  ( -- addr )  a scratch area, 68 bytes above HERE
#   : PAD  HERE 68 + ;
align 4
n_pad:
    db 0x83
    string PA
    db 0xC4                 # D + 0x80
    dw n_hold
pad:
    dw docol
    dw here
    dw lit
    dw 68
    dw plus
    dw semis

# WORD  ( c -- )  move the next word of the input, c its delimiter, to HERE: a
#        length byte, the text, blanks. The input is the block BLK, or the
#        terminal if BLK is 0.
#   : WORD  BLK @ IF BLK @ BLOCK ELSE TIB @ ENDIF
#           IN @ + SWAP ENCLOSE HERE 34 BLANKS IN +!
#           OVER - >R R HERE C! + HERE 1+ R> CMOVE ;
align 4
n_wordd:
    db 0x84
    string WORD
    bytes 0x20 0x20 0xA0
    dw n_pad
wordd:
    dw docol
    dw blk
    dw at
    dw zbran
    dw %offset(wordd1)
    dw blk
    dw at
    dw block
    dw bran
    dw %offset(wordd2)
wordd1:
    dw tib
    dw at
wordd2:
    dw inn
    dw at
    dw plus
    dw swap
    dw encl
    dw here
    dw lit
    dw 34
    dw blank
    dw inn
    dw pstor
    dw over
    dw subb
    dw tor
    dw rr
    dw here
    dw cstor
    dw plus
    dw here
    dw onep
    dw fromr
    dw cmove
    dw semis


# ------------------------------------------------------------------------
# NUMBER INPUT, -FIND

# (NUMBER)  ( d1 addr1 -- d2 addr2 )  take digits from addr1 + 1 on into d
#   : (NUMBER)  BEGIN 1+ DUP >R C@ BASE @ DIGIT WHILE
#               SWAP BASE @ U* DROP ROT BASE @ U* D+
#               DPL @ 1+ IF 1 DPL +! THEN R> REPEAT R> ;
align 4
n_pnumb:
    db 0x88
    string (NUMBER)
    bytes 0x20 0x20 0xA0
    dw n_wordd
pnumb:
    dw docol
pnumb1:
    dw onep
    dw dup
    dw tor
    dw cat
    dw base
    dw at
    dw digit
    dw zbran
    dw %offset(pnumb2)
    dw swap
    dw base
    dw at
    dw ustar
    dw drop
    dw rot
    dw base
    dw at
    dw ustar
    dw dplus
    dw dpl
    dw at
    dw onep
    dw zbran
    dw %offset(pnumb3)
    dw one
    dw dpl
    dw pstor
pnumb3:
    dw fromr
    dw bran
    dw %offset(pnumb1)
pnumb2:
    dw fromr
    dw semis

# NUMBER  ( addr -- d )  the text at addr + 1 as a double number; a point sets DPL
#   : NUMBER  0 0 ROT DUP 1+ C@ 45 = DUP >R + -1
#             BEGIN DPL ! (NUMBER) DUP C@ BL - WHILE
#             DUP C@ 46 - 0 ?ERROR 0 REPEAT
#             DROP R> IF DMINUS THEN ;
align 4
n_numb:
    db 0x86
    string NUMBER
    bytes 0xA0
    dw n_pnumb
numb:
    dw docol
    dw zero
    dw zero
    dw rot
    dw dup
    dw onep
    dw cat
    dw lit
    dw 45
    dw equal
    dw dup
    dw tor
    dw plus
    dw lit
    dw -1
numb1:
    dw dpl
    dw store
    dw pnumb
    dw dup
    dw cat
    dw bl
    dw subb
    dw zbran
    dw %offset(numb2)
    dw dup
    dw cat
    dw lit
    dw 46
    dw subb
    dw zero
    dw qerr
    dw zero
    dw bran
    dw %offset(numb1)
numb2:
    dw drop
    dw fromr
    dw zbran
    dw %offset(numb3)
    dw dminu
numb3:
    dw semis

# -FIND  ( -- pfa b 1 | 0 )  look the next word of the input up in CONTEXT, then CURRENT
#   : -FIND  BL WORD HERE CONTEXT @ @ (FIND)
#            DUP 0= IF DROP HERE LATEST (FIND) THEN ;
align 4
n_dfind:
    db 0x85
    string -FIND
    bytes 0x20 0xA0
    dw n_numb
dfind:
    dw docol
    dw bl
    dw wordd
    dw here
    dw cont
    dw at
    dw at
    dw pfind
    dw dup
    dw zequ
    dw zbran
    dw %offset(dfind1)
    dw drop
    dw here
    dw lates
    dw pfind
dfind1:
    dw semis


# ------------------------------------------------------------------------
# ERRORS, ID.

# (ABORT)  ( -- )
#   : (ABORT)  ABORT ;
align 4
n_pabor:
    db 0x87
    string (ABORT
    db 0xA9                 # ) + 0x80
    dw n_dfind
pabor:
    dw docol
    dw abort
    dw semis

# ERROR  ( n -- in blk )  type the word and the message, empty the stack, leave
#        IN and BLK on it, go to QUIT
#   : ERROR  WARNING @ 0< IF (ABORT) THEN
#            HERE COUNT TYPE ." ? " MESSAGE SP! IN @ BLK @ QUIT ;
align 4
n_error:
    db 0x85
    string ERROR
    bytes 0x20 0xA0
    dw n_pabor
error:
    dw docol
    dw warn
    dw at
    dw zless
    dw zbran
    dw %offset(error1)
    dw pabor
error1:
    dw here
    dw count
    dw typee
    dw pdotq
    db 2
    string ?
    bytes 0x20
align 4
    dw mess
    dw spsto
    dw inn
    dw at
    dw blk
    dw at
    dw quit
    dw semis

# ID.  ( nfa -- )  type a name
#   : ID.  PAD 32 95 FILL DUP PFA LFA OVER - PAD SWAP CMOVE
#          PAD COUNT 31 AND TYPE SPACE ;
align 4
n_iddot:
    db 0x83
    string ID
    db 0xAE                 # . + 0x80
    dw n_error
iddot:
    dw docol
    dw pad
    dw lit
    dw 32
    dw lit
    dw 95
    dw fill
    dw dup
    dw pfa
    dw lfa
    dw over
    dw subb
    dw pad
    dw swap
    dw cmove
    dw pad
    dw count
    dw lit
    dw 31
    dw andd
    dw typee
    dw space
    dw semis


# ------------------------------------------------------------------------
# CREATE
#
# The first line is the model's test for a full dictionary: the user area is
# the first thing above it. The two ALIGN are this port's: one so that the
# name field starts on a cell boundary whatever was allotted before, one so
# that the link field does. WORD left blanks after the name, and the last
# of them takes bit 7. The model's fields are 2 bytes; HERE 4 + here.

# CREATE  ( -- )  make the header of a word named by the next word of the input;
#        its code field points at its parameter field
#   : CREATE  TIB HERE 160 + < 2 ?ERROR
#             ALIGN -FIND IF DROP NFA ID. 4 MESSAGE SPACE THEN
#             HERE DUP C@ WIDTH @ MIN 1+ ALLOT ALIGN
#             DUP 160 TOGGLE HERE 1 - 128 TOGGLE
#             LATEST , CURRENT @ ! HERE 4 + , ;
align 4
n_creat:
    db 0x86
    string CREATE
    bytes 0xA0
    dw n_iddot
creat:
    dw docol
    dw tib
    dw here
    dw lit
    dw 160
    dw plus
    dw less
    dw two
    dw qerr
    dw alignn
    dw dfind
    dw zbran
    dw %offset(creat1)
    dw drop
    dw nfa
    dw iddot
    dw lit
    dw 4
    dw mess
    dw space
creat1:
    dw here
    dw dup
    dw cat
    dw width
    dw at
    dw minn
    dw onep
    dw allot
    dw alignn
    dw dup
    dw lit
    dw 160
    dw toggl
    dw here
    dw one
    dw subb
    dw lit
    dw 128
    dw toggl
    dw lates
    dw comma
    dw curr
    dw at
    dw store
    dw here
    dw lit
    dw 4
    dw plus
    dw comma
    dw semis


# ------------------------------------------------------------------------
# [COMPILE], LITERAL, ?STACK

# [COMPILE]  ( -- )  compile the next word of the input even if it is immediate
#   : [COMPILE]  -FIND 0= 0 ?ERROR DROP CFA , ;  IMMEDIATE
align 4
n_bcomp:
    db 0xC9
    string [COMPILE]
    bytes 0x20 0xA0
    dw n_creat
bcomp:
    dw docol
    dw dfind
    dw zequ
    dw zero
    dw qerr
    dw drop
    dw cfa
    dw comma
    dw semis

# LITERAL  ( n -- )  compiling: compile n as a literal
#   : LITERAL  STATE @ IF COMPILE LIT , THEN ;  IMMEDIATE
align 4
n_liter:
    db 0xC7
    string LITERA
    db 0xCC                 # L + 0x80
    dw n_bcomp
liter:
    dw docol
    dw state
    dw at
    dw zbran
    dw %offset(liter1)
    dw comp
    dw lit
    dw comma
liter1:
    dw semis

# DLITERAL  ( d -- )  compiling: compile d as two literals
#   : DLITERAL  STATE @ IF SWAP [COMPILE] LITERAL [COMPILE] LITERAL THEN ;  IMMEDIATE
align 4
n_dlite:
    db 0xC8
    string DLITERAL
    bytes 0x20 0x20 0xA0
    dw n_liter
dlite:
    dw docol
    dw state
    dw at
    dw zbran
    dw %offset(dlite1)
    dw swap
    dw liter
    dw liter
dlite1:
    dw semis

# ?STACK  ( -- )  error 1 if the stack is empty and more, error 7 if it is full.
#        The model's limits are for its own memory. Here: empty is S0. Full
#        is 8 cells before the return stack, which lies under the data stack:
#        the interpreter itself needs that many between two words.
#   : ?STACK  SP@ S0 @ SWAP < 1 ?ERROR
#             SP@ R0 @ 32 + < 7 ?ERROR ;
align 4
n_qstac:
    db 0x86
    string ?STACK
    bytes 0xA0
    dw n_dlite
qstac:
    dw docol
    dw spat
    dw szero
    dw at
    dw swap
    dw less
    dw one
    dw qerr
    dw spat
    dw rzero
    dw at
    dw lit
    dw 32
    dw plus
    dw less
    dw lit
    dw 7
    dw qerr
    dw semis


# ------------------------------------------------------------------------
# THE TEXT INTERPRETER

# INTERPRET  ( -- )  execute or compile the words of the input, one after the other,
#        until the null word leaves
#   : INTERPRET  BEGIN -FIND IF
#                STATE @ < IF CFA , ELSE CFA EXECUTE THEN ?STACK
#                ELSE HERE NUMBER DPL @ 1+ IF [COMPILE] DLITERAL
#                ELSE DROP [COMPILE] LITERAL THEN ?STACK
#                THEN AGAIN ;
align 4
n_inter:
    db 0x89
    string INTERPRET
    bytes 0x20 0xA0
    dw n_qstac
inter:
    dw docol
inter1:
    dw dfind
    dw zbran
    dw %offset(inter2)
    dw state
    dw at
    dw less
    dw zbran
    dw %offset(inter3)
    dw cfa
    dw comma
    dw bran
    dw %offset(inter4)
inter3:
    dw cfa
    dw exec
inter4:
    dw qstac
    dw bran
    dw %offset(inter5)
inter2:
    dw here
    dw numb
    dw dpl
    dw at
    dw onep
    dw zbran
    dw %offset(inter6)
    dw dlite
    dw bran
    dw %offset(inter7)
inter6:
    dw drop
    dw liter
inter7:
    dw qstac
inter5:
    dw bran
    dw %offset(inter1)
    dw semis


# ------------------------------------------------------------------------
# VOCABULARIES
#
# A vocabulary's body is: a name field that holds one blank, the name field
# address of its newest word, the link to the vocabulary made before it. A
# new vocabulary's newest word is at first the blank name of its parent,
# whose link field is the parent's newest word.
#
# FORTH is made by VOCABULARY in the model. Its body must change with every
# new word, so here it is three cells of RAM at FORTH_VOC, which COLD fills,
# and FORTH is a colon definition.

# IMMEDIATE  ( -- )  make the newest word immediate
#   : IMMEDIATE  LATEST 64 TOGGLE ;
align 4
n_immed:
    db 0x89
    string IMMEDIATE
    bytes 0x20 0xA0
    dw n_inter
immed:
    dw docol
    dw lates
    dw lit
    dw 64
    dw toggl
    dw semis

# VOCABULARY  ( -- )  VOCABULARY name: name makes itself the CONTEXT vocabulary.
#        The blank name is 4 bytes (81 20 20 A0), where the model has A081.
#   : VOCABULARY  <BUILDS 0xA0202081 , CURRENT @ CFA ,
#                 HERE VOC-LINK @ , VOC-LINK !
#                 DOES> 4 + CONTEXT ! ;
align 4
n_vocab:
    db 0x8A
    string VOCABULARY
    bytes 0xA0
    dw n_immed
vocab:
    dw docol
    dw build
    dw lit
    dw 0xA0202081
    dw comma
    dw curr
    dw at
    dw cfa
    dw comma
    dw here
    dw vocl
    dw at
    dw comma
    dw vocl
    dw store
    dw does
    dw lit
    dw 4
    dw plus
    dw cont
    dw store
    dw semis

# FORTH  ( -- )  make FORTH the CONTEXT vocabulary
#   : FORTH  FORTH_VOC+CELL CONTEXT ! ;  IMMEDIATE
align 4
n_forth:
    db 0xC5
    string FORTH
    bytes 0x20 0xA0
    dw n_vocab
forth:
    dw docol
    dw lit
    dw FORTH_VOC+CELL
    dw cont
    dw store
    dw semis

# DEFINITIONS  ( -- )  new words go into the CONTEXT vocabulary
#   : DEFINITIONS  CONTEXT @ CURRENT ! ;
align 4
n_defin:
    db 0x8B
    string DEFINITION
    db 0xD3                 # S + 0x80
    dw n_forth
defin:
    dw docol
    dw cont
    dw at
    dw curr
    dw store
    dw semis

# (  ( -- )  a comment, up to the right parenthesis
#   : (  41 WORD ;  IMMEDIATE
align 4
n_paren:
    db 0xC1
    string (
    bytes 0x20 0xA0
    dw n_defin
paren:
    dw docol
    dw lit
    dw 41
    dw wordd
    dw semis


# ------------------------------------------------------------------------
# QUIT, ABORT, COLD

# QUIT  ( -- )  the outer loop: read a line, interpret it, say OK
#   : QUIT  0 BLK ! [COMPILE] [
#           BEGIN RP! CR QUERY INTERPRET
#           STATE @ 0= IF ." OK" THEN AGAIN ;
align 4
n_quit:
    db 0x84
    string QUIT
    bytes 0x20 0x20 0xA0
    dw n_paren
quit:
    dw docol
    dw zero
    dw blk
    dw store
    dw lbrac
quit1:
    dw rpsto
    dw cr
    dw query
    dw inter
    dw state
    dw at
    dw zequ
    dw zbran
    dw %offset(quit2)
    dw pdotq
    db 2
    string OK
align 4
quit2:
    dw bran
    dw %offset(quit1)
    dw semis

# ABORT  ( -- )  empty the stacks, say who we are, go to QUIT
#   : ABORT  SP! DECIMAL DR0 CR ." fig-FORTH RISC-V"
#            [COMPILE] FORTH DEFINITIONS QUIT ;
align 4
n_abort:
    db 0x85
    string ABORT
    bytes 0x20 0xA0
    dw n_quit
abort:
    dw docol
    dw spsto
    dw decim
    dw drzer
    dw cr
    dw pdotq
    db 16
    string fig-FORTH RISC-V
align 4
    dw forth
    dw defin
    dw quit
    dw semis

# COLD  ( -- )  the cold start. The code is in the nucleus.
align 4
n_coldw:
    db 0x84
    string COLD
    bytes 0x20 0x20 0xA0
    dw n_abort
coldw:
    dw cold

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


# ------------------------------------------------------------------------
# ARITHMETIC

# +-  ( n1 n2 -- n3 )  n1 with its sign changed if n2 is negative
#   : +-  0< IF MINUS THEN ;
align 4
n_pm:
    db 0x82
    string +-
    bytes 0xA0
    dw n_coldw
pm:
    dw docol
    dw zless
    dw zbran
    dw %offset(pm1)
    dw minus
pm1:
    dw semis

# D+-  ( d1 n -- d2 )
#   : D+-  0< IF DMINUS THEN ;
align 4
n_dpm:
    db 0x83
    string D+
    db 0xAD                 # - + 0x80
    dw n_pm
dpm:
    dw docol
    dw zless
    dw zbran
    dw %offset(dpm1)
    dw dminu
dpm1:
    dw semis

# ABS  ( n -- u )
#   : ABS  DUP +- ;
align 4
n_abss:
    db 0x83
    string AB
    db 0xD3                 # S + 0x80
    dw n_dpm
abss:
    dw docol
    dw dup
    dw pm
    dw semis

# DABS  ( d -- ud )
#   : DABS  DUP D+- ;
align 4
n_dabs:
    db 0x84
    string DABS
    bytes 0x20 0x20 0xA0
    dw n_abss
dabs:
    dw docol
    dw dup
    dw dpm
    dw semis

# MIN  ( n1 n2 -- n )
#   : MIN  OVER OVER > IF SWAP THEN DROP ;
align 4
n_minn:
    db 0x83
    string MI
    db 0xCE                 # N + 0x80
    dw n_dabs
minn:
    dw docol
    dw over
    dw over
    dw great
    dw zbran
    dw %offset(minn1)
    dw swap
minn1:
    dw drop
    dw semis

# MAX  ( n1 n2 -- n )
#   : MAX  OVER OVER < IF SWAP THEN DROP ;
align 4
n_maxx:
    db 0x83
    string MA
    db 0xD8                 # X + 0x80
    dw n_minn
maxx:
    dw docol
    dw over
    dw over
    dw less
    dw zbran
    dw %offset(maxx1)
    dw swap
maxx1:
    dw drop
    dw semis

# M*  ( n1 n2 -- d )
#   : M*  OVER OVER XOR >R ABS SWAP ABS U* R> D+- ;
align 4
n_mstar:
    db 0x82
    string M*
    bytes 0xA0
    dw n_maxx
mstar:
    dw docol
    dw over
    dw over
    dw xorr
    dw tor
    dw abss
    dw swap
    dw abss
    dw ustar
    dw fromr
    dw dpm
    dw semis

# M/  ( d n -- remainder quotient )  the remainder has the sign of d
#   : M/  OVER >R >R DABS R ABS U/
#         R> R XOR +- SWAP R> +- SWAP ;
align 4
n_mslas:
    db 0x82
    string M/
    bytes 0xA0
    dw n_mstar
mslas:
    dw docol
    dw over
    dw tor
    dw tor
    dw dabs
    dw rr
    dw abss
    dw uslas
    dw fromr
    dw rr
    dw xorr
    dw pm
    dw swap
    dw fromr
    dw pm
    dw swap
    dw semis

# *  ( n1 n2 -- n )
#   : *  U* DROP ;
align 4
n_star:
    db 0x81
    string *
    bytes 0x20 0xA0
    dw n_mslas
star:
    dw docol
    dw ustar
    dw drop
    dw semis

# /MOD  ( n1 n2 -- remainder quotient )
#   : /MOD  >R S->D R> M/ ;
align 4
n_slmod:
    db 0x84
    string /MOD
    bytes 0x20 0x20 0xA0
    dw n_star
slmod:
    dw docol
    dw tor
    dw stod
    dw fromr
    dw mslas
    dw semis

# /  ( n1 n2 -- quotient )
#   : /  /MOD SWAP DROP ;
align 4
n_slash:
    db 0x81
    string /
    bytes 0x20 0xA0
    dw n_slmod
slash:
    dw docol
    dw slmod
    dw swap
    dw drop
    dw semis

# MOD  ( n1 n2 -- remainder )
#   : MOD  /MOD DROP ;
align 4
n_modd:
    db 0x83
    string MO
    db 0xC4                 # D + 0x80
    dw n_slash
modd:
    dw docol
    dw slmod
    dw drop
    dw semis

# */MOD  ( n1 n2 n3 -- remainder quotient )  n1 * n2 / n3, the product a double number
#   : */MOD  >R M* R> M/ ;
align 4
n_ssmod:
    db 0x85
    string */MOD
    bytes 0x20 0xA0
    dw n_modd
ssmod:
    dw docol
    dw tor
    dw mstar
    dw fromr
    dw mslas
    dw semis

# */  ( n1 n2 n3 -- n )
#   : */  */MOD SWAP DROP ;
align 4
n_ssla:
    db 0x82
    string */
    bytes 0xA0
    dw n_ssmod
ssla:
    dw docol
    dw ssmod
    dw swap
    dw drop
    dw semis

# M/MOD  ( ud1 u2 -- u3 ud4 )  unsigned: remainder u3, double quotient ud4
#   : M/MOD  >R 0 R U/ R> SWAP >R U/ R> ;
align 4
n_msmod:
    db 0x85
    string M/MOD
    bytes 0x20 0xA0
    dw n_ssla
msmod:
    dw docol
    dw tor
    dw zero
    dw rr
    dw uslas
    dw fromr
    dw swap
    dw tor
    dw uslas
    dw fromr
    dw semis


# ------------------------------------------------------------------------
# THE DISC: BUFFERS
#
# The disc is the flash from LO to HI, 46 KiB: blocks 0 to 183, screens 0 to
# 45. A block is 256 bytes, one page of the flash, and a screen is 4 blocks.
#
# A buffer is the block number in a cell (its top bit says the block was
# changed and is to be written), the block, and a cell of nulls. So the 2
# of the model is 4 here, its 8000 is 80000000, and a buffer is B/BUF + 8.
#
# USE and PREV are variables in the model, with their values in the
# dictionary. The kernel is in flash, so here they are user variables.

# USE  ( -- addr )  the buffer to use next, the stalest
align 4
n_use:
    db 0x83
    string US
    db 0xC5                 # E + 0x80
    dw n_msmod
use:
    dw douse
    dw 0x64

# PREV  ( -- addr )  the buffer used last
align 4
n_prev:
    db 0x84
    string PREV
    bytes 0x20 0x20 0xA0
    dw n_use
prev:
    dw douse
    dw 0x68

# +BUF  ( addr1 -- addr2 f )  the next buffer; f is false if it is PREV
#   : +BUF  BUF_SIZE + DUP LIMIT = IF DROP FIRST ENDIF
#           DUP PREV @ - ;
align 4
n_pbuf:
    db 0x84
    string +BUF
    bytes 0x20 0x20 0xA0
    dw n_prev
pbuf:
    dw docol
    dw lit
    dw BUF_SIZE
    dw plus
    dw dup
    dw limit
    dw equal
    dw zbran
    dw %offset(pbuf1)
    dw drop
    dw first
pbuf1:
    dw dup
    dw prev
    dw at
    dw subb
    dw semis

# UPDATE  ( -- )  mark the buffer used last as changed
#   : UPDATE  PREV @ @ 0x80000000 OR PREV @ ! ;
align 4
n_updat:
    db 0x86
    string UPDATE
    bytes 0xA0
    dw n_pbuf
updat:
    dw docol
    dw prev
    dw at
    dw at
    dw lit
    dw 0x80000000
    dw orr
    dw prev
    dw at
    dw store
    dw semis

# EMPTY-BUFFERS  ( -- )  clear the buffers; nothing is written
#   : EMPTY-BUFFERS  FIRST LIMIT OVER - ERASE ;
align 4
n_mtbuf:
    db 0x8D
    string EMPTY-BUFFERS
    bytes 0x20 0xA0
    dw n_updat
mtbuf:
    dw docol
    dw first
    dw limit
    dw over
    dw subb
    dw erase
    dw semis

# DR0  ( -- )  drive 0. There is one drive: no DR1.
#   : DR0  0 OFFSET ! ;
align 4
n_drzer:
    db 0x83
    string DR
    db 0xB0                 # 0 + 0x80
    dw n_mtbuf
drzer:
    dw docol
    dw zero
    dw ofset
    dw store
    dw semis

# BUFFER  ( n -- addr )  give block n the stalest buffer, which is first written
#        to the disc if it was changed; the block is not read
#   : BUFFER  USE @ DUP >R
#             BEGIN +BUF UNTIL USE !
#             R @ 0< IF R 4 + R @ 0x7FFFFFFF AND 0 R/W ENDIF
#             R ! R PREV ! R> 4 + ;
align 4
n_buffe:
    db 0x86
    string BUFFER
    bytes 0xA0
    dw n_drzer
buffe:
    dw docol
    dw use
    dw at
    dw dup
    dw tor
buffe1:
    dw pbuf
    dw zbran
    dw %offset(buffe1)
    dw use
    dw store
    dw rr
    dw at
    dw zless
    dw zbran
    dw %offset(buffe2)
    dw rr
    dw lit
    dw 4
    dw plus
    dw rr
    dw at
    dw lit
    dw 0x7FFFFFFF
    dw andd
    dw zero
    dw rslw
buffe2:
    dw rr
    dw store
    dw rr
    dw prev
    dw store
    dw fromr
    dw lit
    dw 4
    dw plus
    dw semis

# BLOCK  ( n -- addr )  the address of block n in a buffer, read from the disc if
#        no buffer holds it
#   : BLOCK  OFFSET @ + >R
#            PREV @ DUP @ R - DUP +
#            IF BEGIN +BUF 0=
#            IF DROP R BUFFER DUP R 1 R/W 4 - ENDIF
#            DUP @ R - DUP + 0= UNTIL
#            DUP PREV ! ENDIF
#            R> DROP 4 + ;
align 4
n_block:
    db 0x85
    string BLOCK
    bytes 0x20 0xA0
    dw n_buffe
block:
    dw docol
    dw ofset
    dw at
    dw plus
    dw tor
    dw prev
    dw at
    dw dup
    dw at
    dw rr
    dw subb
    dw dup
    dw plus
    dw zbran
    dw %offset(block1)
block2:
    dw pbuf
    dw zequ
    dw zbran
    dw %offset(block3)
    dw drop
    dw rr
    dw buffe
    dw dup
    dw rr
    dw one
    dw rslw
    dw lit
    dw 4
    dw subb
block3:
    dw dup
    dw at
    dw rr
    dw subb
    dw dup
    dw plus
    dw zequ
    dw zbran
    dw %offset(block2)
    dw dup
    dw prev
    dw store
block1:
    dw fromr
    dw drop
    dw lit
    dw 4
    dw plus
    dw semis


# ------------------------------------------------------------------------
# THE DISC: LINES, MESSAGE, LOAD
#
# MESSAGE types line n of screen 4 if WARNING is 1, as in the model. The
# messages are not on the disc until someone puts them there.

# (LINE)  ( line scr -- addr 64 )  a line of a screen, in its buffer
#   : (LINE)  >R C/L B/BUF */MOD R> B/SCR * +
#             BLOCK + C/L ;
align 4
n_pline:
    db 0x86
    string (LINE)
    bytes 0xA0
    dw n_block
pline:
    dw docol
    dw tor
    dw csll
    dw bbuf
    dw ssmod
    dw fromr
    dw bscr
    dw star
    dw plus
    dw block
    dw plus
    dw csll
    dw semis

# .LINE  ( line scr -- )  type it
#   : .LINE  (LINE) -TRAILING TYPE ;
align 4
n_dline:
    db 0x85
    string .LINE
    bytes 0x20 0xA0
    dw n_pline
dline:
    dw docol
    dw pline
    dw dtrai
    dw typee
    dw semis

# MESSAGE  ( n -- )  type message n: a line of the disc, or its number
#   : MESSAGE  WARNING @ IF
#              -DUP IF 4 OFFSET @ B/SCR / - .LINE ENDIF
#              ELSE ." MSG # " . ENDIF ;
align 4
n_mess:
    db 0x87
    string MESSAG
    db 0xC5                 # E + 0x80
    dw n_dline
mess:
    dw docol
    dw warn
    dw at
    dw zbran
    dw %offset(mess1)
    dw ddup
    dw zbran
    dw %offset(mess2)
    dw lit
    dw 4
    dw ofset
    dw at
    dw bscr
    dw slash
    dw subb
    dw dline
mess2:
    dw bran
    dw %offset(mess3)
mess1:
    dw pdotq
    db 6
    bytes 0x4D 0x53 0x47 0x20 0x23 0x20    # MSG #
align 4
    dw dot
mess3:
    dw semis

# LOAD  ( scr -- )  interpret a screen
#   : LOAD  BLK @ >R IN @ >R 0 IN ! B/SCR * BLK !
#           INTERPRET R> IN ! R> BLK ! ;
align 4
n_load:
    db 0x84
    string LOAD
    bytes 0x20 0x20 0xA0
    dw n_mess
load:
    dw docol
    dw blk
    dw at
    dw tor
    dw inn
    dw at
    dw tor
    dw zero
    dw inn
    dw store
    dw bscr
    dw star
    dw blk
    dw store
    dw inter
    dw fromr
    dw inn
    dw store
    dw fromr
    dw blk
    dw store
    dw semis

# -->  ( -- )  go on with the next screen
#   : -->  ?LOADING 0 IN ! B/SCR BLK @ OVER MOD - BLK +! ;  IMMEDIATE
align 4
n_arrow:
    db 0xC3
    string --
    db 0xBE                 # > + 0x80
    dw n_load
arrow:
    dw docol
    dw qload
    dw zero
    dw inn
    dw store
    dw bscr
    dw blk
    dw at
    dw over
    dw modd
    dw subb
    dw blk
    dw pstor
    dw semis


# ------------------------------------------------------------------------
# THE DISC: R/W
#
# The installation dependent part. The model's R/W drives a disc controller;
# its manual also gives one that keeps the blocks in memory, between LO and
# HI, for a system that has no disc:
#
#   : R/W  >R B/BUF * LO + DUP HI > 6 ?ERROR  R> IF SWAP ENDIF  B/BUF CMOVE ;
#
# This is that one. The flash is memory to read, so reading is its CMOVE.
# Writing is BLOCK-WRITE, a CODE word: the board erases and programs the
# page and reads it back. The range check is for both ends, since below LO
# is the kernel.

# LO  ( -- addr )  the start of the disc
align 4
n_dlo:
    db 0x82
    string LO
    bytes 0xA0
    dw n_arrow
dlo:
    dw docon
    dw DISC_LO

# HI  ( -- addr )  its end
align 4
n_dhi:
    db 0x82
    string HI
    bytes 0xA0
    dw n_dlo
dhi:
    dw docon
    dw DISC_HI

# BLOCK-WRITE  ( from to -- f )  write the 256 bytes at from (RAM, on a cell boundary)
#        to the block of the disc at to. f is true if the flash does not
#        hold them afterwards.
align 4
n_blkwr:
    db 0x8B
    string BLOCK-WRIT
    db 0xC5                 # E + 0x80
    dw n_dhi
blkwr:
    dw blkwr + CELL
    lw a0, 0(DSP)
    lw a2, CELL(DSP)
    addi DSP, DSP, CELL
    jal ra, disc_write          # not `call`: bronzebeard gets that wrong beyond 2 KiB
    mv a1, a0
    j put

# R/W  ( addr blk f -- )  read (f = 1) or write (f = 0) block blk at addr.
#        Error 6 is DISC RANGE, error 8 DISC ERROR.
#   : R/W  >R B/BUF * LO + DUP LO < OVER HI B/BUF - > OR 6 ?ERROR
#          R> IF SWAP B/BUF CMOVE
#          ELSE BLOCK-WRITE 8 ?ERROR ENDIF ;
align 4
n_rslw:
    db 0x83
    string R/
    db 0xD7                 # W + 0x80
    dw n_blkwr
rslw:
    dw docol
    dw tor
    dw bbuf
    dw star
    dw dlo
    dw plus
    dw dup
    dw dlo
    dw less
    dw over
    dw dhi
    dw bbuf
    dw subb
    dw great
    dw orr
    dw lit
    dw 6
    dw qerr
    dw fromr
    dw zbran
    dw %offset(rslw1)
    dw swap
    dw bbuf
    dw cmove
    dw bran
    dw %offset(rslw2)
rslw1:
    dw blkwr
    dw lit
    dw 8
    dw qerr
rslw2:
    dw semis


# ------------------------------------------------------------------------
# TICK AND FORGET

# '  ( -- pfa )  the parameter field of the next word of the input; compiling,
#        a literal
#   : '  -FIND 0= 0 ?ERROR DROP [COMPILE] LITERAL ;  IMMEDIATE
align 4
n_tick:
    db 0xC1
    bytes 0x27 0x20 0xA0    # '
    dw n_rslw
tick:
    dw docol
    dw dfind
    dw zequ
    dw zero
    dw qerr
    dw drop
    dw liter
    dw semis

# FORGET  ( -- )  FORGET name: take name and all words after it out of the
#        dictionary. The kernel is below FENCE.
#   : FORGET  CURRENT @ CONTEXT @ - 24 ?ERROR
#             [COMPILE] ' DUP FENCE @ < 21 ?ERROR
#             DUP NFA DP ! LFA @ CURRENT @ ! ;
align 4
n_forge:
    db 0x86
    string FORGET
    bytes 0xA0
    dw n_tick
forge:
    dw docol
    dw curr
    dw at
    dw cont
    dw at
    dw subb
    dw lit
    dw 24
    dw qerr
    dw tick
    dw dup
    dw fence
    dw at
    dw less
    dw lit
    dw 21
    dw qerr
    dw dup
    dw nfa
    dw dp
    dw store
    dw lfa
    dw at
    dw curr
    dw at
    dw store
    dw semis


# ------------------------------------------------------------------------
# THE CONDITIONALS
#
# The 1, 2, 3 and 4 they leave on the stack while compiling are pairing
# marks, not sizes: they are the model's.

# BACK  ( addr -- )  compile the distance back to addr
#   : BACK  HERE - , ;
align 4
n_back:
    db 0x84
    string BACK
    bytes 0x20 0x20 0xA0
    dw n_forge
back:
    dw docol
    dw here
    dw subb
    dw comma
    dw semis

# BEGIN
#   : BEGIN  ?COMP HERE 1 ;  IMMEDIATE
align 4
n_begin:
    db 0xC5
    string BEGIN
    bytes 0x20 0xA0
    dw n_back
begin:
    dw docol
    dw qcomp
    dw here
    dw one
    dw semis

# ENDIF
#   : ENDIF  ?COMP 2 ?PAIRS HERE OVER - SWAP ! ;  IMMEDIATE
align 4
n_endif:
    db 0xC5
    string ENDIF
    bytes 0x20 0xA0
    dw n_begin
endif:
    dw docol
    dw qcomp
    dw two
    dw qpair
    dw here
    dw over
    dw subb
    dw swap
    dw store
    dw semis

# THEN
#   : THEN  [COMPILE] ENDIF ;  IMMEDIATE
align 4
n_then:
    db 0xC4
    string THEN
    bytes 0x20 0x20 0xA0
    dw n_endif
then:
    dw docol
    dw endif
    dw semis

# DO
#   : DO  COMPILE (DO) HERE 3 ;  IMMEDIATE
align 4
n_do:
    db 0xC2
    string DO
    bytes 0xA0
    dw n_then
do:
    dw docol
    dw comp
    dw xdo
    dw here
    dw three
    dw semis

# LOOP
#   : LOOP  3 ?PAIRS COMPILE (LOOP) BACK ;  IMMEDIATE
align 4
n_loop:
    db 0xC4
    string LOOP
    bytes 0x20 0x20 0xA0
    dw n_do
loop:
    dw docol
    dw three
    dw qpair
    dw comp
    dw xloop
    dw back
    dw semis

# +LOOP
#   : +LOOP  3 ?PAIRS COMPILE (+LOOP) BACK ;  IMMEDIATE
align 4
n_ploop:
    db 0xC5
    string +LOOP
    bytes 0x20 0xA0
    dw n_loop
ploop:
    dw docol
    dw three
    dw qpair
    dw comp
    dw xploo
    dw back
    dw semis

# UNTIL
#   : UNTIL  1 ?PAIRS COMPILE 0BRANCH BACK ;  IMMEDIATE
align 4
n_until:
    db 0xC5
    string UNTIL
    bytes 0x20 0xA0
    dw n_ploop
until:
    dw docol
    dw one
    dw qpair
    dw comp
    dw zbran
    dw back
    dw semis

# END
#   : END  [COMPILE] UNTIL ;  IMMEDIATE
align 4
n_endd:
    db 0xC3
    string EN
    db 0xC4                 # D + 0x80
    dw n_until
endd:
    dw docol
    dw until
    dw semis

# AGAIN
#   : AGAIN  1 ?PAIRS COMPILE BRANCH BACK ;  IMMEDIATE
align 4
n_again:
    db 0xC5
    string AGAIN
    bytes 0x20 0xA0
    dw n_endd
again:
    dw docol
    dw one
    dw qpair
    dw comp
    dw bran
    dw back
    dw semis

# REPEAT
#   : REPEAT  >R >R [COMPILE] AGAIN R> R> 2 - [COMPILE] ENDIF ;  IMMEDIATE
align 4
n_repea:
    db 0xC6
    string REPEAT
    bytes 0xA0
    dw n_again
repea:
    dw docol
    dw tor
    dw tor
    dw again
    dw fromr
    dw fromr
    dw two
    dw subb
    dw endif
    dw semis

# IF
#   : IF  COMPILE 0BRANCH HERE 0 , 2 ;  IMMEDIATE
align 4
n_iff:
    db 0xC2
    string IF
    bytes 0xA0
    dw n_repea
iff:
    dw docol
    dw comp
    dw zbran
    dw here
    dw zero
    dw comma
    dw two
    dw semis

# ELSE
#   : ELSE  2 ?PAIRS COMPILE BRANCH HERE 0 ,
#           SWAP 2 [COMPILE] ENDIF 2 ;  IMMEDIATE
align 4
n_elsee:
    db 0xC4
    string ELSE
    bytes 0x20 0x20 0xA0
    dw n_iff
elsee:
    dw docol
    dw two
    dw qpair
    dw comp
    dw bran
    dw here
    dw zero
    dw comma
    dw swap
    dw two
    dw endif
    dw two
    dw semis

# WHILE
#   : WHILE  [COMPILE] IF 2+ ;  IMMEDIATE
align 4
n_whilee:
    db 0xC5
    string WHILE
    bytes 0x20 0xA0
    dw n_elsee
whilee:
    dw docol
    dw iff
    dw twop
    dw semis


# ------------------------------------------------------------------------
# NUMBER OUTPUT

# SPACES  ( n -- )
#   : SPACES  0 MAX -DUP IF 0 DO SPACE LOOP THEN ;
align 4
n_spacs:
    db 0x86
    string SPACES
    bytes 0xA0
    dw n_whilee
spacs:
    dw docol
    dw zero
    dw maxx
    dw ddup
    dw zbran
    dw %offset(spacs1)
    dw zero
    dw xdo
spacs2:
    dw space
    dw xloop
    dw %offset(spacs2)
spacs1:
    dw semis

# <#  ( -- )  start a number: it is built downward from PAD
#   : <#  PAD HLD ! ;
align 4
n_bdigs:
    db 0x82
    bytes 0x3C 0x23 0xA0    # <#
    dw n_spacs
bdigs:
    dw docol
    dw pad
    dw hld
    dw store
    dw semis

# #>  ( d -- addr n )  end it: the text
#   : #>  DROP DROP HLD @ PAD OVER - ;
align 4
n_edigs:
    db 0x82
    bytes 0x23 0x3E 0xA0    # #>
    dw n_bdigs
edigs:
    dw docol
    dw drop
    dw drop
    dw hld
    dw at
    dw pad
    dw over
    dw subb
    dw semis

# SIGN  ( n d -- d )  a minus sign if n is negative
#   : SIGN  ROT 0< IF 45 HOLD THEN ;
align 4
n_sign:
    db 0x84
    string SIGN
    bytes 0x20 0x20 0xA0
    dw n_edigs
sign:
    dw docol
    dw rot
    dw zless
    dw zbran
    dw %offset(sign1)
    dw lit
    dw 45
    dw hold
sign1:
    dw semis

# #  ( d1 -- d2 )  one digit
#   : #  BASE @ M/MOD ROT 9 OVER < IF 7 + THEN 48 + HOLD ;
align 4
n_dig:
    db 0x81
    bytes 0x23 0x20 0xA0    # #
    dw n_sign
dig:
    dw docol
    dw base
    dw at
    dw msmod
    dw rot
    dw lit
    dw 9
    dw over
    dw less
    dw zbran
    dw %offset(dig1)
    dw lit
    dw 7
    dw plus
dig1:
    dw lit
    dw 48
    dw plus
    dw hold
    dw semis

# #S  ( d -- 0 0 )  all the digits
#   : #S  BEGIN # OVER OVER OR 0= UNTIL ;
align 4
n_digs:
    db 0x82
    bytes 0x23 0x53 0xA0    # #S
    dw n_dig
digs:
    dw docol
digs1:
    dw dig
    dw over
    dw over
    dw orr
    dw zequ
    dw zbran
    dw %offset(digs1)
    dw semis

# D.R  ( d n -- )  type d at the right of a field of n
#   : D.R  >R SWAP OVER DABS <# #S SIGN #>
#          R> OVER - SPACES TYPE ;
align 4
n_ddotr:
    db 0x83
    string D.
    db 0xD2                 # R + 0x80
    dw n_digs
ddotr:
    dw docol
    dw tor
    dw swap
    dw over
    dw dabs
    dw bdigs
    dw digs
    dw sign
    dw edigs
    dw fromr
    dw over
    dw subb
    dw spacs
    dw typee
    dw semis

# D.  ( d -- )
#   : D.  0 D.R SPACE ;
align 4
n_ddot:
    db 0x82
    string D.
    bytes 0xA0
    dw n_ddotr
ddot:
    dw docol
    dw zero
    dw ddotr
    dw space
    dw semis

# .R  ( n1 n2 -- )  type n1 at the right of a field of n2
#   : .R  >R S->D R> D.R ;
align 4
n_dotr:
    db 0x82
    string .R
    bytes 0xA0
    dw n_ddot
dotr:
    dw docol
    dw tor
    dw stod
    dw fromr
    dw ddotr
    dw semis

# .  ( n -- )
#   : .  S->D D. ;
align 4
n_dot:
    db 0x81
    string .
    bytes 0x20 0xA0
    dw n_dotr
dot:
    dw docol
    dw stod
    dw ddot
    dw semis

# ?  ( addr -- )  type the cell at addr
#   : ?  @ . ;
align 4
n_ques:
    db 0x81
    string ?
    bytes 0x20 0xA0
    dw n_dot
ques:
    dw docol
    dw at
    dw dot
    dw semis


# ------------------------------------------------------------------------
# LIST, INDEX, TRIAD

# LIST  ( scr -- )  type a screen
#   : LIST  DECIMAL CR DUP SCR !
#           ." SCR # " . 16 0 DO CR I 3 .R SPACE
#           I SCR @ .LINE LOOP CR ;
align 4
n_listt:
    db 0x84
    string LIST
    bytes 0x20 0x20 0xA0
    dw n_ques
listt:
    dw docol
    dw decim
    dw cr
    dw dup
    dw scr
    dw store
    dw pdotq
    db 6
    bytes 0x53 0x43 0x52 0x20 0x23 0x20    # SCR #
align 4
    dw dot
    dw lit
    dw 16
    dw zero
    dw xdo
listt1:
    dw cr
    dw ido
    dw three
    dw dotr
    dw space
    dw ido
    dw scr
    dw at
    dw dline
    dw xloop
    dw %offset(listt1)
    dw cr
    dw semis

# INDEX  ( from to -- )  type the first line of each screen
#   : INDEX  12 EMIT CR 1+ SWAP
#            DO CR I 3 .R SPACE
#            0 I .LINE
#            ?TERMINAL IF LEAVE ENDIF LOOP ;
align 4
n_index:
    db 0x85
    string INDEX
    bytes 0x20 0xA0
    dw n_listt
index:
    dw docol
    dw lit
    dw 12
    dw emit
    dw cr
    dw onep
    dw swap
    dw xdo
index1:
    dw cr
    dw ido
    dw three
    dw dotr
    dw space
    dw zero
    dw ido
    dw dline
    dw qterm
    dw zbran
    dw %offset(index2)
    dw leave
index2:
    dw xloop
    dw %offset(index1)
    dw semis

# TRIAD  ( scr -- )  type the three screens of the page that holds scr, and
#        message 15 under them
#   : TRIAD  12 EMIT 3 / 3 * 3 OVER + SWAP
#            DO CR I LIST LOOP CR
#            15 MESSAGE CR ;
align 4
n_triad:
    db 0x85
    string TRIAD
    bytes 0x20 0xA0
    dw n_index
triad:
    dw docol
    dw lit
    dw 12
    dw emit
    dw three
    dw slash
    dw three
    dw star
    dw three
    dw over
    dw plus
    dw swap
    dw xdo
triad1:
    dw cr
    dw ido
    dw listt
    dw xloop
    dw %offset(triad1)
    dw cr
    dw lit
    dw 15
    dw mess
    dw cr
    dw semis


# ------------------------------------------------------------------------
# VLIST

# VLIST  ( -- )  type the names of the CONTEXT vocabulary; a key stops it
#   : VLIST  128 OUT ! CONTEXT @ @
#            BEGIN OUT @ C/L > IF CR 0 OUT ! THEN
#            DUP ID. SPACE SPACE PFA LFA @
#            DUP 0= ?TERMINAL OR UNTIL DROP ;
align 4
n_vlist:
    db 0x85
    string VLIST
    bytes 0x20 0xA0
    dw n_triad
vlist:
    dw docol
    dw lit
    dw 128
    dw out
    dw store
    dw cont
    dw at
    dw at
vlist1:
    dw out
    dw at
    dw csll
    dw great
    dw zbran
    dw %offset(vlist2)
    dw cr
    dw zero
    dw out
    dw store
vlist2:
    dw dup
    dw iddot
    dw space
    dw space
    dw pfa
    dw lfa
    dw at
    dw dup
    dw zequ
    dw qterm
    dw orr
    dw zbran
    dw %offset(vlist1)
    dw drop
    dw semis


# ------------------------------------------------------------------------
# THE EDITOR: TEXT, LINE, WHERE
#
# Screens 87 to 97 of the manual, the sample editor. Its last screen puts the
# editor below FENCE and makes it part of the system that a cold start
# brings up; this is that system. Three words are in FORTH, the rest in the
# EDITOR vocabulary.
#
# EDITOR is made by VOCABULARY in the model. Like FORTH, its body is three
# cells of RAM that COLD fills (EDITOR_VOC), and it is a colon definition.

# TEXT  ( c -- )  take the text up to the delimiter c to PAD, with blanks to
#        the length of a line
#   : TEXT  HERE C/L 1+ BLANKS WORD HERE PAD C/L 1+ CMOVE ;
align 4
n_text:
    db 0x84
    string TEXT
    bytes 0x20 0x20 0xA0
    dw n_vlist
text:
    dw docol
    dw here
    dw csll
    dw onep
    dw blank
    dw wordd
    dw here
    dw pad
    dw csll
    dw onep
    dw cmove
    dw semis

# LINE  ( n -- addr )  line n of the screen SCR; error 23 unless n is 0 to 15
#   : LINE  DUP -16 AND 23 ?ERROR SCR @ (LINE) DROP ;
align 4
n_line:
    db 0x84
    string LINE
    bytes 0x20 0x20 0xA0
    dw n_text
line:
    dw docol
    dw dup
    dw lit
    dw -16
    dw andd
    dw lit
    dw 23
    dw qerr
    dw scr
    dw at
    dw pline
    dw drop
    dw semis

# EDITOR  ( -- )  make EDITOR the CONTEXT vocabulary
#   : EDITOR  EDITOR_VOC+CELL CONTEXT ! ;  IMMEDIATE
align 4
n_editor:
    db 0xC6
    string EDITOR
    bytes 0xA0
    dw n_line
editor:
    dw docol
    dw lit
    dw EDITOR_VOC+CELL
    dw cont
    dw store
    dw semis

# WHERE  ( in blk -- )  after an error in a LOAD, with the two numbers the error
#        left: show the screen and the line, mark the place, enter the editor
#   : WHERE  DUP B/SCR / DUP SCR ! ." SCR # " DECIMAL .
#            SWAP C/L /MOD C/L * ROT BLOCK + CR C/L TYPE
#            CR HERE C@ - SPACES 94 EMIT [COMPILE] EDITOR QUIT ;
align 4
n_where:
last_nfa:
    db 0x85
    string WHERE
    bytes 0x20 0xA0
    dw n_editor
where:
    dw docol
    dw dup
    dw bscr
    dw slash
    dw dup
    dw scr
    dw store
    dw pdotq
    db 6
    bytes 0x53 0x43 0x52 0x20 0x23 0x20    # SCR #
align 4
    dw decim
    dw dot
    dw swap
    dw csll
    dw slmod
    dw csll
    dw star
    dw rot
    dw block
    dw plus
    dw cr
    dw csll
    dw typee
    dw cr
    dw here
    dw cat
    dw subb
    dw spacs
    dw lit
    dw 94
    dw emit
    dw editor
    dw quit
    dw semis


# ------------------------------------------------------------------------
# THE EDITOR VOCABULARY: LINES
#
# The link field of the first word holds the address of FORTH's blank name,
# which is what VOCABULARY puts into a new vocabulary: a search goes on
# from there into FORTH.
#
# Some of these words have the names of FORTH words: I and R. Where the
# model writes FORTH I or FORTH R it means the old one, and so does the
# thread. R# is the cursor: its offset from the start of the screen.

# #LOCATE  ( -- offset line )  where the cursor is
#   : #LOCATE  R# @ C/L /MOD ;
align 4
n_e_locat:
    db 0x87
    bytes 0x23 0x4C 0x4F 0x43 0x41 0x54 0xC5 # #LOCATE
    dw FORTH_VOC                # the blank name of FORTH: on into FORTH
e_locat:
    dw docol
    dw rnum
    dw at
    dw csll
    dw slmod
    dw semis

# #LEAD  ( -- addr offset )  the cursor's line and the offset in it
#   : #LEAD  #LOCATE LINE SWAP ;
align 4
n_e_lead:
    db 0x85
    bytes 0x23 0x4C 0x45 0x41 0x44 0x20 0xA0 # #LEAD
    dw n_e_locat
e_lead:
    dw docol
    dw e_locat
    dw line
    dw swap
    dw semis

# #LAG  ( -- addr n )  the cursor's address and the characters after it
#   : #LAG  #LEAD DUP >R + C/L R> - ;
align 4
n_e_lag:
    db 0x84
    bytes 0x23 0x4C 0x41 0x47 0x20 0x20 0xA0 # #LAG
    dw n_e_lead
e_lag:
    dw docol
    dw e_lead
    dw dup
    dw tor
    dw plus
    dw csll
    dw fromr
    dw subb
    dw semis

# -MOVE  ( addr n -- )  move a line from addr to line n
#   : -MOVE  LINE C/L CMOVE UPDATE ;
align 4
n_e_move:
    db 0x85
    string -MOVE
    bytes 0x20 0xA0
    dw n_e_lag
e_move:
    dw docol
    dw line
    dw csll
    dw cmove
    dw updat
    dw semis

# H  ( n -- )  hold line n at PAD
#   : H  LINE PAD 1+ C/L DUP PAD C! CMOVE ;
align 4
n_e_h:
    db 0x81
    string H
    bytes 0x20 0xA0
    dw n_e_move
e_h:
    dw docol
    dw line
    dw pad
    dw onep
    dw csll
    dw dup
    dw pad
    dw cstor
    dw cmove
    dw semis

# E  ( n -- )  erase line n with blanks
#   : E  LINE C/L BLANKS UPDATE ;
align 4
n_e_e:
    db 0x81
    string E
    bytes 0x20 0xA0
    dw n_e_h
e_e:
    dw docol
    dw line
    dw csll
    dw blank
    dw updat
    dw semis

# S  ( n -- )  spread: make line n blank; the lines from n on move down, and
#        line 15 is lost
#   : S  DUP 1 - 14 DO I LINE I 1+ -MOVE -1 +LOOP E ;
align 4
n_e_s:
    db 0x81
    string S
    bytes 0x20 0xA0
    dw n_e_e
e_s:
    dw docol
    dw dup
    dw one
    dw subb
    dw lit
    dw 14
    dw xdo
e_s1:
    dw ido
    dw line
    dw ido
    dw onep
    dw e_move
    dw lit
    dw -1
    dw xploo
    dw %offset(e_s1)
    dw e_e
    dw semis

# D  ( n -- )  delete line n, but hold it at PAD; the lines below move up
#   : D  DUP H 15 DUP ROT DO I 1+ LINE I -MOVE LOOP E ;
align 4
n_e_d:
    db 0x81
    string D
    bytes 0x20 0xA0
    dw n_e_s
e_d:
    dw docol
    dw dup
    dw e_h
    dw lit
    dw 15
    dw dup
    dw rot
    dw xdo
e_d1:
    dw ido
    dw onep
    dw line
    dw ido
    dw e_move
    dw xloop
    dw %offset(e_d1)
    dw e_e
    dw semis

# M  ( n -- )  move the cursor by n and type its line, the cursor shown as _
#   : M  R# +! CR SPACE #LEAD TYPE 95 EMIT
#        #LAG TYPE #LOCATE . DROP ;
align 4
n_e_m:
    db 0x81
    string M
    bytes 0x20 0xA0
    dw n_e_d
e_m:
    dw docol
    dw rnum
    dw pstor
    dw cr
    dw space
    dw e_lead
    dw typee
    dw lit
    dw 95
    dw emit
    dw e_lag
    dw typee
    dw e_locat
    dw dot
    dw drop
    dw semis

# T  ( n -- )  type line n, and hold it at PAD
#   : T  DUP C/L * R# ! DUP H 0 M ;
align 4
n_e_t:
    db 0x81
    string T
    bytes 0x20 0xA0
    dw n_e_m
e_t:
    dw docol
    dw dup
    dw csll
    dw star
    dw rnum
    dw store
    dw dup
    dw e_h
    dw zero
    dw e_m
    dw semis

# L  ( -- )  list the screen again
#   : L  SCR @ LIST 0 M ;
align 4
n_e_l:
    db 0x81
    string L
    bytes 0x20 0xA0
    dw n_e_t
e_l:
    dw docol
    dw scr
    dw at
    dw listt
    dw zero
    dw e_m
    dw semis

# R  ( n -- )  replace line n by the text at PAD
#   : R  PAD 1+ SWAP -MOVE ;
align 4
n_e_r:
    db 0x81
    string R
    bytes 0x20 0xA0
    dw n_e_l
e_r:
    dw docol
    dw pad
    dw onep
    dw swap
    dw e_move
    dw semis

# P  ( n -- )  put the text that follows on line n
#   : P  1 TEXT R ;
align 4
n_e_p:
    db 0x81
    string P
    bytes 0x20 0xA0
    dw n_e_r
e_p:
    dw docol
    dw one
    dw text
    dw e_r
    dw semis

# I  ( n -- )  insert the text at PAD at line n; the lines below move down
#   : I  DUP S R ;
align 4
n_e_i:
    db 0x81
    string I
    bytes 0x20 0xA0
    dw n_e_p
e_i:
    dw docol
    dw dup
    dw e_s
    dw e_r
    dw semis

# TOP  ( -- )  the cursor to the top left of the screen
#   : TOP  0 R# ! ;
align 4
n_e_top:
    db 0x83
    string TO
    db 0xD0                 # P + 0x80
    dw n_e_i
e_top:
    dw docol
    dw zero
    dw rnum
    dw store
    dw semis


# ------------------------------------------------------------------------
# THE EDITOR VOCABULARY: SCREENS
#
# FLUSH takes every buffer once. The model computes how many there are,
# [ LIMIT FIRST - B/BUF 4 + / ] LITERAL, and here that number is NBUF. In
# COPY its 2 - is 4 -, the cell that holds the block number.

# CLEAR  ( n -- )  fill screen n with blanks; it becomes SCR
#   : CLEAR  SCR ! 16 0 DO FORTH I EDITOR E LOOP ;
align 4
n_e_clear:
    db 0x85
    string CLEAR
    bytes 0x20 0xA0
    dw n_e_top
e_clear:
    dw docol
    dw scr
    dw store
    dw lit
    dw 16
    dw zero
    dw xdo
e_clear1:
    dw ido
    dw e_e
    dw xloop
    dw %offset(e_clear1)
    dw semis

# FLUSH  ( -- )  write all changed blocks to the disc
#   : FLUSH  NBUF 0 DO 32767 BUFFER DROP LOOP ;
align 4
n_e_flush:
    db 0x85
    string FLUSH
    bytes 0x20 0xA0
    dw n_e_clear
e_flush:
    dw docol
    dw lit
    dw NBUF
    dw zero
    dw xdo
e_flush1:
    dw lit
    dw 32767
    dw buffe
    dw drop
    dw xloop
    dw %offset(e_flush1)
    dw semis

# COPY  ( n1 n2 -- )  copy screen n1 to screen n2
#   : COPY  B/SCR * OFFSET @ + SWAP B/SCR * B/SCR OVER + SWAP
#           DO DUP FORTH I BLOCK 4 - ! 1+ UPDATE LOOP
#           DROP FLUSH ;
align 4
n_e_copy:
    db 0x84
    string COPY
    bytes 0x20 0x20 0xA0
    dw n_e_flush
e_copy:
    dw docol
    dw bscr
    dw star
    dw ofset
    dw at
    dw plus
    dw swap
    dw bscr
    dw star
    dw bscr
    dw over
    dw plus
    dw swap
    dw xdo
e_copy1:
    dw dup
    dw ido
    dw block
    dw lit
    dw 4
    dw subb
    dw store
    dw onep
    dw updat
    dw xloop
    dw %offset(e_copy1)
    dw drop
    dw e_flush
    dw semis


# ------------------------------------------------------------------------
# THE EDITOR VOCABULARY: TEXT IN A LINE
#
# MATCH is the model's one CODE word here, for the 6502; the manual says it
# may be translated. It looks for the text at addr2 (n2 characters) in the
# n1 characters at addr1. Found: true, and the distance from addr1 to the
# character after the text. Not found: false, and n1, which takes the cursor
# to the next line.

# MATCH  ( addr1 n1 addr2 n2 -- f n3 )
align 4
n_e_match:
    db 0x85
    string MATCH
    bytes 0x20 0xA0
    dw n_e_copy
e_match:
    dw e_match + CELL
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

# 1LINE  ( -- f )  look for the text at PAD from the cursor to the end of its
#        line, and move the cursor
#   : 1LINE  #LAG PAD COUNT MATCH R# +! ;
align 4
n_e_1line:
    db 0x85
    string 1LINE
    bytes 0x20 0xA0
    dw n_e_match
e_1line:
    dw docol
    dw e_lag
    dw pad
    dw count
    dw e_match
    dw rnum
    dw pstor
    dw semis

# FIND  ( -- )  look for the text at PAD from the cursor to the end of the
#        screen; not there: the cursor to the top, and error 0 with the text
#   : FIND  BEGIN 1023 R# @ <
#           IF TOP PAD HERE C/L 1+ CMOVE 0 ERROR ENDIF
#           1LINE UNTIL ;
align 4
n_e_find:
    db 0x84
    string FIND
    bytes 0x20 0x20 0xA0
    dw n_e_1line
e_find:
    dw docol
e_find1:
    dw lit
    dw 1023
    dw rnum
    dw at
    dw less
    dw zbran
    dw %offset(e_find2)
    dw e_top
    dw pad
    dw here
    dw csll
    dw onep
    dw cmove
    dw zero
    dw error
e_find2:
    dw e_1line
    dw zbran
    dw %offset(e_find1)
    dw semis

# DELETE  ( n -- )  delete the n characters before the cursor
#   : DELETE  >R #LAG + FORTH R -
#             #LAG R MINUS R# +!
#             #LEAD + SWAP CMOVE
#             R> BLANKS UPDATE ;
align 4
n_e_delete:
    db 0x86
    string DELETE
    bytes 0xA0
    dw n_e_find
e_delete:
    dw docol
    dw tor
    dw e_lag
    dw plus
    dw rr
    dw subb
    dw e_lag
    dw rr
    dw minus
    dw rnum
    dw pstor
    dw e_lead
    dw plus
    dw swap
    dw cmove
    dw fromr
    dw blank
    dw updat
    dw semis

# N  ( -- )  find the next place the text at PAD occurs
#   : N  FIND 0 M ;
align 4
n_e_n:
    db 0x81
    string N
    bytes 0x20 0xA0
    dw n_e_delete
e_n:
    dw docol
    dw e_find
    dw zero
    dw e_m
    dw semis

# F  ( -- )  find the text that follows
#   : F  1 TEXT N ;
align 4
n_e_f:
    db 0x81
    string F
    bytes 0x20 0xA0
    dw n_e_n
e_f:
    dw docol
    dw one
    dw text
    dw e_n
    dw semis

# B  ( -- )  the cursor back by the length of the text at PAD
#   : B  PAD C@ MINUS M ;
align 4
n_e_b:
    db 0x81
    string B
    bytes 0x20 0xA0
    dw n_e_f
e_b:
    dw docol
    dw pad
    dw cat
    dw minus
    dw e_m
    dw semis

# X  ( -- )  find the text that follows and delete it
#   : X  1 TEXT FIND PAD C@ DELETE 0 M ;
align 4
n_e_x:
    db 0x81
    string X
    bytes 0x20 0xA0
    dw n_e_b
e_x:
    dw docol
    dw one
    dw text
    dw e_find
    dw pad
    dw cat
    dw e_delete
    dw zero
    dw e_m
    dw semis

# TILL  ( -- )  delete from the cursor to the end of the text that follows,
#        which must be on the cursor's line
#   : TILL  #LEAD + 1 TEXT 1LINE 0= 0 ?ERROR
#           #LEAD + SWAP - DELETE 0 M ;
align 4
n_e_till:
    db 0x84
    string TILL
    bytes 0x20 0x20 0xA0
    dw n_e_x
e_till:
    dw docol
    dw e_lead
    dw plus
    dw one
    dw text
    dw e_1line
    dw zequ
    dw zero
    dw qerr
    dw e_lead
    dw plus
    dw swap
    dw subb
    dw e_delete
    dw zero
    dw e_m
    dw semis

# C  ( -- )  put the text that follows in at the cursor; what was after the
#        cursor moves right, and the end of the line is lost
#   : C  1 TEXT PAD COUNT
#        #LAG ROT OVER MIN >R
#        FORTH R R# +!
#        R - >R
#        DUP HERE R CMOVE
#        HERE #LEAD + R> CMOVE
#        R> CMOVE UPDATE
#        0 M ;
align 4
n_e_c:
last_enfa:
    db 0x81
    string C
    bytes 0x20 0xA0
    dw n_e_till
e_c:
    dw docol
    dw one
    dw text
    dw pad
    dw count
    dw e_lag
    dw rot
    dw over
    dw minn
    dw tor
    dw rr
    dw rnum
    dw pstor
    dw rr
    dw subb
    dw tor
    dw dup
    dw here
    dw rr
    dw cmove
    dw here
    dw e_lead
    dw plus
    dw fromr
    dw cmove
    dw fromr
    dw cmove
    dw updat
    dw zero
    dw e_m
    dw semis
