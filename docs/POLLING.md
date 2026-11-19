# POLLING.md — talking to the modem by polling

A recap of the design discussion of 17–18 November 2026: how the CH32V006 in
the forthphone talks to the A7670E modem over USART2, by polling only, in
fig-FORTH, with as little assembly and as few peripherals as possible.

It is written for two readers: the owner of the project, as a reminder, and
Claude Code, as the record of what was decided, why, and what is still open.
Numbers marked *estimate* were worked out on paper, not measured on the board.
Numbers marked *datasheet*, *RM* (CH32V00x reference manual V1.5) or *manual*
(SIMCom A76XX Series AT Command Manual V1.12) come from those documents.

---

## Contents

1. The mission
2. The hardware and the software it runs on
3. What was decided (the short version)
4. How we got there: the options that were looked at and dropped
5. Facts about the chip that matter here
6. The two timing limits (and why they are different things)
7. The baud rate and the clock
8. The modem: the AT commands that matter
9. The robustness rules: why lost bytes are not a disaster
10. Flash, SIM and when to write
11. The main loop
12. The Forth code (one screen, untested)
13. Open items and things to check on the board
14. Notes for Claude Code
15. Appendix A: SD card versus internal flash (dropped, kept for reference)
16. Appendix B: running the flash routines from RAM (dropped)
17. Appendix C: the DMA ring (dropped)
18. Sources

---

## 1. The mission

In the owner's words: receive and send AT commands via UART from and to the 4G
modem in the simplest possible way, written in FORTH, with as little assembly
as necessary. Every other feature of the phone is subordinated to this task.

The guiding wishes, stated several times during the discussion:

- Keep it simple. No bells and whistles. The chip has DMA, interrupts, SysTick
  and more; they are known and deliberately not used.
- Use as few peripherals and extras as possible, so the code stays compact and
  easy to understand, yet fully functional.
- Write in Forth wherever possible. Use CODE words (written with the Forth
  assembler on the screens) only for the time-critical parts.
- Stay with plain tools: the bronzebeard assembler (Python) for the kernel, the
  Forth assembler written by Claude for CODE words, and perhaps an assembler of
  the owner's own later.

---

## 2. The hardware and the software it runs on

**The MCU.** WeAct Studio CH32V006F8U6 board. QingKe V2C core (RV32EC + Zmmul
+ Zicsr), 62 KiB flash, 8 KiB SRAM, internal 24 MHz HSI oscillator (48 MHz
possible through the PLL, which multiplies HSI by 2).

**The modem.** Waveshare A7670E Cat-1 HAT (SIMCom A7670E). It is connected to
the MCU's USART2: TX on PD2, RX on PD3 (AFIO remap USART2_RM = 011). The
console stays on USART1 (TX PD5, RX PD6, 115200 baud) through the WCH-LinkE.

**The rest of the phone.** 8 pushbuttons read through a 74HC165 shift
register, a microphone, a 5x42 red LED matrix driven by an MBI5024 chain, and a
speaker. Voice audio does not go over the UART: the HAT has its own analog
audio path (NAU8810 codec, earphone jack). The UART carries only AT commands,
their answers and SMS text.

**The HAT's UART lines.** Only TXD, RXD and DTR are brought to the header, each
through a transistor level shifter (Q1, Q3, Q4 on the Waveshare schematic). The
module's CTS and RTS (module pins 7 and 8) and its ring indicator RI (pin 4)
stop at the module and run at its 1.8 V I/O level (VDD_EXT). So hardware flow
control and the RI pin are not available without soldering to the module.

**The software.**

- `fig-FORTH-RISC-V` (github.com/iksipsilon/fig-FORTH-RISC-V): the current
  work. A port of the fig-FORTH model (Installation Manual, Release 1) to the
  CH32V006. Kernel in bronzebeard assembly (`board.asm`, `figforth.asm`,
  `listings.asm`). Blocks of 256 bytes in flash from 0x4000 to 0xF800
  (blocks 0–183, screens 0–45). The Forth assembler is on screens 42–45
  (`tools/forth-assembler.f`). Names are folded to capitals by `UPPER` in
  `-FIND`.
- `sixforths` (github.com/iksipsilon/sixforths, branch `kernel-phase1`): the
  earlier, more assembly-heavy system. It is still the source of register
  addresses and bit values that were checked on this board (`src/mcu.s`,
  `src/13-modem.s` on that branch). It is no longer developed for the phone;
  its log commits were replaced by blocks.

**How the phone is used.**

- Code is written and edited at the desk, with the phone connected to the PC
  through the WCH-LinkE. During that time the SIM can be taken out, so the
  modem is quiet and nothing it says can be lost.
- During normal phone use, writing is rare and small: saving a contact,
  writing an SMS, setting the volume. Contacts and SMS can live on the SIM
  (or in the modem's own memory), written by the modem through AT commands.

---

## 3. What was decided (the short version)

- **Polling only.** The modem's USART2 is read by polling its status register.
  No DMA, no interrupts. SysTick is not used either (see section 7).
- **No SD card.** Internal flash (blocks) and the SIM are enough.
- **The modem keeps the state; the MCU asks for it.** Unsolicited messages
  from the modem (RING, +CMTI, NO CARRIER ...) are treated as hints. The truth
  comes from queries (AT+CLCC, AT+CMGL, AT+CMGR ...), which can be repeated
  until their answer arrives intact. So correctness does not depend on never
  losing a byte (section 9).
- **Every line received from the modem is checked.** The USART's error flags
  (overrun, framing, noise, parity) are collected over the line; a line with
  any error, or an answer without its final OK, is thrown away and the
  question is asked again.
- **SMS are stored by the modem** (AT+CNMI with `<mt>` = 1) and deleted only
  after they have been read intact. Deleting is the acknowledgement.
- **Flash writes happen when no modem traffic is expected,** and contacts and
  SMS are written to the SIM (or modem memory) rather than to MCU flash. A SIM
  write never freezes the MCU: the modem does the work while the main loop
  keeps polling, scanning buttons and updating the display, waiting for OK.
- **One main loop, cooperative.** Poll the modem, scan the buttons, do one
  small piece of display or application work, repeat.

The owner's conclusion at the end: with the modem keeping the state and
everything re-askable, the CPU clock and the UART baud rate are no longer
critical for correctness. See section 7 for the one thing they still decide:
how often a line gets damaged.

---

## 4. How we got there: the options that were looked at and dropped

The discussion went through these steps, in this order:

1. **SD card over SPI versus internal flash.** Compared speeds (appendix A).
   Conclusion later: skip the SD card.
2. **The flash stall.** While the flash controller erases or programs a page,
   the core stands still (all of fig-Forth runs from flash). In sixforths the
   source log committed lines to flash during normal operation, so this
   mattered then.
3. **Running the flash routines from RAM** (appendix B). Costs 176 bytes of
   RAM (or an 18-byte stub), but buys nothing unless the waiting loop does
   useful work, and an interrupt taken meanwhile would stall anyway (its
   vector and handler are in flash). Dropped.
4. **Polling instead of DMA.** At 115200 baud the USART must be read within
   87 µs, every time, also for unsolicited messages; high-level Forth cannot
   keep that promise everywhere. Interrupts would not help either: the handler
   would be in flash and could not run during a flash write.
5. **Hardware flow control (RTS/CTS)** would let the modem wait for the MCU.
   Not available: the HAT does not bring CTS/RTS to the header.
6. **A lower baud rate.** The modem supports 300 to 3686400 baud
   (AT+IPR / AT+IPREX). Lower rates stretch the deadline per byte.
7. **A RAM buffer filled by DMA** (appendix C): the robust textbook answer,
   used in sixforths. Dropped by decision: no DMA.
8. **48 MHz and a lower baud rate, polling only.** Accepted as the direction.
9. **Clarified** that two separate timing limits exist (section 6).
10. **SIM timing:** reads and writes through AT commands take the modem's time,
    not the MCU's; the MCU keeps running.
11. **Acknowledgements:** the modem does not know whether the MCU heard it,
    but its state can always be asked again. This made byte loss recoverable
    and closed the discussion.

---

## 5. Facts about the chip that matter here

**Flash** (*datasheet* Table 3-14, 3-15; *RM* chapter 18):

| Operation | Typical | Maximum |
|---|---|---|
| Page (256 bytes) program | 1.5 ms | 2.0 ms |
| Page (256 bytes) erase | 2.5 ms | 3.0 ms |
| Sector (1 KiB) erase | 2.7 ms | 3.3 ms |

- Endurance: 100 000 erase/write cycles at 70 °C, 300 000 at 25 °C. Retention
  10 years at 70 °C, 20 at 25 °C.
- The flash is erased and programmed in 256-byte pages, nothing smaller. In
  the fig port a block is exactly one page. A block write (`BLOCK-WRITE`,
  `disc_write` in `board.asm`) erases, programs and reads back one page: about
  4 ms typical, up to 5 ms. The core stands still during the erase and the
  program.
- Reading flash is reading memory (`R/W` reads a block with `CMOVE`). It never
  stalls anything. A 256-byte `CMOVE` takes roughly 0.1 ms (*estimate*).
- In the fig port a block is written when `FLUSH` is called or when `BLOCK`
  needs a buffer whose block was marked changed by `UPDATE`. The second case
  can happen at an unexpected moment.
- The chip runs code from SRAM (proven on the board 2026-11-17, `CLAUDE.md`
  section 4 of fig-FORTH-RISC-V). Whether the core keeps running from SRAM
  while the flash controller is busy is NOT verified, and is no longer needed.

**USART** (*RM* chapter 14):

- One receive data register, no FIFO. A second byte that completes while the
  first is unread is lost, and the overrun flag is set.
- Status register STATR (offset 0x00) bits: PE 0 (parity error), FE 1
  (framing error), NE 2 (noise), ORE 3 (overrun), RXNE 5 (a byte waits),
  TXE 7 (the data register can take a byte). Reading STATR and then DATAR
  clears PE, FE, NE and ORE.
- DATAR is at offset 0x04, BRR at 0x08, CTLR1 at 0x0C, CTLR2 at 0x10,
  CTLR3 at 0x14. USART1 is at 0x40013800, USART2 at 0x40004400.
- BRR holds HCLK / baud (USARTDIV in sixteenths, 16 bits). So the lowest
  possible baud rate is HCLK / 65535: about 366 baud at 24 MHz and 732 baud at
  48 MHz.

**Clock** (*RM* chapters 3 and 18):

- FLASH_ACTLR LATENCY (0x40022000): 0 wait states up to 15 MHz, 1 for 15–24
  MHz, **2 for 24–48 MHz**. `board.asm` sets 1, which is right for 24 MHz
  only. Must be set before the clock goes up.
- PLL: source HSI (PLLSRC, CFGR0 bit 16, = 0, write only while the PLL is
  off), PLLON is RCC_CTLR bit 24, PLLRDY bit 25. CFGR0 SW[1:0] = 10 selects the
  PLL, SWS[3:2] confirms it.
- Run current with HSI and all peripherals enabled (*datasheet* Table 3-6):
  2.5 mA at 24 MHz, 3.7 mA at 48 MHz. Negligible next to the modem.

**Register addresses used by the Forth screen** (checked on the board in
sixforths, `src/mcu.s`, `src/13-modem.s`):

| What | Address / value |
|---|---|
| RCC_PB2PCENR | 0x40021018; AFIOEN bit 0, USART2EN bit 13 |
| AFIO_PCFR1 | 0x4001000C; USART2_RM bits 22:20, 011 = TX PD2, RX PD3 |
| GPIOD_CFGLR | 0x40011400; four bits per pin (CNF, MODE) |
| GPIOD_BSHR | 0x40011410; low half sets output latch bits |
| USART2 | 0x40004400 |
| PD3 (RX) | CNF 10, MODE 00 (input with pull-up), latch bit 3 set first |
| PD2 (TX) | CNF 10, MODE 01 (alternate push-pull output), configured last |

---

## 6. The two timing limits (and why they are different things)

This caused one misunderstanding during the discussion, so it is spelled out.

**Limit 1: how long Forth may run between two looks at USART2.** The receive
register holds one byte, so the program must read it within one byte time
(10 bits: start, 8 data, stop). This limit depends on the baud rate AND on the
CPU clock, because the clock decides how much Forth fits into that time.

| Baud | Time per byte | Simple fig words in that time at 24 MHz (*estimate*) | at 48 MHz (*estimate*) |
|---|---|---|---|
| 115200 | 87 µs | about 150 | about 300 |
| 9600 | 1.04 ms | about 1 500–2 000 | about 3 000–4 000 |
| 4800 | 2.08 ms | about 3 000–4 000 | about 6 000–8 000 |
| 2400 | 4.17 ms | about 6 000–8 000 | about 12 000–16 000 |
| 1200 | 8.33 ms | about 12 000–16 000 | about 25 000–30 000 |

The estimate counts about 9 instructions per simple word (the way section 8
of fig-FORTH-RISC-V's `CLAUDE.md` counts `1 PORT !`) and about 1.5 cycles per
instruction. At 48 MHz the flash needs 2 wait states instead of 1, so the gain
is a little under twice.

**Limit 2: a block write.** The core stands still for up to 5 ms (erase up to
3 ms plus program up to 2 ms). This time is set by the flash, so the clock
does not change it at all. If the receive register is emptied just before
the write starts, no byte is lost only when one byte time is longer than the
write:

| Baud | Time per byte | Bytes lost during a 5 ms block write |
|---|---|---|
| 9600 | 1.04 ms | up to 4 |
| 4800 | 2.08 ms | up to 2 |
| 2400 | 4.17 ms | none for a typical 4 ms write, 1 for a worst-case 5 ms write |
| 1200 | 8.33 ms | none |

These numbers are the same at 24 MHz and at 48 MHz.

---

## 7. The baud rate and the clock

**The owner's conclusion:** because the modem keeps the state and every answer
can be asked for again (section 9), the CPU clock and the baud rate no longer
decide whether the phone works correctly. A line damaged during a block write
is simply asked for again.

**The caveat (Claude's note):** they still decide *how often* a line gets
damaged, and that must stay rare for re-asking to make progress. If the main
loop's longest step is longer than one byte time (limit 1), bytes are lost on
every long answer, not just around the rare block write, and a long answer
such as an SMS might never arrive intact. So the rule that remains is:

> Choose a baud rate at which the longest step of the main loop fits into one
> byte time. Then lines are damaged only around block writes, which are rare
> and scheduled.

At 115200 that budget is about 150 simple words at 24 MHz, which is too tight
for high-level Forth. At 9600 and below it is comfortable. A good way to find
out is to measure (section 13): run the main loop while the modem sends a long
answer and see whether the error flags ever trip.

**Baud register values** (BRR = HCLK / baud):

| Baud | BRR at 24 MHz (dec / hex) | BRR at 48 MHz (dec / hex) |
|---|---|---|
| 115200 | 208 / D0 | 417 / 1A1 |
| 9600 | 2500 / 9C4 | 5000 / 1388 |
| 4800 | 5000 / 1388 | 10000 / 2710 |
| 2400 | 10000 / 2710 | 20000 / 4E20 |
| 1200 | 20000 / 4E20 | 40000 / 9C40 |
| 600 | 40000 / 9C40 | not possible |

All of these divide exactly, except 115200, which is 0.16% off at 24 MHz
(208) and 0.08% off at 48 MHz (417). Both are fine.

**What each rate costs in reply time** (bytes over the wire only, `ATE0`,
text mode, a 13-digit number, a 160-character SMS):

| | Bytes both ways | 1200 | 2400 | 4800 | 9600 |
|---|---|---|---|---|---|
| `OK` alone | 6 | 50 ms | 25 ms | 12 ms | 6 ms |
| Write a contact (`AT+CPBW=...`, `OK`) | ~46 | 0.38 s | 0.19 s | 0.10 s | 0.05 s |
| Read a contact (`AT+CPBR=n` and answer) | ~55 | 0.46 s | 0.23 s | 0.11 s | 0.06 s |
| Write an SMS (`AT+CMGW`, `>`, text, Ctrl-Z, `+CMGW: n`, `OK`) | ~210 | 1.75 s | 0.88 s | 0.44 s | 0.22 s |
| Read an SMS (`AT+CMGR=n`: header, text, `OK`) | ~240 | 2.0 s | 1.0 s | 0.50 s | 0.25 s |

The modem's and SIM's own time comes on top (section 8).

**Options discussed:**

- **1200 baud:** the only standard rate where even a block write loses
  nothing, and every step of the main loop may take up to 8 ms. No special
  cases. Slow replies (2 s per SMS).
- **9600 baud:** eight times faster replies; a block write damages the line
  being received (up to 4 bytes), which the error-flag rule already handles.
- **2400 / 4800:** in between.

**Changing the modem's rate** (*manual* 10.2.3, 10.2.4):

- `AT+IPR=<rate>` changes it until the next reboot; then the modem goes back
  to the `AT+IPREX` value.
- `AT+IPREX=<rate>` changes it permanently (saved automatically). Default
  115200.
- Supported: 300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200,
  230400, 460800, 921600, 1842000, 3686400. No autobaud. `AT+IPR=?` shows what
  the module's firmware actually supports.
- Use `AT+IPREX`, not `AT+IPR`: if the modem reboots on its own (for example
  a supply dip during a transmit burst), it comes back at its IPREX rate. With
  only IPR set it would come back at 115200 while the MCU listens at the lower
  rate.
- Sequence: at 115200 send `AT+IPREX=<rate>`, wait for `OK`, change the MCU's
  BRR, send `AT` and check for `OK`. Not known yet: whether that first `OK`
  arrives at the old or the new rate (expected: old). At boot, if `AT` gets no
  answer at the chosen rate, try 115200 and set IPREX again (covers a replaced
  or factory-reset modem).

**48 MHz** (optional; offered, not done). The change belongs in `serial_init`
in `board.asm`, where the clock is already set up. `CPU_FREQ` drives the
console's BRR, so USART1 follows automatically.

```asm
RCC_CTLR   = 0x00               # 3.4.1 clock control
RCC_PLLON  = 1 << 24
RCC_PLLRDY = 1 << 25
CPU_FREQ   = 48000000           # was 24000000

serial_init:
    # 48 MHz needs two flash wait states (18.3.1: 24 < SYSCLK <= 48 MHz);
    # they must be set before the clock goes up
    li t0, FLASH_R_BASE
    li t1, 2
    sw t1, FLASH_ACTLR(t0)

    # SYSCLK = PLL = HSI x 2 = 48 MHz (3.3.4)
    li t0, RCC_BASE
    sw zero, RCC_CFGR0(t0)      # HSI, no prescaler, PLLSRC = HSI
    lw t1, RCC_CTLR(t0)
    li t2, RCC_PLLON
    or t1, t1, t2
    sw t1, RCC_CTLR(t0)         # PLL on
serial_init1:
    lw t1, RCC_CTLR(t0)
    li t2, RCC_PLLRDY
    and t1, t1, t2
    beqz t1, serial_init1       # wait until it is locked
    li t1, 2
    sw t1, RCC_CFGR0(t0)        # SW = 10: the PLL drives SYSCLK
serial_init2:
    lw t1, RCC_CFGR0(t0)
    andi t1, t1, 0xC
    li t2, 0x8
    bne t1, t2, serial_init2    # wait until SWS says PLL
    # ... then the clocks for USART1 and port D, as now
```

**SysTick.** Not used. Debouncing and timeouts are counted in main-loop passes;
they only need to be roughly right. The time of day comes from the modem
(`AT+CCLK?`). If pass counts ever get awkward, the counter alone needs no
interrupt: `1 E000F000 !` starts it at HCLK/8 and `E000F008 @` reads it. It
can also serve once, at the desk, as a stopwatch for measurements, without
being part of the phone's code.

---

## 8. The modem: the AT commands that matter

**Setup**

| Command | Purpose |
|---|---|
| `ATE0` | No echo of what the MCU sends: fewer bytes, nothing to read while sending |
| `AT+IPREX=<rate>` | Permanent baud rate (section 7) |
| `AT+CPIN?` | SIM state; `+CPIN: READY` when unlocked |
| `AT+CPIN="1234"` | Enter the PIN (or disable the lock with `AT+CLCK="SC",0,"1234"`) |
| `AT+CREG?`, `AT+CEREG?` | Network registration (`0,1` or `0,5` = registered); takes 5–20 s after start |
| `AT+CMGF=1` | SMS text mode |
| `AT+CNMI=...` with `<mt>` = 1 | Store new SMS and report `+CMTI: "SM",<index>` |
| `AT+CPMS` | Where SMS are stored: SIM (`"SM"`) or the modem's own memory (`"ME"`) |
| `AT+CLCC=1` | Optional: the modem reports call state changes as `+CLCC:` lines on its own |
| `AT+CSDVC=3`, `AT+CLVL=5`, `AT+CMIC=0,5` | Audio to the jack, speaker volume, mic gain (from the owner's notes) |
| `AT+CCLK?` | The time of day, from the modem |

**Calls**

| Command / message | Meaning |
|---|---|
| `RING` | Incoming call; repeats every few seconds while it rings |
| `+CLIP: "<number>",...` | Caller's number after each RING (when enabled with `AT+CLIP=1`) |
| `ATA` | Answer |
| `ATD<number>;` | Dial (the semicolon makes it a voice call); `OK` = dialling started |
| `AT+CHUP` | Hang up |
| `AT+CLCC` | List current calls and their state: the question that tells the truth |
| `NO CARRIER`, `VOICE CALL: END: 000041` | Call ended (seen on an A7670G); the number is the call length |
| `VOICE CALL: BEGIN` | Call connected (SIMCom message) |

**SMS**

| Command / message | Meaning |
|---|---|
| `+CMTI: "SM",<index>` | A new SMS was stored at `<index>` |
| `AT+CMGL="REC UNREAD"` | List unread messages (finds any whose `+CMTI` was lost) |
| `AT+CMGR=<index>` | Read one message |
| `AT+CMGD=<index>` | Delete one message (only after an intact read) |
| `AT+CMGS="<number>"` | Send: the modem answers `> ` (no CR LF after it), then the text, ended with Ctrl-Z (0x1A); ESC (0x1B) cancels. Answer `+CMGS: <mr>` and `OK` = the network accepted it |
| `AT+CMGW="<number>"` | Write to storage, same `> ` prompt; answer `+CMGW: <index>` and `OK` |
| `AT+CMSS=<index>` | Send a stored message |

Text mode allows 160 characters with the 7-bit GSM coding (*manual*).

**Phonebook (on the SIM)**

| Command | Meaning |
|---|---|
| `AT+CPBS` | Select the phonebook storage |
| `AT+CPBW=<index>,"<number>",<type>,"<name>"` | Write an entry (`<type>` 129 national, 145 international) |
| `AT+CPBR=<index>` | Read an entry |
| `AT+CPBR=?` | The SIM's limits; the manual's example `+CPBR: (1-500),40,14` = 500 entries, 40 digits, 14 for the name |
| `AT+CPBF` | Find entries |

**Maximum response times** (*manual*; ceilings, not typical times):

| Commands | Maximum |
|---|---|
| `AT+CPBS`, `AT+CPBR`, `AT+CPBF`, `AT+CPBW`, `AT+CPMS`, `AT+CMGF`, `AT+CPIN` | 9 s |
| `AT+CMGL`, `AT+CMGR`, `AT+CMSS`, `AT+CMGD`, `AT+CNMI` | 9 s |
| `AT+CMGS`, `AT+CMGW` | 40 s |

The typical times are not published. A SIM card is a slow device (a serial
link defaulting to about 10 kbit/s, EEPROM behind it); tens to hundreds of
milliseconds per entry is a reasonable guess (*estimate*), to be timed once
at the desk. These ceilings are what the MCU's timeouts must allow for.

**Avoid** direct SMS delivery (`AT+CNMI` with `<mt>` = 2, `+CMT:`). The text
then arrives once, inside the unsolicited message, and is not stored. The
standard (3GPP TS 27.005) has an acknowledgement for that mode, `AT+CNMA`, but
it is the more complicated route.

---

## 9. The robustness rules: why lost bytes are not a disaster

**There is no acknowledgement from the MCU to the modem.** The modem sends its
unsolicited messages once and never learns whether the MCU heard them. The
UART has no checksum.

**There is an acknowledgement from the modem to the MCU.** Every command gets
`OK` or `ERROR` (or a result line followed by `OK`). So the MCU always knows
whether the modem took a command.

**The modem keeps the state.** Whatever matters (is a call ringing, is a call
on, which SMS are stored and unread) can be asked for again at any time. So:

1. **Treat every unsolicited message as a hint** to go and ask. The answer to
   the question is the truth.
2. **Calls:** a missed `RING` is followed by the next one a few seconds later.
   `AT+CLCC` answers what is true now. If both end-of-call messages are
   missed, `AT+CLCC` shows no call.
3. **SMS:** stored mode. The message stays in storage until `AT+CMGD`.
   Deleting only after an intact read is the acknowledgement. A lost `+CMTI`
   is caught by `AT+CMGL="REC UNREAD"`, run after start-up and after any line
   that arrived damaged. A damaged `AT+CMGR` answer is read again.
4. **Every received line is checked.** Collect the USART's error flags (PE,
   FE, NE, ORE: mask 0x0F of STATR) over the whole line in a variable
   (`MERR` in the screen below). Start each line with `0 MERR !`. At the end,
   if `MERR @` is not zero, or the answer did not end with `OK`, throw the line
   away and ask again.
5. **Nothing is deleted before it was read intact.**

**Parity** is possible (`AT+ICF` sets the modem's framing, the USART's CTLR1
sets PCE/PS, and PE is already in the 0x0F mask), but at low baud rates over a
few centimetres of wire bit errors are very unlikely. The realistic failure
is the MCU being busy, which the overrun flag catches. Not planned.

---

## 10. Flash, SIM and when to write

- **Editing code** (screens, blocks) happens at the desk with the WCH-LinkE,
  the SIM out. The modem is quiet; nothing can be lost.
- **Contacts and SMS** go to the SIM (or the modem's memory) through AT
  commands. Unlike a block write, a SIM write never freezes the MCU: the modem
  does the work, and the main loop keeps polling, scanning buttons and
  updating the display while it waits for `OK`. The answer may take up to 9 s
  (40 s for `AT+CMGW`/`AT+CMGS`).
- **SMS are fetched** at a time the MCU knows it will not use the flash.
- **Settings** (for example the volume) may need a block in MCU flash. Rare.
  The rules for such a write:
  - choose a quiet moment (not in the middle of receiving a line, not while
    waiting for an answer); take any waiting byte just before starting;
  - `FLUSH` right after `UPDATE` (in the fig port `FLUSH` is an EDITOR word).
    Never leave a changed buffer behind, or a later `BLOCK` may write it out
    at a random moment;
  - afterwards check the error flags; if a line was damaged, ask again.
  - The volume could also simply be sent with `AT+CLVL` at start-up from a
    value on a screen, edited at the desk.
- **Reading blocks** never stalls anything.
- **A write is never one byte.** The smallest flash write is a whole 256-byte
  block, erase plus program, up to 5 ms.

---

## 11. The main loop

One loop, cooperative, no tasks, no interrupts:

```
BEGIN
   take a modem byte if one waits, add it to the line buffer
   ( a complete line? hand it to the application )
   scan the buttons ( every few ms, debounce )
   do one small piece of display work
   do one step of the application ( send a command, react to a line, time out )
AGAIN
```

Rules that keep it working:

- **No step may take longer than one byte time** at the chosen baud rate
  (section 6, limit 1). Anything long either goes into a CODE word or calls
  the modem poll inside its own loop.
- **The display.** The LED matrix is multiplexed and needs refreshing all the
  time. Do one row per pass. Shifting a row out to the MBI5024 chain is a
  natural CODE word (tens of microseconds in CODE, around half a millisecond
  in high-level Forth, *estimate*).
- **The buttons.** Reading the 74HC165 takes microseconds. A press lasts 50 ms
  or more, so reading every 5–10 ms (counted in passes) and accepting a change
  after 2–3 identical samples is enough.
- **Sending a command.** Send character by character with `MEMIT`, and take
  any received byte between characters (a `RING` can arrive while sending).
  With `ATE0` there is no echo.
- **The `> ` prompt** of `AT+CMGS` and `AT+CMGW` is not followed by CR LF, so
  the line collector must recognise `> ` as complete on its own.
- **Console output** in phone mode: keep it short, or poll the modem between
  characters. Each `EMIT` at 115200 waits up to 87 µs; a 40-character line
  blocks for 3.5 ms.
- **Timeouts** are counts of passes: at least 9 s for phonebook and SMS
  commands, 40 s for `AT+CMGW`/`AT+CMGS`. They only need to be roughly right.
- **Ask, don't assume:** after start-up, after a timeout and after a damaged
  line, ask the state again (`AT+CLCC`, `AT+CMGL="REC UNREAD"`).

---

## 12. The Forth code (one screen, untested)

All of USART2 in high-level fig-Forth, no CODE words. The register addresses
and the order of the writes come from sixforths (`src/mcu.s`,
`src/13-modem.s`), where they were checked on this board. NOT yet tried in
fig-Forth. Every line is at most 63 characters (a 64-character screen line
runs into the next one).

```forth
( MODEM ON USART2: PD2 TX, PD3 RX, POLLED )
HEX  40004400 CONSTANT U2   40011400 CONSTANT PD
: RMW ( MASK BITS ADDR -- )  >R SWAP R @ AND OR R> ! ;
: U2-INIT ( BRR -- )
  -1 2001 40021018 RMW            ( CLOCKS: USART2, AFIO )
  FF8FFFFF 300000 4001000C RMW    ( REMAP 011: PD2, PD3 )
  8 PD 10 + !  FFFF0FFF 8000 PD RMW   ( PD3 IN, PULL-UP )
  U2 8 + !  200C U2 0C + !        ( BAUD; UE TE RE )
  FFFFF0FF 900 PD RMW ;           ( PD2 OUT LAST )
0 VARIABLE MERR                   ( ANY ERROR IN THIS LINE )
: M?     U2 @ 20 AND ;            ( A BYTE WAITS )
: M@  U2 @ 0F AND MERR @ OR MERR !   U2 4 + @ FF AND ;
: MEMIT  BEGIN U2 @ 80 AND UNTIL  U2 4 + ! ;
: M"  22 WORD HERE COUNT OVER + SWAP
  DO I C@ MEMIT LOOP  0D MEMIT ;
: .M  BEGIN M? IF M@ EMIT ENDIF ?TERMINAL UNTIL ;  DECIMAL
```

What each word does:

- `RMW ( mask bits addr -- )` read-modify-write: keeps the bits of the
  register selected by `mask`, ORs in `bits`, stores it back. (`R` is fig's
  name for copying the top of the return stack.)
- `U2-INIT ( brr -- )` switches on the clocks of USART2 and AFIO, maps USART2
  to PD2/PD3, makes PD3 an input with pull-up (latch first, so it never passes
  pull-down; before the receiver, so a floating pin cannot look like a start
  bit), sets the baud register, switches the USART on (UE, TE, RE), and makes
  PD2 an output last, so the line is already idle high when PD2 starts
  driving it.
- `M? ( -- f )` true if a received byte waits (RXNE).
- `M@ ( -- c )` takes the byte; first ORs the error flags of this byte into
  `MERR` (PE, FE, NE, ORE). Reading STATR then DATAR clears the flags.
- `MEMIT ( c -- )` waits until the transmit register is free, then sends.
- `M" text"` sends `text` and a CR. It reads its text with `22 WORD` (as `."`
  does), so it works only typed at the terminal, not inside a definition.
- `.M` copies what the modem says to the console until a key is pressed.

Trying it at the terminal (24 MHz values; at 48 MHz use 1A1 for 115200 and
the 48 MHz column of section 7):

```forth
HEX D0 U2-INIT           ( 115200, the modem's default )
M" AT"  .M               ( should answer OK; any key ends .M )
M" ATE0"  .M
M" AT+IPREX=9600"  .M    ( or the rate chosen )
9C4 U2 8 + !             ( 9600 NOW; AT BOOT: 9C4 U2-INIT )
M" AT"  .M               ( should answer OK at the new rate )
```

Sending at 115200 before `ATE0` loses the modem's echo (the MCU does not read
while sending). That is harmless here: `.M` starts reading at the reply.

If `AT+IPREX` was already set to another rate earlier, start `U2-INIT` at
that rate instead of 115200.

fig-Forth details worth remembering here:

- `0 VARIABLE MERR`: fig's `VARIABLE` takes its initial value from the stack.
- In `HEX`, once the Forth assembler is loaded, `A0`–`A5` can be found as
  register names before they are tried as numbers. Write `0A0`–`0A5` for the
  numbers. (Also `0C` instead of `C`, which could be an EDITOR word.)
- A colon definition compiles the addresses of the words it uses, so a word
  must be redefined before the words that use it are compiled.

---

## 13. Open items and things to check on the board

- [ ] Load the screen above and try it at 115200 (`M" AT" .M`).
- [ ] Choose the baud rate; set it with `AT+IPREX`. Check whether the `OK` to
      `AT+IPREX` arrives at the old or the new rate.
- [ ] Decide on 48 MHz. If yes: the `serial_init` change in `board.asm`
      (section 7). Offered, not done.
- [ ] Stress test of limit 1: run the main loop while the modem sends a long
      answer (the whole SIM phonebook, `AT+CPBR=1,<last>` with `<last>` from
      `AT+CPBR=?`) and look at `MERR`. If it stays 0, every step fits. If not,
      make the long step shorter or lower the baud rate.
- [ ] Time a contact write/read and an SMS write/read once with a stopwatch.
- [ ] Compare SMS storage `"SM"` (SIM) and `"ME"` (modem) for speed.
- [ ] Check what the modem says after start-up before the SIM phonebook and
      SMS store answer (some SIMCom modules announce readiness; not confirmed
      for the A7670E in the manual excerpts read).
- [ ] Write the line collector: CR LF ends a line; `> ` alone is complete;
      overflow of the line buffer counts as a damaged line.
- [ ] Write the application state machine (idle, ringing, in call, sending
      SMS ...) on top of `AT+CLCC` and `AT+CMGL` as the sources of truth.
- [ ] Autostart: the phone used without a computer must start its main loop
      at power-on. fig-FORTH-RISC-V's `CLAUDE.md` section 5 currently advises
      against autostart (with good reasons for development). Revisit when the
      phone loop exists, for example: load a screen at power-on unless a key
      is held.
- [ ] Display: the row shift-out as a CODE word; one row per pass.

---

## 14. Notes for Claude Code

Taken from fig-FORTH-RISC-V's `CLAUDE.md` and from this discussion:

- Stay true to the fig-FORTH model; deviate only where the chip forces it,
  and say so in the comment above the word.
- Ask before changing the repo or the board when the owner asked a question
  rather than gave an order. Look at the disc before writing to it.
- The owner commits and pushes himself. Do not commit unless asked.
- The owner does not read Python. Explain tools by what they do and by the
  Forth or assembly they produce.
- Working style of 1979: the chip is the computer, picocom is its terminal,
  source lives on screens. Screen lines at most 63 characters.
- Never paste into the console: the chip has no input buffer, a key that
  arrives during compiling or a flash write is lost. Type one line at a time
  and wait for the answer.
- **Keep it simple.** Polling only. No DMA, no interrupts, no SysTick, no SD
  card, unless the owner changes this decision. Do not propose them again as
  the default; mention them only if a measured problem leaves no simpler way,
  and say so plainly.
- Forth first; CODE words (Forth assembler on screens 42–45) only where timing
  demands it; kernel changes (bronzebeard) only where the chip forces it.
- Mark estimates as estimates. Check register addresses against the RM before
  calling them right; the sixforths values were checked on this board.

---

## 15. Appendix A: SD card versus internal flash (dropped, kept for reference)

| | Internal flash | SD card over SPI |
|---|---|---|
| Read | Memory-mapped; about 10 MB/s in a copy loop at 24 MHz, 20 MB/s at 48 MHz (*estimate*); usually read in place | SCK at most HCLK/2: 12 MHz at 24 MHz (1.5 MB/s raw, ~0.8–1.2 MB/s polled), 24 MHz at 48 MHz (3 MB/s raw, ~1.5–2.5 MB/s polled); plus 0.1–1 ms latency per read command |
| Write | 256-byte page erase + program: ~64 KB/s; ~115 KB/s with 1 KiB sector erase; ~170 KB/s into erased pages | ~150–400 KB/s single-block, toward 1 MB/s multi-block |
| Latency | Fixed, at most 5 ms per page | Usually ms, occasional stalls of hundreds of ms (250 ms allowed by the spec) |
| Unit | 256 bytes | 512-byte block, needs a 512-byte RAM buffer |
| Size / wear | 62 KiB minus the kernel; 100k–300k cycles | Gigabytes, wear levelled by the card |

The SD card needs 100–400 kHz during initialisation (SPI prescaler /64 at
24 MHz = 375 kHz). Decided: no SD card.

---

## 16. Appendix B: running the flash routines from RAM (dropped)

- In sixforths, `fpage_prog` was 116 bytes and `fpage_erase` 58 bytes (+2 of
  padding): 176 bytes of RAM to run both from there. Both were
  position-independent, so a copy at boot would have worked.
- Only the waits on the long operations need to be in RAM: an 18-byte stub
  (store to FLASH_CTLR, poll BSY, return), 10 bytes with compressible
  registers.
- It buys nothing by itself: the core then spins in RAM instead of standing
  still, and any interrupt taken meanwhile fetches its vector and handler from
  flash and stalls anyway. It would only help if the waiting loop also read
  the USART, which is more code than it saves.
- Whether the core keeps running from SRAM while the flash controller is busy
  was never verified (the manuals do not say).

---

## 17. Appendix C: the DMA ring (dropped)

- sixforths received the modem through DMA1 channel 7 into a 256-byte ring
  (`MRING`), configured with a handful of register writes, no interrupt. Its
  notes say it kept every byte while the core stood still for 16 page erases.
- With a ring the deadline becomes 256 byte times: 22 ms at 115200, 267 ms at
  9600.
- In fig-Forth it would also have been just a few stores, but the ring would
  sit in the dictionary and keep being written after a `FORGET` or `COLD`.
- Dropped by decision: no DMA. Kept here because it is the answer if a
  measured problem ever leaves no simpler way.

---

## 18. Sources

- CH32V006 datasheet V2.0: Table 3-6 (run current), 3-14 and 3-15 (flash),
  3-22 (SPI).
- CH32V00x reference manual V1.5: chapter 3 (RCC, PLL), 7 (GPIO, AFIO),
  14 (USART), 16 (SPI), 18 (flash, 18.3.1 LATENCY, 18.4.5 fast programming).
- QingKe V2 processor manual V1.3: vector table, VTF, HPE, SysTick registers.
- SIMCom A76XX Series AT Command Manual V1.12, chapters 8 (phonebook),
  9 (SMS), 10 (serial interface):
  https://eicut.com/wp-content/uploads/2025/10/A76XX_Series_AT_Command_Manual_V1.12.pdf
- Waveshare A7670X Cat-1 HAT schematic (in the project docs).
- A7670G log with `+CLCC`, `NO CARRIER`, `VOICE CALL: END` (EEVblog forum):
  https://www.eevblog.com/forum/beginners/simcom-a7670g-labe-modem-fails-to-hang-up-a-call-(atchup)-or-make-a-second-one
- ModemManager simtech plugin (`VOICE CALL: BEGIN/END`, `AT+CLCC=1`):
  https://git.uninsane.org/colin/ModemManager/commit/395b22178c4f6dd24d552e82d2d46dfb24c65297
- fig-FORTH-RISC-V: `board.asm`, `figforth.asm`, `docs/MANUAL.txt`
  (sections 8 and 11), `CLAUDE.md`.
- sixforths, branch `kernel-phase1`: `src/mcu.s`, `src/13-modem.s`.
