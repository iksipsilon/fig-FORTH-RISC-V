#!/usr/bin/env python3
"""Test the real board, over the serial port.

    python3 tools/board_test.py [port]      (or: make test-board)

The port is /dev/ttyACM0 if none is given. Nothing else may have it open:
quit picocom first. The board must hold the current build (make flash).

Two parts. First the lines of tests/test_listings.py are typed at the board,
without those tests that reach into the emulator's flash or pull its power.
Then a session with the disc and the editor: a screen is written, the chip
is reset with minichlink -b, and the screen must still be there.

What it does to the board: COLD before every test, so words defined at the
terminal are gone; and SCREENS 40 AND 41 OF THE DISC ARE WRITTEN OVER.
"""
import os, select, sys, termios, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"

fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = 0; a[1] = 0; a[3] = 0
a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
a[4] = a[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, a)

def read_quiet(quiet=0.25, limit=8.0):
    out = b""; last = time.time(); end = last + limit
    while time.time() < end and time.time() - last < quiet:
        if select.select([fd], [], [], 0.02)[0]:
            out += os.read(fd, 4096); last = time.time()
    return out

class Board:                      # stands in for the emulated machine
    pass

def hw_keys(e, data):
    for b in data:                # one key at a time: the chip has no input buffer
        os.write(fd, bytes([b])); time.sleep(0.003)
    return read_quiet()

def fresh():
    read_quiet(0.1)
    hw_keys(None, b"\r")          # end any line that is open
    out = hw_keys(None, b"[ COLD\r")
    assert out.endswith(b"fig-FORTH RISC-V\r\n"), "COLD answered %r" % out
    return Board()

src = open(os.path.join(ROOT, "tests", "test_listings.py")).read()
# the tests that reach into the emulator's flash are left out; the disc and
# the editor are tried below, through the terminal
src = src[:src.index("# ---------------------------------------------------------------- the disc")] \
    + src[src.index("# ---------------------------------------------------------------- cold and warm"):]
src = src[:src.index('e = t([": T 5 ;", "HEX"], "")')] + src[src.index("# ---------------------------------------------------------------- the image"):]
src = src.replace("copy.deepcopy(BOOTED)", "fresh()")
a = src.index("def keys(e, data):"); b = src.index("def say(e, line):")
src = src[:a] + "keys = hw_keys\n\n" + src[b:]
src = src.replace('check("cold start", bytes(BOOTED.uart_out)', 'check("cold start", b"\\r\\nfig-FORTH RISC-V\\r\\n"')
src = src.replace("sys.exit(1 if failed else 0)", "")
g = {"__name__": "board", "__file__": os.path.join(ROOT, "tests", "test_listings.py"),
     "hw_keys": hw_keys, "fresh": fresh}
exec(compile(src, "test_listings(board)", "exec"), g)
check, say = g["check"], g["say"]

# ---------------------------------------------------------------- the disc, on the chip
import subprocess
SCR = ["( A TEST SCREEN )", ": SQ DUP * ;", "7 SQ ."]
def listing(n, lines):
    lines = lines + [""] * (16 - len(lines))
    return "\r\nSCR # %d " % n + "".join("\r\n%3d %s" % (i, l) for i, l in enumerate(lines)) + "\r\nOK\r\n"
def shown(text, n):
    return "\r\n " + text.ljust(65) + "%d OK\r\n" % n

e = fresh()
check("EDITOR", say(e, "EDITOR"), "OK\r\n")
check("40 CLEAR", say(e, "40 CLEAR"), "OK\r\n")
for i, l in enumerate(SCR):
    check("P", say(e, "%d P %s" % (i, l)), "OK\r\n")
check("FLUSH", say(e, "FLUSH"), "OK\r\n")
check("40 LIST", say(e, "40 LIST"), listing(40, SCR))
check("40 LOAD", say(e, "40 LOAD"), "49 OK\r\n")

r = subprocess.run(["minichlink", "-b"], capture_output=True, text=True)   # reset: the RAM starts again
out = read_quiet(0.6)
check("the reset", out.endswith(b"fig-FORTH RISC-V\r\n"), True)
check("after a reset: SQ is gone", say(e, "SQ"), "SQ? \r\n")
check("after a reset: 40 LIST", say(e, "40 LIST"), listing(40, SCR))
check("after a reset: 40 LOAD", say(e, "40 LOAD"), "49 OK\r\n")
check("EDITOR", say(e, "EDITOR"), "OK\r\n")
check("40 41 COPY", say(e, "40 41 COPY"), "OK\r\n")
check("41 LIST", say(e, "41 LIST"), listing(41, SCR))
check("TOP F DUP", say(e, "TOP F DUP"), shown(": SQ DUP_ * ;", 1))
check("C  ROT", say(e, "C  ROT"), shown(": SQ DUP ROT_ * ;", 1))
check("2 D", say(e, "2 D"), "OK\r\n")
check("FLUSH", say(e, "FLUSH"), "OK\r\n")
check("184 BLOCK", say(e, "184 BLOCK"), "BLOCK? DISC RANGE ?\r\n")
check("BLOCK-WRITE refuses the kernel", say(e, "FIRST 4 + 0 BLOCK-WRITE ."), "1 OK\r\n")
print("%d checks, %d failed, on the board" % (g["count"], g["failed"]))
sys.exit(1 if g["failed"] else 0)
