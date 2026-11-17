#!/usr/bin/env python3
"""Put a file of Forth source on screens of the board's disc, through the editor.

    python3 tools/put_screens.py FILE FIRST [port] [--force]
    make put-assembler        tools/forth-assembler.f on screens 42 to 45

Line 16k+n of the file goes on line n of screen FIRST+k. The lines are typed
at the board as you would type them: EDITOR, n CLEAR, n P text ..., FLUSH;
one key at a time, because the chip has no input buffer. Then each screen is
LISTed and compared with the file.

A screen line is 64 characters and nothing ends it, so a line of the file
may have 63 at most: a 64th would run into the first word of the next line.

The screens must be empty first (blanks, or flash that was never written);
the tool looks, and stops if they are not. --force writes over them. The
port is /dev/ttyACM0 if none is given; quit picocom first. Words defined at
the terminal are kept: there is no COLD.
"""
import os, select, sys, termios, time

args = [a for a in sys.argv[1:] if a != "--force"]
if len(args) not in (2, 3):
    raise SystemExit(__doc__)
FILE, FIRST = args[0], int(args[1])
PORT = args[2] if len(args) == 3 else "/dev/ttyACM0"
FORCE = "--force" in sys.argv[1:]

lines = open(FILE).read().rstrip("\n").split("\n")
for i, l in enumerate(lines):
    if len(l) > 63:
        raise SystemExit("%s line %d has %d characters; 63 at most" % (FILE, i + 1, len(l)))
    if any(not " " <= c <= "~" for c in l):
        raise SystemExit("%s line %d has a character that is not plain ASCII" % (FILE, i + 1))
screens = [lines[i:i + 16] for i in range(0, len(lines), 16)]
LAST = FIRST + len(screens) - 1
if FIRST < 1 or LAST > 45:
    raise SystemExit("screens %d to %d: the disc has screens 1 to 45 (0 cannot be loaded)" % (FIRST, LAST))

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

def say(line):
    """Type a line and Enter; returns what comes after the echo."""
    for b in line.encode() + b"\r":
        os.write(fd, bytes([b])); time.sleep(0.003)
    out = read_quiet().decode("latin-1")
    echo = line + " "
    if not out.startswith(echo):
        raise SystemExit("the board did not echo %r: %r" % (line, out))
    return out[len(echo):]

def must(line, want="OK\r\n"):
    out = say(line)
    if out != want:
        raise SystemExit("%r answered %r" % (line, out))

read_quiet(0.1)
os.write(fd, b"\r"); read_quiet()        # end any line that is open
must("[ FORTH DECIMAL")

# how many bytes of each screen are not blank and not erased flash
must(": ?USED ( scr -- n )  0 SWAP B/SCR * DUP B/SCR + SWAP", "\r\n")
must("  DO I BLOCK DUP B/BUF + SWAP DO I C@ DUP BL = SWAP 255 = OR 0= +", "\r\n")
must("  LOOP LOOP ;")
used = {}
for n in range(FIRST, LAST + 1):
    used[n] = int(say("%d ?USED ." % n).split()[0])
must("FORGET ?USED")
full = [n for n in used if used[n]]
if full and not FORCE:
    raise SystemExit("screens %s are not empty (%s bytes in use); nothing written. "
                     "LIST them, or say --force" % (full, [used[n] for n in full]))

must("EDITOR")
for k, scr in enumerate(screens):
    must("%d CLEAR" % (FIRST + k))
    for i, l in enumerate(scr):
        if l.strip():
            must("%d P %s" % (i, l))
    print("screen %d typed" % (FIRST + k))
must("FLUSH")
must("FORTH")

bad = 0
for k, scr in enumerate(screens):
    n = FIRST + k
    scr = [l.rstrip(" ") for l in scr] + [""] * (16 - len(scr))
    want = "\r\nSCR # %d " % n + "".join("\r\n%3d %s" % (i, l) for i, l in enumerate(scr)) + "\r\nOK\r\n"
    if say("%d LIST" % n) != want:
        bad += 1
        print("screen %d is not what the file says" % n)
print("%s: %d screens, %d to %d, %s" % (FILE, len(screens), FIRST, LAST,
      "written and read back" if not bad else "%d WRONG" % bad))
sys.exit(1 if bad else 0)
