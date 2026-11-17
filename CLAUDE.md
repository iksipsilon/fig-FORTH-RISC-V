                     Notes for Claude: fig-FORTH for RISC-V

            what was decided, what was measured, and what is planned


  This file is for Claude. As CLAUDE.md at the root of the repo it is
  read at the start of every session; keep it up to date when one of
  the decisions below changes. MANUAL.txt (docs/) is for the
  reader of the system; this one keeps the reasons, the rejected
  options, and the plans that are not done yet. Written 2026-11-17.

  CONTENTS

     1  How the user wants to work
     2  The assembler in Forth: what is there and why
     3  Getting it onto the board, and the traps found doing it
     4  Facts measured on the board
     5  Decided against: autostart, the assembler in the kernel
     6  PLANNED: CSR and system instructions (do it with the interrupts)
     7  Interrupts: what is known, what is open
     8  Timing of high-level Forth
     9  Small things left over
    10  Small letters (UPPER in -FIND)


 ------------------------------------------------------------------------
  1  HOW THE USER WANTS TO WORK
 ------------------------------------------------------------------------

  - Stay true to the fig-FORTH model (Installation Manual, Release 1):
    write each word as the model has it, deviate only where the chip
    forces it, and say so in the comment above the word. When unsure
    between fidelity and convenience, pick fidelity and mention it.

  - Ask before doing anything that changes the repo or the board, when
    the user has asked a question rather than given an order. They
    said so explicitly ("ask me before you do anything") when the
    board and the disc were involved. Before writing to the disc,
    look at what is there first.

  - The user commits and pushes themselves. Do not commit unless asked.

  - The user does not read Python. Explain tools by what they do and
    by the Forth or assembly they produce, not by their Python.

  - The working style is that of 1979: the chip is the computer,
    picocom is its terminal, source lives on screens.


 ------------------------------------------------------------------------
  2  THE ASSEMBLER IN FORTH: WHAT IS THERE AND WHY
 ------------------------------------------------------------------------

  tools/forth-assembler.f, four screens, 64 lines. MANUAL.txt section 16
  describes it for the reader. It loads to 2980 bytes of dictionary.

  The model's own listing (screens 12-32 of the PDF) is written in a
  6502 Forth assembler: operands first, mnemonics end in a comma,
  NEXT JMP, PUSH JMP, PUT JMP, IF, THEN, BEGIN, UNTIL, END, . The
  glossary describes ;CODE as setting CONTEXT to ASSEMBLER. The
  glossary has NO entries for CODE, END-CODE, C; or ASSEMBLER.

  Design decisions, and why:

  - Operand order is that of the assembly text: rd rs1 rs2 ADD, ,
    rd imm rs1 LW, (as lw rd, imm(rs1)), rs2 imm rs1 SW, , rs1 rs2
    addr BEQ, , rd addr JAL, . Branches take an absolute address and
    compute the distance from HERE.

  - fig-FORTH has no shift words, so fields are placed by multiplying
    by powers of two (RD = 80 *, RS1 = 8000 *, RS2 = 100000 *).
    BOFF and JOFF scatter branch/jump offsets: mask each bit group with
    AND first, then * or / ; the values are then never negative, so the
    signed / is safe. * is U* DROP, so overflow into bit 31 is fine.

  - Each instruction is a template (opcode+funct3+funct7) made by one of
    six defining words RTYPE ITYPE LTYPE STYPE BTYPE UTYPE, each
    <BUILDS , DOES> @ X, .

  - Registers are constants: ZERO RA SP GP TP T0 T1 T2 DSP IP A0-A5,
    plus W RSP UP. No S0/S1 constants: S0 is the fig user variable.

  - Conditions EQ NE LT GE LTU GEU are the INVERSE branch (EQ = BNE),
    the branch that skips the IF, part. IF, puts down the branch with
    offset 0 and leaves its address; THEN, ORs the offset in (BOFF).
    ELSE, is ZERO ZERO NE IF, (= BEQ zero,zero, always taken).

  - NEXT, PUSH, PUT, put NEXT's four instructions in place instead of
    jumping to next (the model's NEXT JMP,): the address of next is
    only in figforth.labels, not known to Forth. Costs 16 bytes a word.
    If the kernel ever publishes the address of next (e.g. in the
    +ORIGIN table), NEXT could become a constant and NEXT J, would be
    the model's way. Not done: it changes the kernel.

  - CODE  ?EXEC CREATE [COMPILE] ASSEMBLER !CSP ; IMMEDIATE
    END-CODE  CURRENT @ CONTEXT ! ?EXEC ?CSP SMUDGE ;
    These two are our design (not in the model's glossary). CREATE
    leaves the word smudged; END-CODE unsmudges it.

  - The assembler REDEFINES ;CODE as the kernel's with [COMPILE]
    ASSEMBLER in the place of SMUDGE, so it follows the glossary, and
    END-CODE ends both. Loading therefore prints ;CODE ISN'T UNIQUE
    (with WARNING 0: ;CODE MSG # 4, two blanks after the 4): intended.

  - Not there: compressed instructions, LI, , and (yet) the system
    instructions: see section 6.

  Testing (tests/test_listings.py, section "the assembler in Forth",
  between "the editor" and "cold and warm" so that board_test.py, which
  cuts out "the disc" .. "cold and warm", does not type it at the
  board): file shape (64 lines, <= 63 chars, --> ends screens 1-3),
  42 LOAD from the emulated disc, 41 instructions compared with
  bronzebeard bit for bit (CASES list; a temporary .asm with labels
  L0..Ln), and the manual's examples. make test: 413 + 294 checks
  (nucleus + listings), all passing since UPPER (section 10).


 ------------------------------------------------------------------------
  3  GETTING IT ONTO THE BOARD, AND THE TRAPS FOUND DOING IT
 ------------------------------------------------------------------------

  Where: screens 42 to 45, the last four of the disc (0-45). Chosen by
  the user. 4 and 5 hold the error messages (written 2026-11-17 with
  put_screens.py; WARNING starts at 1, the model's value), 40 and 41
  are overwritten by make test-board, 0 cannot be loaded.

  How: make put-assembler = tools/put_screens.py FILE 42 [port]
  [--force]. It types EDITOR, n CLEAR, n P line ..., FLUSH, FORTH at
  one key per 3 ms, then LISTs each screen and compares. Before that it
  defines ?USED (counts bytes that are neither blank nor FF in a
  screen), refuses if any target screen is in use, then FORGETs ?USED.
  No COLD: words typed at the terminal survive. It took 36 s.
  The screens on the board NOW HOLD THE CURRENT FILE. After changing
  the file, rewriting needs --force (they are no longer empty).

  Traps:

  - A screen line is 64 characters with nothing ending it. A 64-char
    line runs into the next: the first LOAD failed with ;:? (a ; in
    column 63 and a : at the start of the next line). Every line of a
    file meant for screens must be 63 characters at most.

  - In HEX, the register constants A0-A5 hide the numbers A0-A5 hex
    (the dictionary is searched before NUMBER). Write 0A0 for the
    number. This broke two of my own test cases at first. Since UPPER
    (section 10) the same holds for a0-a5 in small letters.

  - A line typed while compiling (inside : ... ) answers only CR LF,
    no OK. A test that waits for OK must allow that.

  - 42 LOAD takes longer than 0.3 s before it answers. read_quiet with
    0.25-0.3 s quiet time (board_test.py) gives up too early and all
    later answers look shifted by one line. Use about 1 s for LOAD.

  - The chip has no input buffer: a key that arrives while a line is
    being compiled, or during a flash write, is lost. Never paste;
    type one key at a time and wait for the answer of each line.

  - CODE SIGN would hide fig's SIGN (number formatting): pick test
    names that are not fig words (SGN, ABS' ...).


 ------------------------------------------------------------------------
  4  FACTS MEASURED ON THE BOARD
 ------------------------------------------------------------------------

  - THE CH32V006 RUNS CODE FROM SRAM. Proven 2026-11-17: after a reset
    and 42 LOAD, CODE TWO A1 ZERO 2 ADDI, A1 PUSH, END-CODE had its code
    field at 20000BC8 hex and TWO . answered 2. All the manual's
    examples gave the same answers as in the emulator (2* 42, SGN -1 1,
    SUMTO 55, BITS 8 32 0, CON 1234, IF, without THEN, = error 20,
    FORGET ASSEMBLER cleans up).

  - The kernel's CODE words run from flash (bronzebeard, figforth.bin
    at address 0). Before the assembler, no code had run from RAM.

  - The emulator (tests/rv32emu.py) fetches instructions from any
    readable address, so it proves nothing about the chip's limits.

  - The trap handler (board.asm, trap:) prints T, mcause and mepc in
    hex and hangs. A reset (minichlink -b) brings the board back; the
    disc is untouched by a trap.

  - The board run of the examples was a one-off script, not kept. To
    repeat it: minichlink -b, read the banner, type 42 LOAD (wait ~1 s),
    then the example lines from MANUAL.txt section 16.

  - Sizes: image 13100 bytes (13028 before UPPER), must stay below
    16384 (the disc starts at 4000 hex), so about 3.2 KiB of kernel
    space is left. RAM 8 KiB.
    HERE after a cold start + 42 LOAD: 20000BBC hex.


 ------------------------------------------------------------------------
  5  DECIDED AGAINST: AUTOSTART, THE ASSEMBLER IN THE KERNEL
 ------------------------------------------------------------------------

  Nothing loads at startup. cold (figforth.asm) copies the vocabulary
  bodies and boot_up, then EMPTY-BUFFERS FIRST USE ! FIRST PREV ! and
  ABORT -> QUIT. That is the model's COLD. Screen 0 cannot be loaded
  (block 0 = the terminal); a "load screen" on 1 is only a habit.

  The user asked whether the assembler should autostart. Advised NO:
  - it would change the model's COLD, which the chip does not force;
  - a damaged screen or a crashing word would hit every reset, with no
    way out but a skip key or reflashing;
  - every boot would lose 2.9 KiB of the 8 KiB RAM;
  - make test-board does COLD before every test, and the check
    "COLD puts the dictionary pointer back" would fail.
  The editor's trick of moving the cold-start values past loaded words
  (MANUAL section 12) does not work here: those values are in flash,
  and the RAM dictionary is gone at power-off.
  If the user ever wants it anyway: ask how it should behave (e.g. skip
  the load when a key is held) before touching COLD.

  The assembler in the kernel, like the editor: possible but advised
  against for now. It would save its 2.9 KiB of RAM, but take nearly
  all of the ~3.2 KiB of kernel space left, and needs a third
  vocabulary body (the same work MANUAL section 12 lists for SF:
  figforth.asm voc body, voc_up, COLD copies more cells, VOC-LINK;
  listing.py must learn a third vocabulary).

  The kernel's own CODE words cannot be moved to the Forth assembler:
  a Forth assembler needs a running Forth. bronzebeard stays.


 ------------------------------------------------------------------------
  6  PLANNED: CSR AND SYSTEM INSTRUCTIONS (DO IT WITH THE INTERRUPTS)
 ------------------------------------------------------------------------

  The user said: do this when we get to the interrupts. Not done yet.

  Screens 3 and 4 have all 16 lines in use. Three merges free three
  lines (lengths measured):

  - screen 3: move LUI, and AUIPC, onto the AND, JALR, line, and drop
    the comment "( A CONDITION: THE SKIPPING B )" (the manual explains
    it). New line, 63 chars:
      7033 RTYPE AND,  67 ITYPE JALR,  37 UTYPE LUI,  17 UTYPE AUIPC,
  - screen 4: MV, J, JR, on one line, without stack comments, single
    blanks, 63 chars:
      : MV, 0 ADDI, ; : J, ZERO SWAP JAL, ; : JR, ZERO SWAP 0 JALR, ;
  - screen 4: FORTH DEFINITIONS joins the PUT, line, 58 chars:
      : PUT,   ( REG -- )  0 DSP SW,  NEXT, ;  FORTH DEFINITIONS

  The freed lines take (55, 58 and 58 chars):

      1073 ITYPE CSRRW,  2073 ITYPE CSRRS,  3073 ITYPE CSRRC,
      5073 ITYPE CSRRWI,  6073 ITYPE CSRRSI,  7073 ITYPE CSRRCI,
      : MRET, 30200073 , ;  : ECALL, 73 , ;  : WFI, 10500073 , ;

  The CSRRx line goes on screen 3 (freed line 12); the other two on
  screen 4, before FORTH DEFINITIONS; retitle screen 4
  "( RISC-V ASSEMBLER 4 OF 4: SYSTEM, STRUCTURES, NEXT, CODE )".
  Check again that the screen ends stay where they must: --> on line
  15 of screens 1-3, END-CODE ... DECIMAL last.

  Notes:
  - CSR instructions are I-type with the CSR number in the immediate,
    so ITYPE makes them: operands rd rs1 csr, the order of bronzebeard
    and figforth.asm (csrrw zero, t0, CSR_MTVEC). The RISC-V manual
    writes csrrw rd, csr, rs1: say so in the manual. For the I forms the
    5-bit value takes the place of rs1.
  - CSR numbers above 7FF need no trick: IMM masks to 12 bits. (In
    bronzebeard they must be written as the number minus 1000 hex.)
  - EBREAK, and FENCE, left out: no cache to fence, the debugger does
    not need EBREAK in code. About 200 bytes more dictionary.
  - Example for the manual, in HEX:
      CODE MCAUSE@  A1 ZERO 342 CSRRS,  A1 PUSH,  END-CODE

  Rejected alternative: a fifth screen (41-45). Keeps the spacing, but
  collides with make test-board (40, 41), which would have to move
  (e.g. to 38, 39). I recommended four screens; the user has not
  chosen yet: ask.

  Steps when doing it (ask the user first):
  1. edit screens 3 and 4 of tools/forth-assembler.f, 63 chars max;
  2. add the nine to CASES in tests/test_listings.py (bronzebeard
     syntax: csrrs a1, zero, CSR, with CSR > 7FF written minus 1000),
     and a test that CSRRS, reads a CSR in the emulator;
  3. MANUAL.txt section 16: the list of instructions, the operand order
     of the CSR words, the example; remove "(yet)"-style remarks;
  4. make test;
  5. on the board: make put-assembler needs --force now (the screens
     hold the old version); then reset, 42 LOAD, try the example.


 ------------------------------------------------------------------------
  7  INTERRUPTS: WHAT IS KNOWN, WHAT IS OPEN
 ------------------------------------------------------------------------

  Known:
  - None is enabled. trap_init (board.asm) clears MIE and sets mtvec =
    3: table at 0, vectored, absolute addresses. The vector table in
    board.asm has the reset and trap entries only, IN FLASH.
  - figforth.asm: sp (the machine stack) is left for interrupt frames.
  - The emulator models SysTick at E000F000 with its interrupt (12), the
    HPE (hardware prologue/epilogue, a 48-byte frame on sp) and faults
    if sp is outside the machine stack. Its SysTick counts one cycle per
    instruction: that is a model, not the chip's timing.

  Open, to plan with the user:
  - Handlers written with the Forth assembler live in RAM, but the
    vector table is in flash. Options to put before the user: a flash
    vector that jumps through a cell in RAM (a kernel change), or
    pointing mtvec at a table in RAM (check the QingKe V2C / CH32V006
    reference manual for the alignment and mode rules first).
  - A handler that runs Forth must save what NEXT uses (IP, W, DSP, t0,
    a1-a5 ...) or run on its own stacks; one in pure CODE need not.
  - The assembler needs the CSR words and MRET, first: section 6.


 ------------------------------------------------------------------------
  8  TIMING OF HIGH-LEVEL FORTH
 ------------------------------------------------------------------------

  I first said high-level Forth "can't promise the timing between two
  !s". The user rightly objected: on this board (no cache, no
  interrupts, one task) a thread runs the same instructions every time,
  so its time is fixed and can be counted. The better statement: the
  timing is fixed, but coarse and laborious to work out; fine timing
  below a few dozen instructions needs CODE.

  Counted from figforth.asm, 1 PORT ! (PORT a CONSTANT):
      LIT    lw, addi IP, addi DSP, sw + NEXT(4)        8 instructions
      PORT   docon: lw, j push, addi DSP, sw + NEXT(4)  8
      !      lw, lw, sw, j poptwo, addi DSP + NEXT(4)   about 10
  so about 26 instructions from one store to the next, the minimum.

  Why CODE is still needed for fine timing:
  - the step is a whole word (8+ instructions); CODE can put two sw
    back to back and pad by single instructions;
  - instructions are not cycles: taken jumps (every NEXT ends in jr),
    loads and flash wait states cost extra; fixed, but to be measured;
  - data-dependent words: 0BRANCH, (LOOP), U*, U/, * (software
    multiply: the chip has no M extension used), CMOVE;
  - KEY, EMIT (wait on the UART), BLOCK-WRITE (stalls for ms), and
    interrupts once enabled.

  Offered, not done: measure 1 PORT ! in real cycles on the board with
  the SysTick counter (read it with @ before and after). Ask first.

  When the assembler is worth loading (told to the user): speed in an
  inner loop; exact timing (bit-banged protocols, LED strips, pulses);
  instructions Forth lacks (shifts, rotates); defining words with fast
  ;CODE parts (tables, ports, a PIN word); trying a CODE word before it
  goes into figforth.asm; learning the chip. NOT needed for ordinary
  memory-mapped I/O: @ ! C@ C! on the register address are enough.


 ------------------------------------------------------------------------
  9  SMALL THINGS LEFT OVER
 ------------------------------------------------------------------------

  - tools/words.py line 159, the comment on ;CODE: "There is no
    assembler vocabulary yet: the code is put in with , by hand." Still
    true of the kernel; could point to MANUAL section 16. Changing it
    means make listing (listings.asm changes in a comment only; the
    image does not). Not done; mention it if touching words.py.

  - make test-board does not test the assembler. If it should: LOAD
    screens 42-45 (already on the board, do not rewrite them) and run
    the examples; give LOAD about 1 s.

  - This file was docs/CLAUDE.txt first; the user had it moved here as
    CLAUDE.md so that it is read automatically.


 ------------------------------------------------------------------------
  10  SMALL LETTERS (UPPER IN -FIND)
 ------------------------------------------------------------------------

  Done 2026-11-17, at the user's request: they did not want to keep
  switching caps lock. It is the one deviation the chip does not force;
  the user chose it knowing that (I asked first, and gave the cost).

  - UPPER ( addr -- ), a CODE word in figforth.asm right after (FIND)
    (ENCLOSE now links to it): small letters a-z of a counted text to
    capitals. -FIND is  BL WORD HERE UPPER HERE CONTEXT @ @ (FIND) ...
    tools/listing.py's LAB table knows UPPER.
  - Why -FIND and not KEY/EXPECT/WORD: every name goes through -FIND
    (INTERPRET, CREATE and so : CONSTANT VARIABLE VOCABULARY, ' ,
    [COMPILE], FORGET), and NUMBER reads the same word at HERE, so hex
    digits work too. ." and the editor's P F etc. read with WORD and
    keep small letters. Folding at KEY was rejected: it would make
    small letters impossible to type at all.
  - Consequences: names are stored in capitals (: sq ... shows SQ in
    VLIST); an error echoes the word in capitals (foo gives FOO? ...).
  - Cost: 72 bytes of flash (64 for UPPER, 8 in -FIND). Speed counted
    from the source, not measured: about 8 instructions a character,
    60-80 a word, against a (FIND) of up to ~6000; 3-7 us a word at 24
    MHz; nothing at all for compiled code.
  - Tests: test_nucleus.py has UPPER's own checks (all 26 letters, the
    neighbours ` { @ [, bytes above 7F, the length, an odd address);
    test_listings.py the small-letter lines after "the prompt" (these
    are also typed at the board by make test-board).
  - The board must be reflashed (make flash) to get it. minichlink
    writes the image only (13100 bytes, below 4000 hex), so the disc,
    screens 4, 5 and 42-45, should survive: check with 4 LIST and
    42 LIST after the first flash with UPPER.
