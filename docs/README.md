# fig-FORTH for RISC-V

fig-FORTH (the Forth Interest Group's model, Release 1) for 32-bit RISC-V,
written for the [bronzebeard](https://github.com/theandrew168/bronzebeard)
assembler. The first target is the WCH CH32V006 (RV32EC, 62 KiB flash,
8 KiB RAM).

**What is here: the model, with its editor.** The 46 CODE words (the nucleus),
176 high-level words in `FORTH` (the text interpreter, the compiler, the
defining words, vocabularies, number input and output, `FORGET`, `VLIST`, and
the disc: `BLOCK` `BUFFER` `UPDATE` `LOAD` `-->` `LIST` `INDEX` `TRIAD`) and the
28 words of the `EDITOR` vocabulary. It starts, reads a line, and answers
`OK`:

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

**The editor** is the sample editor of the manual (screens 87 to 97), in the
kernel. `EDITOR` makes its words known; a `:` or a `LOAD` goes back to
`FORTH`, so say `EDITOR` again after one.

    EDITOR
    1 CLEAR                 fill screen 1 with blanks; it is now the screen
    0 P : SQ DUP * ;        put text on line 0
    1 P 7 SQ .
    L                       list the screen
    FLUSH                   write it to the disc
    1 LOAD                  49

| | |
|---|---|
| `n CLEAR` `n1 n2 COPY` | blank a screen; copy screen n1 to n2 (`FLUSH` first) |
| `L` `n T` | list the screen; type line n and hold it |
| `n P text` `n E` | put text on line n; erase line n |
| `n H` `n R` `n I` | hold line n; replace line n by what is held; insert it at n |
| `n D` `n S` | delete line n (it is held); spread, making line n blank |
| `TOP` `n M` | cursor to the top; move it by n characters |
| `F text` `N` `B` | find text; find it again; back over it |
| `X text` `TILL text` | find and delete text; delete from the cursor up to text |
| `C text` | put text in at the cursor |
| `FLUSH` | write all changed blocks to the disc |

After an error in a `LOAD`, `WHERE` shows the line and enters the editor.

The nucleus and the high-level words without the disc have run on the chip:
the lines of `tests/test_listings.py` were typed at it. The disc and the
editor have run in the emulator only.

## Files

| | |
|---|---|
| `MANUAL.txt` | how it works and why: the dictionary, the memory map, errors, the disc, the differences from the model |
| `figforth.asm` | the nucleus: the CODE words, in the order of the model's screens, and the cold start |
| `listings.asm` | the high-level words: colon definitions written out as threads, with the code behind `;CODE`. Written by `tools/listing.py`; do not edit |
| `board.asm` | the chip (CH32V006): vector table, clock, console UART, trap handler, flash page writer |
| `docs/fig-FORTH_Installation_Manual.pdf` | the model: its screens are what `listings.asm` was written from |
| `tools/words.py` | every high-level word as its Forth definition: the source of `listings.asm` |
| `tools/listing.py` | writes `listings.asm` from it (`make listing`) |
| `tools/header.py` | prints the header of a word; `listing.py` uses it |
| `tools/board_test.py` | types the tests at the real board (`make test-board`); writes over screens 40 and 41 |
| `tools/forth-assembler.f` | an `ASSEMBLER` vocabulary for RISC-V, in Forth: four screens for the disc, `42 LOAD` (MANUAL.txt section 16) |
| `tools/put_screens.py` | types a source file onto empty screens of the board's disc with the editor and reads them back (`make put-assembler`) |
| `tests/test_nucleus.py` | assembles the image and runs every word of the nucleus in the emulator |
| `tests/test_listings.py` | starts the image in the emulator and types lines at it |
| `tests/rv32emu.py` | the RV32EC emulator of the sixforths repository, unchanged |

## Build, test, flash

    pip install bronzebeard
    make            # figforth.bin, 13028 bytes, and figforth.labels
    make test       # 403 checks of the nucleus, 211 of the listings
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
`COLD` fills, and `FORTH` is a colon definition. `EDITOR` is the same, in the
next three cells. `USE` and `PREV` are user
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

**The editor** is in the kernel because the model's last screen makes it so:
it moves `FENCE` and the cold start values past the editor. Its one CODE
word, `MATCH`, is translated from the 6502, as the manual allows. In `FLUSH`
and `COPY` the model's `B/BUF 4 +` and `2 -` are for its buffer; here the
count of buffers is a number and the step back to the block number is 4.

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
data stack (64 cells), return stack (64 cells), machine stack (24 cells), the
three disc buffers (792 bytes), terminal input buffer (96 bytes), user area
(32 cells). RAM from the bottom: the bodies of `FORTH` and `EDITOR` (6 cells), then
the dictionary of new words. The free cells are for a word run on an empty
stack: it reads them, prints `MSG # 1`, and the chip does not trap. At the
other end `?STACK` says `MSG # 7` when more than 56 numbers are on the stack;
the last 8 cells are what the interpreter itself needs between two words.

## Writing for bronzebeard

Found while writing this; each was tried.

- **No macros.** Every header is written out. `python3 tools/header.py NAME
  label previous [code-field]` prints one. The test walks the dictionary and
  checks every header.
- **`last_nfa:`** and **`last_enfa:`** stand on the name fields of the newest
  words of `FORTH` and `EDITOR`; `tools/listing.py` puts them there.
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

## Next

The screens of error messages (4 and 5 in the manual) are not on the disc.
Type them with the editor and set `1 WARNING !` to have errors in words.

## Licence

fig-FORTH is in the public domain through the courtesy of the Forth Interest
Group; its notice is at the top of `figforth.asm` and must stay there.
