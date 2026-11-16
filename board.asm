# fig-FORTH for RISC-V: the WCH CH32V006 (WeAct Studio CH32V006F8U6)
#
# QingKe V2C core: RV32EC + Zmmul + Zicsr, 62 KiB flash, 8 KiB RAM, HSI 24 MHz.
# The console is USART1: TX = PD5, RX = PD6, 115200 baud, 8N1.
#
# This file is the first thing in the image. A board file must
#   - put whatever the chip needs at address 0 and make reset reach `boot`
#   - define RAM_BASE and RAM_SIZE
#   - implement serial_init, serial_putc, serial_getc, serial_poll and trap_init
#   - define DISC_LO, DISC_HI and DISC_BLK and implement disc_init and
#     disc_write: the disc
# The routines are leaves, and use no stack. The serial ones use t0-t2 and a0
# only; disc_write says what it uses.
#
# The register addresses, the order of the writes and the reasons given for
# them come from the sixforths kernel (src/mcu.s, src/03-traps.s,
# src/11-flash.s), where they were checked on this board. The section numbers are those of the CH32V00x
# reference manual V1.5.

# The vector table (QingKe V2 processor manual, chapter 3): with mtvec = 3 the
# core takes entry n of this table as the address of the handler of
# exception or interrupt n. The table must be 1 KiB aligned, and address 0 is.
# Reset starts at address 0, so entry 0 is a jump instead of an address; it
# must fill the whole entry (the `align`).
    j boot                      # 0: reset
align 4
    dw 0                        # 1: reserved
    dw trap                     # 2: NMI
    dw trap                     # 3: every exception
# No interrupt is enabled. One that is needs the table extended to its number
# (SysTick is 12).

RAM_BASE = 0x20000000
RAM_SIZE = 8 * 1024

CPU_FREQ  = 24000000
BAUD_RATE = 115200

# Clock (RCC), chapter 3
RCC_BASE     = 0x40021000
RCC_CFGR0    = 0x04             # 3.4.2 clock configuration (0x20 at reset: HCLK = HSI / 3)
RCC_PB2PCENR = 0x18             # 3.4.7 PB2 peripheral clock enable
RCC_IOPDEN   = 1 << 5           # port D
RCC_USART1EN = 1 << 14

# Flash controller, chapter 18
FLASH_R_BASE = 0x40022000
FLASH_ACTLR  = 0x00             # 18.3.1 LATENCY[1:0], the wait states
FLASH_KEYR     = 0x04           # unlocks the control register: KEY1, then KEY2
FLASH_STATR    = 0x0C           # status: BSY in bit 0
FLASH_CTLR     = 0x10           # control
FLASH_ADDR     = 0x14           # the page to erase or program
FLASH_MODEKEYR = 0x24           # unlocks the fast (page) modes: KEY1, then KEY2
FLASH_KEY1 = 0x45670123
FLASH_KEY2 = 0xCDEF89AB
FLASH_STRT    = 1 << 6          # CTLR: start the erase or the programming
FLASH_FTPG    = 1 << 16         # CTLR: fast page programming mode
FLASH_FTER    = 1 << 17         # CTLR: fast page erase mode
FLASH_BUFLOAD = 1 << 18         # CTLR: take the latched word into the page buffer
FLASH_BUFRST  = 1 << 19         # CTLR: clear the page buffer
FLASH_BSY     = 1 << 0          # STATR: busy
FLASH_MAP = 0x08000000          # where the controller sees the flash; it is
                                # also at 0, where the program runs and reads

# The disc is the flash from DISC_LO up to DISC_HI. A block is one page of
# the flash: the chip erases and programs 256 bytes at a time, nothing less.
# The kernel is below DISC_LO.
DISC_LO  = 0x4000
DISC_HI  = 0xF800               # the end of the flash, 62 KiB
DISC_BLK = 256

# Port D, chapter 7
GPIOD_BASE  = 0x40011400
GPIOD_CFGLR = 0x00              # 7.3.1.1 four bits a pin: CNF[1:0], MODE[1:0]
GPIOD_BSHR  = 0x10              # 7.3.1.4 bit set/reset register (low half sets)

# USART1, chapter 14
USART1_BASE = 0x40013800
USART_STATR = 0x00              # 14.8.1 status
USART_DATAR = 0x04              # 14.8.2 data
USART_BRR   = 0x08              # 14.8.3 baud rate (USARTDIV in 1/16ths)
USART_CTLR1 = 0x0C              # 14.8.4 control 1
USART_CTLR2 = 0x10              # 14.8.5 control 2 (stop bits)
USART_CTLR3 = 0x14              # 14.8.6 control 3
USART_RXNE  = 1 << 5            # STATR: a received byte waits
USART_TXE   = 1 << 7            # STATR: the data register can take a byte
USART_RE    = 1 << 2            # CTLR1: receiver on
USART_TE    = 1 << 3            # CTLR1: transmitter on
USART_UE    = 1 << 13           # CTLR1: USART on

# CSR numbers. bronzebeard takes a CSR number as a signed 12-bit value, so one
# above 0x7FF is written as number - 0x1000.
CSR_MSTATUS = 0x300
CSR_MTVEC   = 0x305
CSR_MEPC    = 0x341
CSR_MCAUSE  = 0x342

# Set up the clock, the console's pins and USART1.
serial_init:
    # One flash wait state is required above 15 MHz (18.3.1); it must be set
    # before the clock goes up, or instruction fetches are corrupted.
    li t0, FLASH_R_BASE
    li t1, 1
    sw t1, FLASH_ACTLR(t0)

    # HCLK = HSI = 24 MHz: the whole register to 0 (HSI, no prescaler).
    li t0, RCC_BASE
    sw zero, RCC_CFGR0(t0)

    # clocks for USART1 and port D
    lw t1, RCC_PB2PCENR(t0)
    li t2, RCC_USART1EN | RCC_IOPDEN
    or t1, t1, t2
    sw t1, RCC_PB2PCENR(t0)

    # 115200 baud, 8N1, no flow control; receiver and transmitter on
    li t0, USART1_BASE
    li t1, CPU_FREQ // BAUD_RATE
    sw t1, USART_BRR(t0)
    sw zero, USART_CTLR2(t0)
    sw zero, USART_CTLR3(t0)
    li t1, USART_RE | USART_TE | USART_UE
    sw t1, USART_CTLR1(t0)

    # PD5 = TX: alternate function push-pull output (CNF 10, MODE 01).
    # PD6 = RX: input with pull-up (CNF 10, MODE 00, output latch 1). The
    # pull-up keeps a floating PD6 from picking up PD5 while the WCH-LinkE
    # powers up. The latch is set first, so PD6 never passes pull-down.
    li t0, GPIOD_BASE
    li t1, 1 << 6
    sw t1, GPIOD_BSHR(t0)
    lw t1, GPIOD_CFGLR(t0)
    li t2, ~((0xF << 20) | (0xF << 24))
    and t1, t1, t2
    li t2, (0b1001 << 20) | (0b1000 << 24)
    or t1, t1, t2
    sw t1, GPIOD_CFGLR(t0)
    ret

# Send the character in a0.
serial_putc:
    li t0, USART1_BASE
serial_putc1:
    lw t1, USART_STATR(t0)
    andi t1, t1, USART_TXE
    beqz t1, serial_putc1
    sb a0, USART_DATAR(t0)
    ret

# Wait for a character; return it in a0.
serial_getc:
    li t0, USART1_BASE
serial_getc1:
    lw t1, USART_STATR(t0)
    andi t1, t1, USART_RXNE
    beqz t1, serial_getc1
    lbu a0, USART_DATAR(t0)
    ret

# Has a character come? a0 = 1 and the character is taken, or a0 = 0.
serial_poll:
    li t0, USART1_BASE
    lw a0, USART_STATR(t0)
    andi a0, a0, USART_RXNE
    beqz a0, serial_poll1
    lbu a0, USART_DATAR(t0)     # take it: reading the data register clears RXNE
    li a0, 1
serial_poll1:
    ret

# Unlock the flash controller, for programming and for the page modes. It
# stays unlocked.
disc_init:
    li t0, FLASH_R_BASE
    li t1, FLASH_KEY1
    li t2, FLASH_KEY2
    sw t1, FLASH_KEYR(t0)
    sw t2, FLASH_KEYR(t0)
    sw t1, FLASH_MODEKEYR(t0)
    sw t2, FLASH_MODEKEYR(t0)
    ret

# Write one block of the disc: erase its page, program it (18.4.5: FTPG,
# BUFRST, 64 times a word and BUFLOAD, the address, STRT), and read it back.
# The core stands still while the controller is busy, about 3 ms each time.
#   a0 = the address of the block: DISC_LO ... DISC_HI - DISC_BLK, a multiple
#        of DISC_BLK
#   a2 = the 256 bytes, in RAM, on a cell boundary
# Returns a0 = 0 if the flash now holds them, 1 if not. Nothing is written if
# a0 or a2 is not as above: the kernel cannot be reached from here.
# Uses t0-t2 and a2-a5.
disc_write:
    li t0, DISC_LO
    bltu a0, t0, disc_write9
    li t0, DISC_HI
    bgeu a0, t0, disc_write9
    andi t0, a0, DISC_BLK - 1
    bnez t0, disc_write9
    andi t0, a2, 3
    bnez t0, disc_write9
    li t0, FLASH_R_BASE
    li a5, FLASH_MAP
    add a5, a5, a0              # a5 = the page, as the controller sees it
disc_write1:
    lw t1, FLASH_STATR(t0)
    andi t1, t1, FLASH_BSY
    bnez t1, disc_write1
    li t1, FLASH_FTER           # erase the page
    sw t1, FLASH_CTLR(t0)
    sw a5, FLASH_ADDR(t0)
    li t1, FLASH_FTER | FLASH_STRT
    sw t1, FLASH_CTLR(t0)
disc_write2:
    lw t1, FLASH_STATR(t0)
    andi t1, t1, FLASH_BSY
    bnez t1, disc_write2
    li t1, FLASH_FTPG           # program it: first clear the page buffer
    sw t1, FLASH_CTLR(t0)
    li t1, FLASH_FTPG | FLASH_BUFRST
    sw t1, FLASH_CTLR(t0)
disc_write3:
    lw t1, FLASH_STATR(t0)
    andi t1, t1, FLASH_BSY
    bnez t1, disc_write3
    mv a3, a5                   # a3 = where the next word goes
    li a4, DISC_BLK // 4        # a4 = words still to load
disc_write4:
    lw t2, 0(a2)
    sw t2, 0(a3)                # latch the word at its address in the flash
    li t1, FLASH_FTPG | FLASH_BUFLOAD
    sw t1, FLASH_CTLR(t0)       # and take it into the page buffer
disc_write5:
    lw t1, FLASH_STATR(t0)
    andi t1, t1, FLASH_BSY
    bnez t1, disc_write5
    addi a2, a2, 4
    addi a3, a3, 4
    addi a4, a4, -1
    bnez a4, disc_write4
    sw a5, FLASH_ADDR(t0)
    li t1, FLASH_FTPG | FLASH_STRT
    sw t1, FLASH_CTLR(t0)       # program the page from the buffer
disc_write6:
    lw t1, FLASH_STATR(t0)
    andi t1, t1, FLASH_BSY
    bnez t1, disc_write6
    sw zero, FLASH_CTLR(t0)     # the page modes off
    addi a2, a2, -DISC_BLK      # read it back
    li a4, DISC_BLK // 4
disc_write7:
    lw t1, 0(a0)
    lw t2, 0(a2)
    bne t1, t2, disc_write9
    addi a0, a0, 4
    addi a2, a2, 4
    addi a4, a4, -1
    bnez a4, disc_write7
    li a0, 0
    ret
disc_write9:
    li a0, 1
    ret

# Interrupts off, and every exception to `trap` through the vector table.
trap_init:
    csrrci zero, 8, CSR_MSTATUS         # MIE = 0
    li t0, 3                            # mtvec: table at 0, MODE0 = 1 (entry =
    csrrw zero, t0, CSR_MTVEC           # base + 4 * number), MODE1 = 1 (addresses)
    ret

# Every exception lands here: print T, mcause and mepc in hex on the console
# and hang, so the terminal says what went wrong and where. On this chip a
# misaligned lw or sw is an exception (mcause 4 and 6).
align 4
trap:
    li t0, USART1_BASE
    li t2, 'T'
trap1:
    lw t1, USART_STATR(t0)
    andi t1, t1, USART_TXE
    beqz t1, trap1
    sw t2, USART_DATAR(t0)
    csrrs a1, zero, CSR_MCAUSE          # the first value to print
    li a3, 2                            # two values
trap2:
    li a2, 8                            # of eight hex digits
trap3:
    lw t1, USART_STATR(t0)
    andi t1, t1, USART_TXE
    beqz t1, trap3
    srli t2, a1, 28                     # the top four bits
    addi t2, t2, 48                     # '0'..'9'
    li t1, 57
    ble t2, t1, trap4
    addi t2, t2, 7                      # 'A'..'F'
trap4:
    sw t2, USART_DATAR(t0)
    slli a1, a1, 4
    addi a2, a2, -1
    bnez a2, trap3
    li t2, 32                           # a blank
trap5:
    lw t1, USART_STATR(t0)
    andi t1, t1, USART_TXE
    beqz t1, trap5
    sw t2, USART_DATAR(t0)
    csrrs a1, zero, CSR_MEPC            # the second value
    addi a3, a3, -1
    bnez a3, trap2
trap6:
    j trap6
