# fig-FORTH for RISC-V
#
#   make          assemble figforth.bin (and figforth.labels, the addresses)
#   make test     assemble, then run every word in the emulator, and type at it
#   make flash    program the chip through a WCH-LinkE and restart it
#   make term     the console: 115200 baud, Enter sends CR, Ctrl-A Ctrl-X quits
#   make listing  write listings.asm again from tools/words.py
#   make test-board   type the tests at the real board (quit the console
#                 first; screens 40 and 41 of the disc are written over)
#   make put-assembler   put tools/forth-assembler.f on screens 42 to 45 of
#                 the board's disc (they must be empty); then  42 LOAD

TERMINAL ?= /dev/ttyACM0

figforth.bin: figforth.asm listings.asm board.asm
	bronzebeard -i . -l figforth.labels -o figforth.bin figforth.asm

listings.asm: tools/words.py tools/listing.py tools/header.py
	python3 tools/listing.py

.PHONY: test flash term clean listing test-board put-assembler

listing:
	python3 tools/listing.py

test-board: figforth.bin
	python3 tools/board_test.py $(TERMINAL)

put-assembler:
	python3 tools/put_screens.py tools/forth-assembler.f 42 $(TERMINAL)

test:
	python3 tests/test_nucleus.py
	python3 tests/test_listings.py

flash: figforth.bin
	minichlink -w figforth.bin flash -b

term:
	picocom -b 115200 $(TERMINAL)

clean:
	rm -f figforth.bin figforth.labels
