Gran Turismo (PS1, PAL) - Overlay Cheat Menu v1.1
=================================================
by soaresden - https://github.com/soaresden/GranTurismo1-OverlayCheat

Hold SELECT (or press L1 + R1 + L2 + R2 together) and a small menu appears over the game:

  FREEZE TIMER   stops the clock of the licence tests
  MONEY          changes the credits live (adjustable step, maximum, zero)

Controls (pad 1)
----------------
Two ways to open the "GT1 CHEAT" menu:
  - hold SELECT: the menu appears after a short moment, and goes away on release;
  - press L1 + R1 + L2 + R2 together: the menu opens and stays open; START (or the four
    shoulder buttons again) closes it. Use this one in RetroArch / Batocera, where SELECT is
    often the hotkey button.
While the menu is open, the game does not receive the pad.

  Up / Down                     choose the line
  FREEZE TIMER line:
    Left / Right / Cross / Circle   ON / OFF
  MONEY line:
    Right / Left                + / - the step (held: repeats)
    R1 / L1                     step x10 / step /10 (from 1 to 10,000,000)
    Triangle                    99,999,999 (the game's maximum)
    Square                      0

- FREEZE TIMER ON: in a licence test the clock stops where it is. If it was already ON at the
  start, it stops at 0:00.040, right after the start (a licence test whose clock stays at 0
  never ends). Stop in the target zone and the gold is yours. The choice is kept until power
  off. It only acts in licence tests, not in races.
- A short press of SELECT (no other button) is given back to the game on release.
- The menu is there once Gran Turismo mode has been opened at least once since power on (the
  second half of the cheat's code comes with it): not on the title screen nor in the Arcade
  mode menus; Arcade races have it after a visit to GT mode.

Patching
--------
Patch the disc image (SCES-00984) with one of:
  Gran Turismo (Europe) [Overlay Cheat].ppf     (PPF 3.0, changed bytes only)
  Gran Turismo (Europe) [Overlay Cheat].xdelta  (xdelta3, original image only)

Source image: a single-track .bin, MODE2/2352:
  Gran Turismo (Europe) (En,Fr,De,Es,It).bin
  Size   691,652,640 bytes
  CRC32  DBA21C42
  SHA-1  1da2e8b50b6f506335b73d84223db2277f843e3f
Patched image:
  CRC32  A871244C
  SHA-1  9192f566ae6916e89ba96d5415999b0a4c3046b8

The PPF only touches 4 sectors of the three executables (GTOS.EXE, GTMENU.EXE, GTMAIN.EXE), so
it also applies to a disc already modded in other files.

For a .chd or .cue, the Python tool of the project (patch_disc.py, Python 3, nothing to
install) checks each executable (SHA-1) before changing it:
  python patch_disc.py "Gran Turismo.chd"

Tested
------
PCSX-Redux (BIOS SCPH-5502): menu on the city map, the licence list and during licence tests;
credits updated on screen (99,999,999); licence B-1 passed with the clock frozen ("YOU WIN
GOLD", 0:00.059); L1 + R1 + L2 + R2 keeps the menu open, START closes it.

How it works
------------
The game's executables are packed (PSLZ) and unpacked in place by a small loader. The patch
changes two words of the PSLZ header of each one: the loader also copies a small stub written
in the free bytes after it, and jumps to it once the game is unpacked. The stub copies its part
of the resident code to free low RAM (0x8000F000; the code does not fit in a single file, the
first half comes from GTOS.EXE, the second from GTMENU.EXE), then redirects three calls of the
game: the pad copy, the frame drawing (the menu is drawn over the frame with GPU primitives)
and, in GTMAIN.EXE, the race clock, skipped in licence tests while FREEZE TIMER is on. The
packed game code is not touched. Sources, addresses and notes: see the GitHub project.

Gran Turismo is a trademark of Sony Interactive Entertainment. Fan project, not affiliated with
Sony or Polyphony Digital. License: GPL-3.0.
