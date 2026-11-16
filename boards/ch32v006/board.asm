# fig-FORTH for RISC-V: the WCH CH32V006 (WeAct Studio CH32V006F8U6)
#
# QingKe V2C core: RV32EC + Zmmul + Zicsr, 62 KiB flash, 8 KiB RAM, HSI 24 MHz.
# The console is USART1: TX = PD5, RX = PD6, 115200 baud, 8N1.
#
# This file is the first thing in the image. A board file must
#   - put whatever the chip needs at address 0 and make reset reach `boot`
#   - define RAM_BASE and RAM_SIZE
#   - implement serial_init, serial_putc, serial_getc, serial_poll and trap_init
# The routines are leaves: they use t0-t2 and a0 only, and no stack.
#
# The register addresses, the order of the writes and the reasons given for
# them come from the sixforths kernel (src/mcu.s, src/03-traps.s), where they
# were checked on this board. The section numbers are those of the CH32V00x
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
