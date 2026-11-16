# fig-FORTH for RISC-V
#
#   make          assemble figforth.bin (and figforth.labels, the addresses)
#   make test     assemble, then run every word in the emulator
#   make flash    program the chip through a WCH-LinkE and restart it
#   make term     the console: 115200 baud, Enter sends CR, Ctrl-A Ctrl-X quits

TERMINAL ?= /dev/ttyACM0

figforth.bin: figforth.asm listings.asm board.asm
	bronzebeard -i . -l figforth.labels -o figforth.bin figforth.asm

.PHONY: test flash term clean

test:
	python3 tests/test_nucleus.py

flash: figforth.bin
	minichlink -w figforth.bin flash -b

term:
	picocom -b 115200 $(TERMINAL)

clean:
	rm -f figforth.bin figforth.labels
