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


def patch_exe(name, data, check=True):
    """The executable `name` ('GTMAIN.EXE', 'GTMENU.EXE' or 'GTOS.EXE') with the cheat; same size.

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
    ext = payload.STUBS[name] + (payload.PIECES[e['piece']][1] if e['piece'] is not None else b'')
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


def patch_disc(src, dst, progress=None):
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
        new[name] = patch_exe(name, d.read(name))
    d.write_bin(dst, new, progress)
    return new
