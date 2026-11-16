# fig-FORTH for RISC-V: the nucleus
#
# The CODE words of the fig-FORTH model (fig-FORTH Installation Manual,
# Release 1, screens 12 to 34, 43, 55 and 56) in RISC-V assembly, for the
# bronzebeard assembler. The model is the work of the Forth Interest Group:
#
#                      Through the courtesy of
#
#                       FORTH INTEREST GROUP
#                          P. O. BOX 1105
#                      SAN CARLOS, CA. 94070
#
#                            RELEASE 1
#                      WITH COMPILER SECURITY
#                              AND
#                      VARIABLE LENGTH NAMES
#
#        Further distribution must include the above notice.
#
# Build:  bronzebeard -i . -o figforth.bin figforth.asm
#
# The image must run at address 0: a label is an offset into the image, and
# the threads hold labels as absolute addresses. The CH32V006 maps its flash
# there.
#
# Only x0-x15 are used (RV32E), and no multiply or divide instruction.
# The cell is 32 bits; a double number is two cells, the high cell on top.
# True is 1, as in the model.
#
#
# REGISTERS (the model's names; N and XSAVE are not needed)

W   = a0    # the code field address of the word NEXT has just started
IP  = s1    # interpretive pointer: the next cell of the thread
DSP = s0    # data stack pointer (the model's SP); 0(DSP) is the model's BOT,
            # CELL(DSP) its SEC
RSP = tp    # return stack pointer (the model's RP)
UP  = gp    # user area pointer

# sp is the machine stack: `call` needs none here (the board's routines are
# leaves), but an interrupt will put its frame there.
# Free inside a word: a1-a5, t0-t2 and ra. NEXT uses t0. W is only
# needed by the routines a code field points at, so a word may use a0.
#
# Both stacks grow down and their pointers point at the top item.
#
#
# A WORD IN THE DICTIONARY
#
#   name field       a length byte with bit 7 set (bit 6 = immediate, bit 5 =
#                    smudge), the characters, then blanks up to a cell
#                    boundary; bit 7 is set on the last byte, whether that is
#                    a character or a blank
#   link field       the name field of the word before it, 0 in the first
#   code field       the address of the machine code that runs the word
#   parameter field  machine code (a CODE word), a thread (a colon word), data
#
# The blanks are what this port adds to the model: lw and sw trap on an
# address that is not a multiple of 4 on the CH32V006, so the three fields
# after the name must lie on cell boundaries. (FIND), TRAVERSE and ID. work
# as in the model, because WORD leaves blanks after the text at HERE.
# tools/header.py prints a header; labels: n_x is the name field of the word
# whose code field is x.
#
# A label is looked up by Python: it cannot be a Python keyword (and, or, not,
# if, else, while, in, is ...). The labels here are those of the fig-FORTH
# assembly listings (andd, orr, zequ ...).

CELL = 4

include board.asm

# RAM, from the top down. The dictionary grows up from RAM_BASE.
S0_INIT  = RAM_BASE + RAM_SIZE          # data stack, 64 cells
R0_INIT  = S0_INIT - 64 * CELL          # return stack, 64 cells
MSP_INIT = R0_INIT - 64 * CELL          # machine stack, 24 cells
TIB_INIT = MSP_INIT - 24 * CELL - 96    # terminal input buffer, 96 bytes
UP_INIT  = TIB_INIT - 128               # user area, 32 cells
DP_INIT  = RAM_BASE

# User variables this file needs: offsets into the user area. The model's
# offsets, doubled.
U_S0  = 0x0C
U_R0  = 0x10
U_OUT = 0x34

# Reset comes here from the board file.
boot:
    li sp, MSP_INIT
    call trap_init
    call serial_init
    j cold


# ---------------------------------------------------------------- SCR 12
# COLD AND WARM ENTRY, USER PARAMETERS
#
# n +ORIGIN in the model is origin + 2 * n here.
align 4
origin:
    j cold                      # +0x00  cold start
align 4
    j warm                      # +0x04  warm start
align 4
    dw 0                        # +0x08  CPU
    dw 1                        # +0x0C  revision
boot_up:                        # the cells COLD copies to the user area
    dw last_nfa                 # +0x10  topmost word in the FORTH vocabulary
    dw 0x7F                     # +0x14  backspace character
    dw UP_INIT                  # +0x18  initial user area
    dw S0_INIT                  # +0x1C  initial top of stack (S0)
    dw R0_INIT                  # +0x20  initial top of return stack (R0)
    dw TIB_INIT                 # +0x24  terminal input buffer (TIB)
    dw 31                       # +0x28  initial name field width (WIDTH)
    dw 0                        # +0x2C  initial WARNING: 0, no disc yet
    dw DP_INIT                  # +0x30  initial FENCE
    dw DP_INIT                  # +0x34  cold start value for DP
    dw 0                        # +0x38  cold start value for VOC-LINK


# ---------------------------------------------------------------- SCR 13
# START OF NUCLEUS, LIT, PUSH, PUT, NEXT

# LIT  ( -- n )  push the cell that follows in the thread
align 4
n_lit:
    db 0x83
    string LI
    db 0xD4                 # T + 0x80
    dw 0
lit:
    dw lit + CELL
    lw a1, 0(IP)
    addi IP, IP, CELL
push:                           # push a1, then NEXT
    addi DSP, DSP, -CELL
put:                            # replace the top item with a1, then NEXT
    sw a1, 0(DSP)
next:                           # run the next word of the thread
    lw W, 0(IP)                 # its code field address
    addi IP, IP, CELL
    lw t0, 0(W)                 # the address of its machine code
    jr t0


# ---------------------------------------------------------------- SCR 14

# EXECUTE  ( cfa -- )  run the word whose code field address is on the stack
align 4
n_exec:
    db 0x87
    string EXECUT
    db 0xC5                 # E + 0x80
    dw n_lit
exec:
    dw exec + CELL
    lw W, 0(DSP)
    addi DSP, DSP, CELL
    lw t0, 0(W)
    jr t0


# ---------------------------------------------------------------- SCR 15
# BRANCH, 0BRANCH
#
# The cell after the word holds the distance from that cell to the target,
# which is what bronzebeard's %offset(target) gives.

# BRANCH  ( -- )  add the in-line offset to IP
align 4
n_bran:
    db 0x86
    string BRANCH
    bytes 0xA0
    dw n_exec
bran:
    dw bran + CELL
bran1:
    lw a1, 0(IP)
    add IP, IP, a1
    j next

# 0BRANCH  ( f -- )  branch if f is zero
align 4
n_zbran:
    db 0x87
    string 0BRANC
    db 0xC8                 # H + 0x80
    dw n_bran
zbran:
    dw zbran + CELL
    lw a1, 0(DSP)
    addi DSP, DSP, CELL
    beqz a1, bran1
bump:                           # step IP over the offset, then NEXT
    addi IP, IP, CELL
    j next


# ---------------------------------------------------------------- SCR 16
# LOOP CONTROL
#
# The return stack holds the index on top and the limit under it.

# (LOOP)  ( -- )  add 1 to the index; branch back while index < limit
align 4
n_xloop:
    db 0x86
    string (LOOP)
    bytes 0xA0
    dw n_zbran
xloop:
    dw xloop + CELL
    lw a1, 0(RSP)
    addi a1, a1, 1
xloop1:                         # a1 = the new index
    sw a1, 0(RSP)
    lw a2, CELL(RSP)
    sub a2, a2, a1
    addi a2, a2, -1             # limit - index - 1
xloop2:
    bgez a2, bran1              # not negative: loop again
    addi RSP, RSP, 2*CELL       # done: drop index and limit
    j bump

# (+LOOP)  ( n -- )  add n to the index; branch back while index < limit,
# or while index > limit if n is negative
align 4
n_xploo:
    db 0x87
    string (+LOOP
    db 0xA9                 # ) + 0x80
    dw n_xloop
xploo:
    dw xploo + CELL
    lw a3, 0(DSP)
    addi DSP, DSP, CELL
    lw a1, 0(RSP)
    add a1, a1, a3
    bgez a3, xloop1             # n is not negative: as (LOOP)
    sw a1, 0(RSP)
    lw a2, CELL(RSP)
    sub a2, a1, a2
    addi a2, a2, -1             # index - limit - 1
    j xloop2


# ---------------------------------------------------------------- SCR 17

# (DO)  ( limit index -- )  move both to the return stack
align 4
n_xdo:
    db 0x84
    string (DO)
    bytes 0x20 0x20 0xA0
    dw n_xploo
xdo:
    dw xdo + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    addi RSP, RSP, -2*CELL
    sw a2, CELL(RSP)
    sw a1, 0(RSP)
poptwo:                         # drop two items, then NEXT
    addi DSP, DSP, CELL
pop:                            # drop one item, then NEXT
    addi DSP, DSP, CELL
    j next

# I  ( -- n )  copy the loop index; its code field points at the code of R
align 4
n_ido:
    db 0x81
    string I
    bytes 0x20 0xA0
    dw n_xdo
ido:
    dw rr + CELL


# ---------------------------------------------------------------- SCR 18

# DIGIT  ( c base -- n 1 | 0 )  convert the character c in the given base
align 4
n_digit:
    db 0x85
    string DIGIT
    bytes 0x20 0xA0
    dw n_ido
digit:
    dw digit + CELL
    lw a2, 0(DSP)               # the base
    lw a1, CELL(DSP)            # the character
    addi a1, a1, -48            # less '0'
    bltz a1, digit2
    li a3, 10
    blt a1, a3, digit1
    addi a1, a1, -7             # 'A' becomes 10
    blt a1, a3, digit2          # it was between '9' and 'A'
digit1:
    bgeu a1, a2, digit2         # not below the base
    sw a1, CELL(DSP)            # the digit, second
    li a1, 1                    # true on top
    j put
digit2:
    addi DSP, DSP, CELL
    li a1, 0                    # false alone
    j put


# ---------------------------------------------------------------- SCR 19
# FIND FOR VARIABLE LENGTH NAMES

# (FIND)  ( addr nfa -- pfa b 1 | 0 )  search the dictionary, starting at the
# name field nfa, for the text at addr (a length byte, then the characters,
# then blanks). Found: the parameter field address, the length byte of the
# name field and true. The smudge bit makes a name unequal to any text.
align 4
n_pfind:
    db 0x86
    string (FIND)
    bytes 0xA0
    dw n_digit
pfind:
    dw pfind + CELL
    lw a2, 0(DSP)               # a2 = a name field
    lw a1, CELL(DSP)            # a1 = the text
    addi DSP, DSP, 2*CELL
pfind1:
    lbu a3, 0(a2)
    lbu a4, 0(a1)
    xor a3, a3, a4
    andi a3, a3, 0x3F           # the lengths, and the smudge bit
    mv t1, a2                   # t1 goes along the name field
    mv t2, a1                   # t2 goes along the text
    bnez a3, pfind4
pfind2:
    addi t1, t1, 1
    addi t2, t2, 1
    lbu a3, 0(t1)
    lbu a4, 0(t2)
    xor a4, a4, a3
    andi a5, a4, 0x7F
    bnez a5, pfind3             # the characters differ
    andi a4, a4, 0x80
    beqz a4, pfind2             # equal, and not the last byte of the field
    addi a3, t1, 1 + 2*CELL     # found: over the link and the code field
    lbu a4, 0(a2)
    addi DSP, DSP, -3*CELL
    sw a3, 2*CELL(DSP)          # the parameter field address
    sw a4, CELL(DSP)            # the length byte
    li a1, 1
    j put                       # true
pfind3:
    andi a3, a3, 0x80
    bnez a3, pfind5             # they differ in the last byte of the field
pfind4:                         # go to the last byte of the name field
    addi t1, t1, 1
    lbu a3, 0(t1)
    andi a3, a3, 0x80
    beqz a3, pfind4
pfind5:
    lw a2, 1(t1)                # the link field: the name before this one
    bnez a2, pfind1
    li a1, 0                    # the end of the dictionary: false
    j push


# ---------------------------------------------------------------- SCR 20

# ENCLOSE  ( addr c -- addr n1 n2 n3 )  find the next word of the text at
# addr, c being the delimiter: n1 = offset of its first character, n2 = offset
# of the first delimiter after it, n3 = offset of the first character not yet
# looked at. A null ends the text whatever the delimiter is.
align 4
n_encl:
    db 0x87
    string ENCLOS
    db 0xC5                 # E + 0x80
    dw n_pfind
encl:
    dw encl + CELL
    lw a2, 0(DSP)               # the delimiter
    lw a1, CELL(DSP)            # the text
    addi DSP, DSP, -2*CELL      # n1 goes to 2*CELL(DSP), n2 to CELL, n3 to 0
    li a3, -1                   # a3 = the offset
encl1:                          # step over leading delimiters
    addi a3, a3, 1
    add a4, a1, a3
    lbu a4, 0(a4)
    beq a4, a2, encl1
    sw a3, 2*CELL(DSP)          # n1
encl2:
    add a4, a1, a3
    lbu a4, 0(a4)
    bnez a4, encl4
    sw a3, 0(DSP)               # a null: n3 = its offset
    lw a5, 2*CELL(DSP)
    bne a3, a5, encl3
    addi a3, a3, 1              # the null is the word itself, one character
encl3:
    sw a3, CELL(DSP)            # n2
    j next
encl4:
    mv a5, a3                   # the offset of this character
    addi a3, a3, 1
    bne a4, a2, encl2           # not the delimiter: on to the next one
    sw a5, CELL(DSP)            # n2 = the offset of the delimiter
    sw a3, 0(DSP)               # n3 = the offset after it
    j next


# ---------------------------------------------------------------- SCR 21
# TERMINAL VECTORS
#
# The four installation dependent words. The serial routines are in the
# board file.

# EMIT  ( c -- )  send the character, seven bits of it, and count it in OUT
align 4
n_emit:
    db 0x84
    string EMIT
    bytes 0x20 0x20 0xA0
    dw n_encl
emit:
    dw emit + CELL
    lw a0, 0(DSP)
    andi a0, a0, 0x7F           # ID. sends the last byte of a name, bit 7 set
    call serial_putc
    lw a1, U_OUT(UP)
    addi a1, a1, 1
    sw a1, U_OUT(UP)
    j pop

# KEY  ( -- c )  wait for a character
align 4
n_key:
    db 0x83
    string KE
    db 0xD9                 # Y + 0x80
    dw n_emit
key:
    dw key + CELL
    call serial_getc
    andi a1, a0, 0x7F
    j push

# ?TERMINAL  ( -- f )  true if a key was pressed; the character is taken
align 4
n_qterm:
    db 0x89
    string ?TERMINAL
    bytes 0x20 0xA0
    dw n_key
qterm:
    dw qterm + CELL
    call serial_poll
    mv a1, a0
    j push

# CR  ( -- )  carriage return and line feed
align 4
n_cr:
    db 0x82
    string CR
    bytes 0xA0
    dw n_qterm
cr:
    dw cr + CELL
    li a0, 13
    call serial_putc
    li a0, 10
    call serial_putc
    j next


# ---------------------------------------------------------------- SCR 22

# CMOVE  ( from to count -- )  copy count bytes, lowest address first
align 4
n_cmove:
    db 0x85
    string CMOVE
    bytes 0x20 0xA0
    dw n_cr
cmove:
    dw cmove + CELL
    lw a3, 0(DSP)
    lw a2, CELL(DSP)
    lw a1, 2*CELL(DSP)
    addi DSP, DSP, 3*CELL
cmove1:
    beqz a3, next
    lbu a4, 0(a1)
    sb a4, 0(a2)
    addi a1, a1, 1
    addi a2, a2, 1
    addi a3, a3, -1
    j cmove1


# ---------------------------------------------------------------- SCR 23

# U*  ( u1 u2 -- ud )  unsigned product, a double number
# The model's loop, 32 times: double the product, then add the multiplicand
# if the bit shifted out of the multiplier was set.
align 4
n_ustar:
    db 0x82
    string U*
    bytes 0xA0
    dw n_cmove
ustar:
    dw ustar + CELL
    lw a1, 0(DSP)               # the multiplier
    lw a2, CELL(DSP)            # the multiplicand
    li a3, 0                    # the product, low cell
    li a4, 0                    # the product, high cell
    li a5, 32
ustar1:
    srli t1, a3, 31
    slli a4, a4, 1
    or a4, a4, t1
    slli a3, a3, 1
    bgez a1, ustar2             # the top bit of the multiplier is clear
    add a3, a3, a2
    sltu t1, a3, a2             # the carry
    add a4, a4, t1
ustar2:
    slli a1, a1, 1
    addi a5, a5, -1
    bnez a5, ustar1
    sw a3, CELL(DSP)
    sw a4, 0(DSP)
    j next


# ---------------------------------------------------------------- SCR 24

# U/  ( ud u -- remainder quotient )  unsigned divide of a double number
# Shift and subtract, 32 times. Unlike the model's, the divisor may use all
# its bits. The result is only right if the quotient fits in a cell; dividing
# by zero gives a quotient of all ones.
align 4
n_uslas:
    db 0x82
    string U/
    bytes 0xA0
    dw n_ustar
uslas:
    dw uslas + CELL
    lw a1, 0(DSP)               # the divisor
    lw a3, CELL(DSP)            # the dividend, high cell: becomes the remainder
    lw a2, 2*CELL(DSP)          # the dividend, low cell: becomes the quotient
    addi DSP, DSP, CELL
    li a5, 32
uslas1:
    srli t1, a3, 31             # the bit shifted out of the remainder
    slli a3, a3, 1
    srli t2, a2, 31
    or a3, a3, t2
    slli a2, a2, 1
    bnez t1, uslas2             # 33 bits: more than any divisor
    bltu a3, a1, uslas3
uslas2:
    sub a3, a3, a1
    addi a2, a2, 1              # a quotient bit
uslas3:
    addi a5, a5, -1
    bnez a5, uslas1
    sw a3, CELL(DSP)
    sw a2, 0(DSP)
    j next


# ---------------------------------------------------------------- SCR 25
# LOGICALS

# AND  ( n1 n2 -- n3 )
align 4
n_andd:
    db 0x83
    string AN
    db 0xC4                 # D + 0x80
    dw n_uslas
andd:
    dw andd + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    addi DSP, DSP, CELL
    and a1, a1, a2
    j put

# OR  ( n1 n2 -- n3 )
align 4
n_orr:
    db 0x82
    string OR
    bytes 0xA0
    dw n_andd
orr:
    dw orr + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    addi DSP, DSP, CELL
    or a1, a1, a2
    j put

# XOR  ( n1 n2 -- n3 )
align 4
n_xorr:
    db 0x83
    string XO
    db 0xD2                 # R + 0x80
    dw n_orr
xorr:
    dw xorr + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    addi DSP, DSP, CELL
    xor a1, a1, a2
    j put


# ---------------------------------------------------------------- SCR 26
# STACK INITIALIZATION

# SP@  ( -- addr )  the address of the top item, as it was before the push
align 4
n_spat:
    db 0x83
    string SP
    db 0xC0                 # @ + 0x80
    dw n_xorr
spat:
    dw spat + CELL
    mv a1, DSP
    j push

# SP!  ( -- )  empty the data stack: load its pointer from S0
align 4
n_spsto:
    db 0x83
    string SP
    db 0xA1                 # ! + 0x80
    dw n_spat
spsto:
    dw spsto + CELL
    lw DSP, U_S0(UP)
    j next

# RP!  ( -- )  empty the return stack: load its pointer from R0
align 4
n_rpsto:
    db 0x83
    string RP
    db 0xA1                 # ! + 0x80
    dw n_spsto
rpsto:
    dw rpsto + CELL
rpsto1:
    lw RSP, U_R0(UP)
    j next

# ;S  ( -- )  leave a colon definition: take IP back from the return stack
align 4
n_semis:
    db 0x82
    string ;S
    bytes 0xA0
    dw n_rpsto
semis:
    dw semis + CELL
    lw IP, 0(RSP)
    addi RSP, RSP, CELL
    j next


# ---------------------------------------------------------------- SCR 27
# RETURN STACK WORDS

# LEAVE  ( -- )  make the loop end at its next LOOP: limit = index
align 4
n_leave:
    db 0x85
    string LEAVE
    bytes 0x20 0xA0
    dw n_semis
leave:
    dw leave + CELL
    lw a1, 0(RSP)
    sw a1, CELL(RSP)
    j next

# >R  ( n -- )  move the top item to the return stack
align 4
n_tor:
    db 0x82
    string >R
    bytes 0xA0
    dw n_leave
tor:
    dw tor + CELL
    lw a1, 0(DSP)
    addi DSP, DSP, CELL
    addi RSP, RSP, -CELL
    sw a1, 0(RSP)
    j next

# R>  ( -- n )  move the top of the return stack to the data stack
align 4
n_fromr:
    db 0x82
    string R>
    bytes 0xA0
    dw n_tor
fromr:
    dw fromr + CELL
    lw a1, 0(RSP)
    addi RSP, RSP, CELL
    j push

# R  ( -- n )  copy the top of the return stack
align 4
n_rr:
    db 0x81
    string R
    bytes 0x20 0xA0
    dw n_fromr
rr:
    dw rr + CELL
    lw a1, 0(RSP)
    j push


# ---------------------------------------------------------------- SCR 28
# TESTS AND LOGICALS

# 0=  ( n -- f )  true if n is zero
align 4
n_zequ:
    db 0x82
    string 0=
    bytes 0xA0
    dw n_rr
zequ:
    dw zequ + CELL
    lw a1, 0(DSP)
    seqz a1, a1
    j put

# 0<  ( n -- f )  true if n is negative
align 4
n_zless:
    db 0x82
    string 0<
    bytes 0xA0
    dw n_zequ
zless:
    dw zless + CELL
    lw a1, 0(DSP)
    srli a1, a1, 31
    j put


# ---------------------------------------------------------------- SCR 29
# MATH

# +  ( n1 n2 -- sum )
align 4
n_plus:
    db 0x81
    string +
    bytes 0x20 0xA0
    dw n_zless
plus:
    dw plus + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    addi DSP, DSP, CELL
    add a1, a1, a2
    j put

# D+  ( d1 d2 -- dsum )  add two double numbers
align 4
n_dplus:
    db 0x82
    string D+
    bytes 0xA0
    dw n_plus
dplus:
    dw dplus + CELL
    lw a1, CELL(DSP)            # d2, low cell
    lw a2, 3*CELL(DSP)          # d1, low cell
    add a2, a2, a1
    sltu a1, a2, a1             # the carry
    sw a2, 3*CELL(DSP)
    lw a2, 0(DSP)               # d2, high cell
    lw a3, 2*CELL(DSP)          # d1, high cell
    add a2, a2, a3
    add a2, a2, a1
    sw a2, 2*CELL(DSP)
    j poptwo

# MINUS  ( n -- -n )  two's complement
align 4
n_minus:
    db 0x85
    string MINUS
    bytes 0x20 0xA0
    dw n_dplus
minus:
    dw minus + CELL
    lw a1, 0(DSP)
    neg a1, a1
    j put

# DMINUS  ( d -- -d )  two's complement of a double number
align 4
n_dminu:
    db 0x86
    string DMINUS
    bytes 0xA0
    dw n_minus
dminu:
    dw dminu + CELL
    lw a1, CELL(DSP)            # the low cell
    lw a2, 0(DSP)               # the high cell
    neg a1, a1
    snez a3, a1                 # the borrow
    neg a2, a2
    sub a2, a2, a3
    sw a1, CELL(DSP)
    sw a2, 0(DSP)
    j next


# ---------------------------------------------------------------- SCR 30
# STACK MANIPULATION

# OVER  ( n1 n2 -- n1 n2 n1 )
align 4
n_over:
    db 0x84
    string OVER
    bytes 0x20 0x20 0xA0
    dw n_dminu
over:
    dw over + CELL
    lw a1, CELL(DSP)
    j push

# DROP  ( n -- )  its code field points straight at POP
align 4
n_drop:
    db 0x84
    string DROP
    bytes 0x20 0x20 0xA0
    dw n_over
drop:
    dw pop

# SWAP  ( n1 n2 -- n2 n1 )
align 4
n_swap:
    db 0x84
    string SWAP
    bytes 0x20 0x20 0xA0
    dw n_drop
swap:
    dw swap + CELL
    lw a2, 0(DSP)
    lw a1, CELL(DSP)
    sw a2, CELL(DSP)
    j put

# DUP  ( n -- n n )
align 4
n_dup:
    db 0x83
    string DU
    db 0xD0                 # P + 0x80
    dw n_swap
dup:
    dw dup + CELL
    lw a1, 0(DSP)
    j push


# ---------------------------------------------------------------- SCR 31
# MEMORY INCREMENT

# +!  ( n addr -- )  add n to the cell at addr
align 4
n_pstor:
    db 0x82
    string +!
    bytes 0xA0
    dw n_dup
pstor:
    dw pstor + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    lw a3, 0(a1)
    add a3, a3, a2
    sw a3, 0(a1)
    j poptwo

# TOGGLE  ( addr b -- )  exclusive-or the byte at addr with the pattern b
align 4
n_toggl:
    db 0x86
    string TOGGLE
    bytes 0xA0
    dw n_pstor
toggl:
    dw toggl + CELL
    lw a2, 0(DSP)
    lw a1, CELL(DSP)
    lbu a3, 0(a1)
    xor a3, a3, a2
    sb a3, 0(a1)
    j poptwo


# ---------------------------------------------------------------- SCR 32
# MEMORY FETCH AND STORE
#
# @ ! and +! want an address that is a multiple of 4. Any other traps on the
# CH32V006.

# @  ( addr -- n )
align 4
n_at:
    db 0x81
    string @
    bytes 0x20 0xA0
    dw n_toggl
at:
    dw at + CELL
    lw a1, 0(DSP)
    lw a1, 0(a1)
    j put

# C@  ( addr -- b )
align 4
n_cat:
    db 0x82
    string C@
    bytes 0xA0
    dw n_at
cat:
    dw cat + CELL
    lw a1, 0(DSP)
    lbu a1, 0(a1)
    j put

# !  ( n addr -- )
align 4
n_store:
    db 0x81
    string !
    bytes 0x20 0xA0
    dw n_cat
store:
    dw store + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    sw a2, 0(a1)
    j poptwo

# C!  ( b addr -- )
align 4
n_cstor:
    db 0x82
    string C!
    bytes 0xA0
    dw n_store
cstor:
    dw cstor + CELL
    lw a1, 0(DSP)
    lw a2, CELL(DSP)
    sb a2, 0(a1)
    j poptwo


# ---------------------------------------------------------------- SCR 56

# S->D  ( n -- d )  extend a number to a double number
align 4
n_stod:
last_nfa:
    db 0x84
    string S->D
    bytes 0x20 0x20 0xA0
    dw n_cstor
stod:
    dw stod + CELL
    lw a1, 0(DSP)
    srai a1, a1, 31
    j push


# ------------------------------------------------- SCR 33, 34 and 43
# THE CODE AFTER ;CODE
#
# What the code field of a word made by a defining word points at. Each of
# these gets W = the code field address from NEXT; the parameter field is at
# CELL(W). In the model they stand after the ;CODE of : CONSTANT VARIABLE
# USER and DOES> and they have no names.

align 4
docol:                          # a colon definition: nest into its thread
    addi RSP, RSP, -CELL
    sw IP, 0(RSP)
    addi IP, W, CELL
    j next

docon:                          # a CONSTANT: push its parameter
    lw a1, CELL(W)
    j push

dovar:                          # a VARIABLE: push the address of its parameter
    addi a1, W, CELL
    j push

douse:                          # a USER variable: its parameter is an offset
    lw a1, CELL(W)              # into the user area
    add a1, a1, UP
    j push

dodoe:                          # a word made by <BUILDS ... DOES>: its first
    addi RSP, RSP, -CELL        # parameter is the address of the thread after
    sw IP, 0(RSP)               # DOES>. Nest into that, and push the address
    lw IP, CELL(W)              # of the parameters behind it.
    addi a1, W, 2*CELL
    j push


# ---------------------------------------------------------------- SCR 55
# COLD START
#
# The code of COLD. Its header comes with the high-level words; the model also
# sets the head of the FORTH vocabulary here, from the first cell of boot_up.

cold:                           # all eleven cells of boot_up, VOC-LINK included
    li a3, 11*CELL
    j cold1
warm:                           # eight, up to WARNING: FENCE, DP and VOC-LINK
    li a3, 8*CELL               # stay
cold1:
    li a1, boot_up
    lw UP, 2*CELL(a1)           # the initial user area
    mv a2, UP
cold2:
    lw a4, 0(a1)
    sw a4, 0(a2)
    addi a1, a1, CELL
    addi a2, a2, CELL
    addi a3, a3, -CELL
    bnez a3, cold2
    li IP, abort + CELL         # ABORT is the first word to run,
    j rpsto1                    # after RP!


# ------------------------------------------------------------------------
# THE HIGH-LEVEL WORDS
#
# The colon definitions of the model are in listings.asm. ABORT is there.

include listings.asm
