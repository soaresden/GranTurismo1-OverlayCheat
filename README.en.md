# Gran Turismo (PS1) — overlay cheat menu

🇫🇷 [Version française](README.md)

A patch for **Gran Turismo** (PlayStation, European version **SCES-00984**): hold **SELECT**
(or press **L1 + R1 + L2 + R2** together) and a small menu shows up over the game, with two
options:

1. **FREEZE TIMER** — stops the clock of the **licence tests**;
2. **MONEY** — changes the credits **live** (adjustable step, maximum, zero).

The patch only touches the game's executables (`GTOS.EXE`, `GTMENU.EXE`, `GTMAIN.EXE`) and holds
no game data: it works on the original disc **and** on a disc already modded in other files
(for instance the same author's MX-5 mod, which leaves these files alone).

## Controls (pad 1)

Two ways to open the `GT1 CHEAT` menu, at the top of the screen:

- **hold SELECT**: the menu appears after a short moment and goes away on release;
- **press L1 + R1 + L2 + R2 together**: the menu opens and **stays open**; **START** (or the four
  shoulder buttons again) closes it. Use this one in **Batocera / RetroArch**, where SELECT is
  the hotkey button: while it is held the game receives nothing, and SELECT + a button triggers
  the emulator's shortcuts.

While the menu is open, the game gets no input from the pad.

| Button | FREEZE TIMER line | MONEY line |
|---|---|---|
| ↑ / ↓ | change line | change line |
| ← / → | ON / OFF | − / + the step (held: repeat) |
| ✕ / ○ | ON / OFF | |
| R1 / L1 | | step × 10 / ÷ 10 (1 to 10,000,000) |
| △ | | 99,999,999 (the game's maximum) |
| □ | | 0 |

- **FREEZE TIMER ON**: in a licence test, the clock stops. If it was already ON at the start,
  it stops at **0:00.040** (right after the start): a licence whose clock stays at 0 never
  ends. The choice is kept from screen to screen, until the console is switched off.
- **MONEY**: the credits change at once (garage display, dealers…).
- A **short** press of SELECT (no other button) is given back to the game on release.

Tried in PCSX-Redux with the PAL BIOS SCPH-5502: menu on the city map and in a licence,
money updated on screen, licence B-1 passed with the clock stopped (*YOU WIN GOLD*, 0:00.059).
L1 + R1 + L2 + R2 on the city map: the menu stays open, △ gives 99,999,999, START closes it,
SELECT still works.

## Applying the patch

### With the script (recommended)

Python 3, nothing to install:

```bash
python patch_disc.py "Gran Turismo.chd"            # -> "Gran Turismo [Cheat].bin" + .cue
python patch_disc.py "Gran Turismo.cue" "GT cheat.bin"
```

The input can be a `.chd`, a `.cue` or a `.bin`; each executable is checked (SHA-1) before
it is changed.

### With a PPF / xdelta patch (`patch/` folder)

- `Gran Turismo (Europe) [Overlay Cheat].ppf`: apply it to the `.bin` (2352-byte sectors,
  single track). It only touches the sectors of the three executables, so it also applies to
  a disc already modded in other files.
- `Gran Turismo (Europe) [Overlay Cheat].xdelta`: for the original `.bin` only (xdelta checks
  its source).

Expected original `.bin` (one MODE2/2352 track, 691,652,640 bytes, as `patch_disc.py` /
chdman write it from the CHD): SHA-1 `1da2e8b50b6f506335b73d84223db2277f843e3f`.
Result: SHA-1 `9192f566ae6916e89ba96d5415999b0a4c3046b8` (build 1FE1CB19).

## How it works

Gran Turismo's executables are packed ("PSLZ") and unpacked in place by a small loader at
their entry point. That loader first copies itself, with its header, right after the end of
the unpacked code, then unpacks and jumps to the game (0x80010000).

The patch changes two words of that header and nothing else of the game's code:

- **+0x14** (bytes copied) is enlarged: the copy also takes a small **stub** written in the
  free bytes (zeros, never read) after the loader in the file;
- **+0x18** (jump address) points at that stub instead of 0x80010000.

The game's packed code is left as it is. Once the game is unpacked, the stub:

1. copies its piece of the **resident block** to 0x8000F000 (low RAM, free: the BIOS kernel
   heap ends near 0x8000E500). The block (≈ 2.7 KB) does not fit in a single file: the first
   piece comes from `GTOS.EXE` (run at start-up, before the menus), the second from
   `GTMENU.EXE`;
2. checks that the block is complete (magic word + CRC of the build at its start, another
   magic word at its end), then calls `cheat_boot`, which redirects three `jal` of the game
   after checking they are the expected ones;
3. flushes the instruction cache (A0:44, as the loader does) and jumps to the game.

`GTMAIN.EXE` (races, licences) only has a stub: it uses the block already in memory. If the
block is missing or from another build (a demo run before the menus, a save state from
another build), the stub leaves the game untouched.

The three redirected `jal` (the game calls our function, which calls the game's):

| | GTMAIN.EXE | GTMENU.EXE | role |
|---|---|---|---|
| pad copy | 0x8007A92C → memcpy 0x8007BD10 | 0x80041144 → memcpy 0x80045460 | once per frame: reads SELECT, runs the menu, hides the pad from the game |
| the frame's DrawOTag | 0x8007021C → 0x80086F2C | 0x80036978 → 0x8004B3A4 | once the frame is drawn (DrawSync), draws the menu over it |
| race clock | 0x80052D48 → 0x80057EB4 | — | skipped in a licence while FREEZE TIMER is on |

Useful addresses found (static analysis, checked in PCSX-Redux):

| Address | Role |
|---|---|
| 0x800C0940 / 0x800C09C0 (GTMAIN), 0x800A86D0 / 0x800A8750 (GTMENU) | pad buffers (libpad `PadInitDirect`) / the copy the game reads |
| 0x80093BC8 (GTMAIN) | race clock (ms): +40 per frame at 25 fps (+20 at 50) |
| 0x800CB645 (GTMAIN) | game mode, 4 = licence test (table 0x8008BC68, case 0x80027E80 → "license result menu") |
| 0x800C4A94 (GTMAIN), 0x8009B874 (GTMENU) | credits (u32), "GTos" status block + 0x44, passed between executables through SPU RAM |
| 0x8000F000…0x8000FA8B | resident block (the cheat's code) |
| 0x8000FF80 | cheat state (FREEZE TIMER, line, step…), kept across executables |

Drawing: TILE primitives sent straight to the GPU (GP0) after `DrawSync`, the project's 5×7
font (`src/font.py`), doubled at 640 wide / 480 lines, the game's draw mode restored
afterwards. Pad: bits once inverted, SELECT = 0x0001 (byte 2 bit 0 of the raw data), as in the
game's own pad code (0x8007A7D0).

## Known limits

- Pad 1 only (with a multitap: its port A).
- While the menu is open, the game does not see the pad.
- The menu only exists once the **Gran Turismo mode** has been opened at least once since
  power on: the second piece of the code comes from `GTMENU.EXE`. The title screen and the
  Arcade mode menus have no menu; Arcade races have it, after a visit to GT mode.
- Menus in 640×480 interlaced: the game redraws the whole screen every frame and the menu is
  drawn after it; on an emulator that outputs line by line (Beetle) or on a console, a slight
  flicker is possible.
- While the menu is shown, the CPU waits for each frame to be drawn (the game may slow down a
  little, only while the menu is shown).
- FREEZE TIMER only acts in licence tests (mode 4), not in races.

## Building from source

- `src/cheat.c`, `src/start.S`, `src/stub.S`, `src/payload.ld`, `src/font.py`: the code;
- `gt1cheat/exes.py`: every game address; `gt1cheat/patcher.py`: the patch;
  `gt1cheat/check.py`: checks of a patched executable (the game's loader is replayed in
  Python: same unpacked code, copy = header + loader + stub, jump to the stub, original sites
  in place);
- `python build.py [--list]`: compiles (MIPS GCC `mipsel-none-elf-*` from PSn00bSDK, or
  `mips-linux-gnu-*`), checks (`src/verify.py`: R3000 load delays, no jump in a delay slot,
  mfhi/mflo, jump targets, saved/restored registers, tables) and writes `gt1cheat/payload.py`;
- `python make_release.py --src <image> --test <folder> --patches`: test disc, PPF and xdelta
  (xdelta3), each one checked.

The PSLZ format (header layout) comes from pez2k's GT1ExecutableTool; the CHD reader and the
sector writing (EDC/ECC) come from the same author's MazdaMx5NDRF project.

## License

GPL-3.0 (see `LICENSE`). No game data is provided: you need your own disc.
