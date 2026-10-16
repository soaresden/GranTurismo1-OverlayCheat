"""Start PCSX-Redux on a disc with drive.lua (polls out/cmd.txt), for tests driven by cmd.py.

    python tools/emu/launch.py "TEST_CHEAT/Gran Turismo [Cheat].cue" [--sony] [--interp] [--debugger]
    python tools/emu/cmd.py $'hold SELECT 60\nwait 30\nshot menu\nr32 0x8009b874'

PCSX_REDUX: path of pcsx-redux(.exe) (else the Resident Evil 1 Hotkey project's copy);
PSX_BIOS: BIOS for --sony (else OpenBIOS, PCSX-Redux's own). --interp: interpreter (needed for
breakpoints, and for RAM writes from Lua to reach code already compiled by the dynarec).
cmd.py commands: press/hold BTN frames, wait n, shot name, vram name, dump name, save name,
load path, r32 addr, w8/w32 addr value, lua <code>, quit. Output in tools/emu/out/.
Adapted from the Resident Evil 1 Hotkey project's harness (same author).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EMU = os.environ.get('PCSX_REDUX', r'D:\DOCS\Documents\GitHub\Resident Evil 1 Hotkey\tools\redux\pcsx-redux.exe')
BIOS = os.environ.get('PSX_BIOS', r'D:\DOCS\Documents\a-Emulation\Batocera\PACK FULL BIOS BATOCERA V42 - sys modules SHADPS4 -MINICAKETV\bios\scph5502.bin')
out = os.path.join(HERE, 'out')
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    try:
        os.remove(os.path.join(out, f))
    except OSError:
        pass
env = dict(os.environ, HARNESS_SCRIPT=os.path.join(HERE, 'drive.lua'), HARNESS_OUT=out,
           CMD_FILE=os.path.join(out, 'cmd.txt'))
args = [EMU, '-cli', '-stdout', '-run', '-iso', os.path.abspath(sys.argv[1]), '-dofile', os.path.join(HERE, 'harness.lua')]
if '--interp' in sys.argv:
    args.insert(3, '-interpreter')
if '--debugger' in sys.argv:
    args.insert(3, '-debugger')
if '--sony' in sys.argv:
    args += ['-bios', BIOS]
with open(os.path.join(out, 'emu.log'), 'w') as log:
    subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=HERE)
