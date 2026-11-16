# fig-FORTH for RISC-V

fig-FORTH (the Forth Interest Group's model, Release 1) for 32-bit RISC-V,
written for the [bronzebeard](https://github.com/theandrew168/bronzebeard)
assembler. The first target is the WCH CH32V006 (RV32EC, 62 KiB flash,
8 KiB RAM).

**What is here: the kernel without the disc.** The 46 CODE words of the model
(the nucleus) and 149 high-level words: the text interpreter, the compiler,
the defining words, vocabularies, number input and output, `FORGET`, `VLIST`.
It starts, reads a line, and answers `OK`:

    fig-FORTH RISC-V
    : SQ DUP * ; OK
    7 SQ . 49 OK
    FOO FOO? MSG # 0

Names are in capitals, as then. An error is a number (the model's list is in
the Installation Manual): 0 not found, 1 empty stack, 4 not unique, 17
compilation only, 18 execution only, 19 conditionals not paired, 20
definition not finished, 21 in protected dictionary, 24 declare vocabulary.

New words go into RAM (about 7 KiB) and are gone at power-off.

**Not here: the disc.** `BLOCK` `BUFFER` `LOAD` `LIST` and their company, the
editor, and the disc half of `WORD`, `QUIT`, `ERROR`, `MESSAGE` and the null
word.

It has run in an emulator only. The nucleus alone has been on the chip; the
high-level words have not.

## Files

| | |
|---|---|
| `figforth.asm` | the nucleus: the CODE words, in the order of the model's screens, and the cold start |
| `listings.asm` | the high-level words: colon definitions written out as threads, with the code behind `;CODE` |
| `board.asm` | the chip (CH32V006): vector table, clock, console UART, trap handler |
| `tools/header.py` | prints the header of a word, to paste into the source |
| `tests/test_nucleus.py` | assembles the image and runs every word of the nucleus in the emulator |
| `tests/test_listings.py` | starts the image in the emulator and types lines at it |
| `tests/rv32emu.py` | the RV32EC emulator of the sixforths repository, unchanged |

## Build, test, flash

    pip install bronzebeard
    make            # figforth.bin, 9020 bytes, and figforth.labels
    make test       # 402 checks of the nucleus, 131 of the listings
    make flash      # minichlink -w figforth.bin flash -b
    make term       # picocom -b 115200 /dev/ttyACM0

`make flash` replaces the kernel that is on the board (sixforths). The image is
under 16 KiB, so the source lines sixforths keeps from 0x4000 on are not touched.
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
`COLD` fills, and `FORTH` is a colon definition.

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
dictionary. RAM from the top: 8 cells left free, data stack (56 cells), return
stack (64 cells), machine stack (24 cells), terminal input buffer (96 bytes),
user area (32 cells). RAM from the bottom: the body of `FORTH` (3 cells), then
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

## Next: the disc

The model keeps source on disc, in screens of 1 KiB, and the editor is loaded
from there. The chip has no disc; the flash from 0x4000 up is free (46 KiB).
What that needs, none of it written:

- a word that writes a page of flash, in `board.asm`, and `R/W` on top of it
- the block buffers, in RAM: one screen and its header is 1028 bytes of the
  8 KiB
- `USE` and `PREV` as user variables: in the model they are variables with
  their value in the dictionary, which is flash here
- the disc half of `WORD`, `QUIT`, `ERROR`, `MESSAGE` and the null word, marked
  in `listings.asm`

## Licence

fig-FORTH is in the public domain through the courtesy of the Forth Interest
Group; its notice is at the top of `figforth.asm` and must stay there.
