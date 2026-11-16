# fig-FORTH for RISC-V

fig-FORTH (the Forth Interest Group's model, Release 1) for 32-bit RISC-V,
written for the [bronzebeard](https://github.com/theandrew168/bronzebeard)
assembler. The first target is the WCH CH32V006 (RV32EC, 62 KiB flash,
8 KiB RAM).

**What is here: the nucleus.** The 46 CODE words of the model, the code that
`:` `CONSTANT` `VARIABLE` `USER` and `DOES>` point new words at, and the cold
and warm start. The high-level words (the text interpreter, the compiler, the
disc words, the editor) are not written yet; in their place a stand-in `ABORT`
prints a line and echoes keys.

    LIT EXECUTE BRANCH 0BRANCH (LOOP) (+LOOP) (DO) I DIGIT (FIND) ENCLOSE
    EMIT KEY ?TERMINAL CR CMOVE U* U/ AND OR XOR SP@ SP! RP! ;S LEAVE >R R> R
    0= 0< + D+ MINUS DMINUS OVER DROP SWAP DUP +! TOGGLE @ C@ ! C! S->D

It has run in an emulator only. It has not been on the chip.

## Files

| | |
|---|---|
| `figforth.asm` | the nucleus, in the order of the model's screens |
| `boards/ch32v006/board.asm` | the chip: vector table, clock, console UART, trap handler |
| `tools/header.py` | prints the header of a word, to paste into the source |
| `tests/test_nucleus.py` | assembles the image and runs every word in the emulator |
| `tests/rv32emu.py` | the RV32EC emulator of the sixforths repository, unchanged |

## Build, test, flash

    pip install bronzebeard
    make            # figforth.bin, 2544 bytes, and figforth.labels
    make test       # 403 checks
    make flash      # minichlink -w figforth.bin flash -b
    make term       # picocom -b 115200 /dev/ttyACM0

`make flash` replaces the kernel that is on the board (sixforths). The image is
under 4 KiB, so the source lines sixforths keeps from 0x4000 on are not touched.
After it, the console should show `fig-FORTH RISC-V nucleus` and then echo what
is typed. The terminal needs no character maps: `CR` sends CR and LF, and Enter
is CR, as the model expects.

## How the model was fitted to RISC-V

**Cells are 32 bits.** A double number is 64 bits, high cell on top. True is 1,
as in the model.

**Registers.** `IP` = s1, `W` = a0, the data stack pointer (`DSP`) = s0, the
return stack pointer (`RSP`) = tp, the user area pointer (`UP`) = gp. `sp` is
left to the machine: on this chip an interrupt puts its frame there. Both
Forth stacks grow down and point at their top item. Only x0-x15 are used, and
no multiply or divide instruction: `U*` and `U/` are the model's shift loops,
32 times round.

**`PUSH` `PUT` `NEXT` `POP` `POPTWO`** are the model's shared endings: a word
jumps to one of them with its result in a1.

**Headers** are the model's (name, link, code field, parameter field), with
one addition. `lw` and `sw` trap on the CH32V006 unless the address is a
multiple of 4, so the name field is filled with blanks up to a cell boundary,
and bit 7 marks its last byte, blank or not:

    DUP     83 'D' 'U' 'P'+80
    SWAP    84 'S' 'W' 'A' 'P' 20 20 A0
    +       81 '+' 20 A0

`(FIND)` needs no change for this, because `WORD` leaves blanks after the text
it puts at `HERE`. `CREATE` will need one line: round `DP` up after the name.

**Branches** hold the distance from their own cell to the target, as in the
model. bronzebeard's `%offset(label)` is exactly that number.

**`U/`** takes a divisor of all 32 bits: it keeps the bit that each shift
pushes out of the remainder, which the model's loop drops. A quotient that
does not fit in a cell is wrong, and dividing by zero gives a quotient of all
ones; neither traps.

**Memory.** Flash from 0: vector table, serial routines, the `origin` table
(cold and warm entry, the cells `COLD` copies to the user area), the
dictionary. RAM from the top: data stack (64 cells), return stack (64 cells),
machine stack (24 cells), terminal input buffer (96 bytes), user area (32
cells). The dictionary of new words will grow up from the start of RAM.

## Writing for bronzebeard

Found while writing this; each was tried.

- **No macros.** Every header is written out. `python3 tools/header.py NAME
  label previous [code-field]` prints one. The test walks the dictionary and
  checks every header.
- **`last_nfa:`** stands on the name field of the newest word. Move that line
  when a word is added at the end.
- **A label cannot be a Python keyword**: `in:` `if:` `else:` `while:` `and:`
  `or:` `not:` do not assemble. The source uses the labels of the fig-FORTH
  listings (`andd`, `orr`, `zequ` ...).
- **One value per `dw`.** A thread is one `dw` per line.
- **`string` takes the rest of the line as it is**: no comment after it and no
  blank at the end.
- **Character literals**: `'#'`, `'('` and `')'` do not assemble, and `','`
  gives a blank without an error. Write the number.
- **Division** in an expression is `//`.
- **A CSR number above 0x7FF** is written as the number minus 0x1000.
- **The image must sit at address 0.** A label is its offset in the image and
  there is no origin directive. The CH32V006 maps its flash at 0.
- **Do not use `-c`** (compressed instructions). The assembler picks the short
  forms before the addresses are final; with this source, `li IP, abort + CELL`
  then stops the assembly with "imm must not be 0".

## Next: the high-level words

The rest of the model is colon definitions, written as threads like the
stand-in `ABORT` at the end of `figforth.asm`. From reading the model, these
are the places where a definition cannot be copied as it stands. None of it
is written or tried yet.

*The cell is 4 bytes.* `,` (`2 ALLOT`), `COMPILE` (`2+`), `LFA` `CFA` `NFA`
`PFA` (4, 2, 5, 5 become 8, 4, 9, 9), `CREATE` (`HERE 2+ ,`), `VOCABULARY`
and `FORGET`, `+BUF` `BUFFER` `BLOCK`, the update bit `8000`. Not every 2 is a
cell: the 1, 2, 3 that `BEGIN` `IF` `DO` leave are the compiler's pairing
marks, and `EXPECT` counts characters.

*Alignment.* `CREATE` rounds `DP` up after the name (in place of its "6502
only" line). `(.")` must leave the return address on a cell boundary, and `."`
must round `DP` up after the text. `EXPECT` ends the line with `0 I 1+ !`, a
store to any address: two `C!`. The dummy name `A081` in `VOCABULARY` and the
header of the null word (`8081`) become four bytes.

*The kernel is in flash and cannot be written.* `USE` and `PREV` are
variables with their value in the dictionary: make them user variables. The
`FORTH` vocabulary keeps the address of its newest word in its own parameter
field, which every new definition changes: that cell has to live in RAM.

## Licence

fig-FORTH is in the public domain through the courtesy of the Forth Interest
Group; its notice is at the top of `figforth.asm` and must stay there.
