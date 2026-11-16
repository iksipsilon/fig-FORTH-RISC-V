# fig-FORTH for RISC-V

fig-FORTH (the Forth Interest Group's model, Release 1) for 32-bit RISC-V,
written for the [bronzebeard](https://github.com/theandrew168/bronzebeard)
assembler. The first target is the WCH CH32V006 (RV32EC, 62 KiB flash,
8 KiB RAM).

**What is here: the kernel of the model.** The 46 CODE words (the nucleus) and
172 high-level words: the text interpreter, the compiler, the defining words,
vocabularies, number input and output, `FORGET`, `VLIST`, and the disc:
`BLOCK` `BUFFER` `UPDATE` `LOAD` `-->` `LIST` `INDEX` `TRIAD`. It starts, reads a
line, and answers `OK`:

    fig-FORTH RISC-V
    : SQ DUP * ; OK
    7 SQ . 49 OK
    FOO FOO? MSG # 0

Names are in capitals, as then. An error is a number (the list is in the
Installation Manual): 0 not found, 1 empty stack, 4 not unique, 6 disc range,
8 disc error, 17 compilation only, 18 execution only, 19 conditionals not
paired, 20 definition not finished, 21 in protected dictionary, 24 declare
vocabulary. After an error two numbers are on the stack, `IN` and `BLK`.

New words go into RAM (about 6.5 KiB) and are gone at power-off. What is
written to the disc stays.

**The disc is the flash above the kernel**: 0x4000 to 0xF800, 46 KiB. A block
is 256 bytes, one page of the flash; a screen is 4 blocks; there are screens
0 to 45. `n LIST` shows a screen and `n LOAD` interprets it. A block that was
changed (`UPDATE`) is written when its buffer is wanted for another, or by
`FLUSH`. A flash that was never written reads as FF, which `LIST` shows as
rubbish; the sixforths source lines are still there until they are written
over.

**Not here: the editor**, and `FLUSH`, which the model defines on its editor
screens. Until then, type it:

    : FLUSH  [ LIMIT FIRST - B/BUF 8 + / ] LITERAL 0 DO 32767 BUFFER DROP LOOP ;

The nucleus and the high-level words without the disc have run on the chip:
the lines of `tests/test_listings.py` were typed at it. The disc has run in
the emulator only.

## Files

| | |
|---|---|
| `figforth.asm` | the nucleus: the CODE words, in the order of the model's screens, and the cold start |
| `listings.asm` | the high-level words: colon definitions written out as threads, with the code behind `;CODE` |
| `board.asm` | the chip (CH32V006): vector table, clock, console UART, trap handler, flash page writer |
| `fig-FORTH_Installation_Manual.pdf` | the model: its screens are what `listings.asm` was written from |
| `tools/header.py` | prints the header of a word, to paste into the source |
| `tests/test_nucleus.py` | assembles the image and runs every word of the nucleus in the emulator |
| `tests/test_listings.py` | starts the image in the emulator and types lines at it |
| `tests/rv32emu.py` | the RV32EC emulator of the sixforths repository, unchanged |

## Build, test, flash

    pip install bronzebeard
    make            # figforth.bin, 11076 bytes, and figforth.labels
    make test       # 402 checks of the nucleus, 177 of the listings
    make flash      # minichlink -w figforth.bin flash -b
    make term       # picocom -b 115200 /dev/ttyACM0

`make flash` replaces the kernel that is on the board (sixforths). The image is
under 16 KiB, so it does not reach the disc at 0x4000.
After it, the console should show `fig-FORTH RISC-V` and wait for a line. The
terminal needs no character maps: `CR` sends CR and LF, and Enter is CR, as
the model expects. Backspace is the key that sends 7F.

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
it puts at `HERE`. `CREATE` rounds `DP` up before and after the name. `ALIGN`
does that; it is not a word of the model, and it is wanted after `C,` or an
odd `ALLOT`. The text after `(.")` is padded the same way.

**The cell is 4 bytes** wherever the model has a 2 that means a cell: `,`
`COMPILE` `LFA` `CFA` `NFA` `PFA` `CREATE` `VOCABULARY`. `2+` still adds 2.

**The kernel is in flash**, so nothing in it can change. The body of the
`FORTH` vocabulary (its newest word) is three cells at the start of RAM that
`COLD` fills, and `FORTH` is a colon definition. `USE` and `PREV` are user
variables.

**The disc** is the manual's RAM disc (`R/W` between `LO` and `HI`, section
"RAM DISC SIMULATION"), with the flash as the memory: reading is its `CMOVE`,
writing is the CODE word `BLOCK-WRITE`, which erases and programs a page and
reads it back. It refuses any address that is not a block of the disc, so the
kernel cannot be written over from Forth. `B/BUF` is 256 because the chip
programs 256 bytes at a time; a buffer is `B/BUF` + 8. There are three
buffers: the manual asks for two or more, but with two its `FLUSH` can pass a
changed buffer by. A cold start does `EMPTY-BUFFERS`, which the manual leaves
to the operator: here a buffer of leftover RAM could be written to the flash.
There is one drive, so no `DR1`.

**Everything else is the model's**, definition for definition: `<` is `- 0<`,
an error leaves `IN` and `BLK` on the stack, `LEAVE` ends the loop at the next
`LOOP`, and `:` `CONSTANT` `VARIABLE` `USER` `DOES>` end in `;CODE` with their
machine code behind it (`docol` `docon` `dovar` `douse` `dodoe`). The one word
added is `ALIGN`.

**Branches** hold the distance from their own cell to the target, as in the
model. bronzebeard's `%offset(label)` is exactly that number.

**`U/`** takes a divisor of all 32 bits: it keeps the bit that each shift
pushes out of the remainder, which the model's loop drops. A quotient that
does not fit in a cell is wrong, and dividing by zero gives a quotient of all
ones; neither traps.

**Memory.** Flash from 0: vector table, serial routines, the `origin` table
(cold and warm entry, the cells `COLD` copies to the user area), the
dictionary, and from 0x4000 the disc. RAM from the top: 8 cells left free,
data stack (56 cells), return stack (64 cells), machine stack (24 cells), the
three disc buffers (792 bytes), terminal input buffer (96 bytes), user area
(32 cells). RAM from the bottom: the body of `FORTH` (3 cells), then
the dictionary of new words. The free cells are for a word run on an empty
stack: it reads them, prints `MSG # 1`, and the chip does not trap. Nothing
guards the other end: more than 56 items run into the return stack.

## Writing for bronzebeard

Found while writing this; each was tried.

- **No macros.** Every header is written out. `python3 tools/header.py NAME
  label previous [code-field]` prints one. The test walks the dictionary and
  checks every header.
- **`last_nfa:`** stands on the name field of the newest word (in
  `listings.asm`). Move that line when a word is added at the end.
- **`call` beyond 2 KiB is wrong.** bronzebeard makes it one `jal` and keeps
  only the low 12 bits of the distance. Write `jal ra, label`.
- **`string` and `#`.** A name or a text with `#` `"` `'` or `,` in it is written
  as numbers (`bytes`); `tools/header.py` does that.
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

## Next: the editor

The model's editor is on screens 87 to 97 of the manual, in Forth, with one
CODE word (`MATCH`). It is to be typed onto the disc and loaded from there.
Its screens are written for a block of 128 bytes in two places (`FLUSH` and
`COPY` use `B/BUF 4 +` and `2 -`, which are `B/BUF 8 +` and `4 -` here).

## Licence

fig-FORTH is in the public domain through the courtesy of the Forth Interest
Group; its notice is at the top of `figforth.asm` and must stay there.
