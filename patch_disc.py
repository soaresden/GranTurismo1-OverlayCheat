"""Gran Turismo (PS1, PAL SCES-00984): add the overlay cheat menu to your disc image.

    python patch_disc.py "Gran Turismo.chd"                      -> "Gran Turismo [Cheat].bin/.cue"
    python patch_disc.py "Gran Turismo.cue" "GT cheat.bin"
    python patch_disc.py --exe GTMENU.EXE GTMENU.patched.EXE     (one extracted executable)

The input can be the stock disc or a disc already modded in other files (the MX-5 mod, for
instance): only GTOS.EXE, GTMENU.EXE and GTMAIN.EXE change, at their place on the disc. Each must
be the original one (checked by SHA-1). Python 3 only, nothing to install.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gt1cheat import patcher  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('src', help='.chd, .cue or .bin of Gran Turismo PAL (SCES-00984)')
    ap.add_argument('dst', nargs='?', help='output .bin (a .cue is written next to it)')
    ap.add_argument('--exe', metavar='NAME', help='patch one extracted executable (GTOS.EXE, GTMENU.EXE, GTMAIN.EXE)')
    a = ap.parse_args()
    try:
        if a.exe:
            data = open(a.src, 'rb').read()
            out = patcher.patch_exe(a.exe.upper(), data)
            open(a.dst or a.src + '.patched', 'wb').write(out)
            print('written', a.dst or a.src + '.patched')
            return
        dst = a.dst or os.path.splitext(a.src)[0] + ' [Cheat].bin'
        if not dst.lower().endswith('.bin'):
            dst += '.bin'
        patcher.patch_disc(a.src, dst, lambda i, n: print('\r%3d %%' % (100 * i // n), end='', flush=True))
        print('\rwritten %s (+ .cue)' % dst)
    except (patcher.PatchError, ValueError, OSError) as e:
        sys.exit('error: %s' % e)


if __name__ == '__main__':
    main()
