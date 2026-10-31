"""Apply the cheat to GTMAIN.EXE / GTMENU.EXE, or to a whole disc image."""
import hashlib
import os
import struct

from . import exes, pslz

try:
    from . import payload
except ImportError:                       # not built yet (python build.py)
    payload = None


class PatchError(Exception):
    pass


# options (the page's switches): the word at offset 8 of the resident block (src/start.S, OPTIONS
# of src/cheat.c), in the first piece (GTOS.EXE); 0 = the menu, as the release patches
NO_MENU, MONEY, FREEZE = 0x001, 0x004, 0x100


def options_word(menu=True, freeze=False, money=False):
    """The options word: menu (SELECT / L1 + R1 + L2 + R2), FREEZE TIMER on from power on, credits
    kept at 99,999,999."""
    return (0 if menu else NO_MENU) | (FREEZE if freeze else 0) | (MONEY if money else 0)


def piece(k, options=0):
    """Piece k of the resident block, with the options word (in piece 0)."""
    b = payload.PIECES[k][1]
    if k == 0 and options:
        b = b[:8] + struct.pack('<I', options) + b[12:]
    return b


def patch_exe(name, data, check=True, options=0):
    """The executable `name` ('GTMAIN.EXE', 'GTMENU.EXE' or 'GTOS.EXE') with the cheat; same size.
    options: options_word().

    Only the PSLZ header (+0x14, +0x18) and zero bytes after the loader change; the packed
    game code is left as it is."""
    if payload is None:
        raise PatchError('gt1cheat/payload.py missing: run build.py first')
    e = exes.EXES[name]
    if check and hashlib.sha1(data).hexdigest() != e['sha1']:
        raise PatchError('%s: not the executable of Gran Turismo PAL SCES-00984 (or already patched)' % name)
    x = pslz.Exe(data)
    if x.loader_size != exes.LOADER_SIZE or x.jump != exes.GAME_ENTRY or x.loader != e['loader']:
        raise PatchError('%s: unexpected PSLZ header (already patched?)' % name)
    ext = payload.STUBS[name] + (piece(e['piece'], options) if e['piece'] is not None else b'')
    start = x.hdr + exes.LOADER_SIZE
    copied = x.hdr + ((exes.LOADER_SIZE + len(ext) + 15) & ~15)   # the loader copies 16-byte blocks
    if copied > len(data):
        raise PatchError('%s: %d bytes of stub, room for %d' % (name, len(ext), len(data) - start))
    if any(data[start:copied]):
        raise PatchError('%s: the bytes after the loader are not free' % name)
    d = bytearray(data)
    d[start:start + len(ext)] = ext
    struct.pack_into('<I', d, x.hdr + 0x14, exes.LOADER_SIZE + len(ext))
    struct.pack_into('<I', d, x.hdr + 0x18, x.loader + exes.LOADER_SIZE)
    return bytes(d)


def patch_disc(src, dst, progress=None, options=0):
    """Write dst (.bin + .cue) = the image src (.chd, .cue or .bin) with the three executables
    patched (GTOS.EXE, GTMENU.EXE, GTMAIN.EXE)."""
    from . import disc
    d = disc.Disc(src)
    if os.path.abspath(d.path) == os.path.abspath(dst):
        raise PatchError('the output must be another file than the input')
    new = {}
    for name in exes.EXES:
        if name not in d.files:
            raise PatchError('%s not on the disc: is it Gran Turismo PAL (SCES-00984)?' % name)
        new[name] = patch_exe(name, d.read(name), options=options)
    d.write_bin(dst, new, progress)
    return new
