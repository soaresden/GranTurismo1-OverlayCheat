"""Static checks of a patched executable against the original one.

  - same size; the only bytes that change are the PSLZ header's +0x14 / +0x18 and the zero
    bytes after the loader, which receive the stub and its piece of the resident block;
  - the game's PSLZ loader, run here as it runs on the console (pslz.run_loader), unpacks the
    same code as from the original (the packed code is not touched) and stops where it stops
    for the original; its copy holds header + loader + stub + piece, and it jumps to the stub;
  - each redirected site of the unpacked code holds the `jal` cheat_boot expects (else
    cheat_boot leaves the game alone), and the jal's target is the expected game function.
"""
import struct

from . import exes, pslz


def check_exe(name, orig, patched, payload):
    p = []
    e = exes.EXES[name]
    if len(orig) != len(patched):
        return ['%s: size changed' % name]
    xo, xp = pslz.Exe(orig), pslz.Exe(patched)
    ext = payload.STUBS[name] + (payload.PIECES[e['piece']][1] if e['piece'] is not None else b'')
    start = xo.hdr + exes.LOADER_SIZE
    allowed = set(range(xo.hdr + 0x14, xo.hdr + 0x1C)) | set(range(start, start + len(ext)))
    diff = [i for i in range(len(orig)) if orig[i] != patched[i]]
    bad = [i for i in diff if i not in allowed]
    if bad:
        p.append('%s: %d bytes changed outside the header words and the stub (first at %X)' % (name, len(bad), bad[0]))
    if patched[start:start + len(ext)] != ext:
        p.append('%s: stub bytes' % name)
    if xp.loader_size != exes.LOADER_SIZE + len(ext) or xp.jump != e['loader'] + exes.LOADER_SIZE:
        p.append('%s: PSLZ header words (+0x14 = %d, +0x18 = %08X)' % (name, xp.loader_size, xp.jump))
    if (xp.out_end, xp.in_end, xp.loader, xp.entry) != (xo.out_end, xo.in_end, xo.loader, xo.entry):
        p.append('%s: other header fields changed' % name)
    code_o, copy_o, jump_o, end_o = pslz.run_loader(orig)
    code_p, copy_p, jump_p, end_p = pslz.run_loader(patched)
    if code_o != code_p:
        p.append('%s: the unpacked code differs' % name)
    if end_o != end_p or end_o[0] != end_o[1]:
        p.append('%s: the loader stops elsewhere (%08X/%08X, original %08X/%08X)' % ((name,) + end_p + end_o))
    if jump_o != exes.GAME_ENTRY or jump_p != e['loader'] + exes.LOADER_SIZE:
        p.append('%s: jump %08X (original %08X)' % (name, jump_p, jump_o))
    if copy_p[:exes.LOADER_SIZE] != copy_o[:exes.LOADER_SIZE] and \
            copy_p[0x1C:exes.LOADER_SIZE] != copy_o[0x1C:exes.LOADER_SIZE]:
        p.append('%s: the copied loader differs' % name)
    if copy_p[exes.LOADER_SIZE:exes.LOADER_SIZE + len(ext)] != ext:
        p.append('%s: the loader does not copy the whole stub' % name)
    for site in e.get('sites', []):
        if not site:
            continue
        a, target = site
        w = struct.unpack_from('<I', code_p, a - exes.GAME_ENTRY)[0]
        if w != exes.jal(target):
            p.append('%s: %08X holds %08X, not jal %08X' % (name, a, w, target))
    for k in ('memcpy', 'drawsync', 'drawotag', 'tick'):
        f = e.get(k)
        if f:
            prologue = struct.unpack_from('<I', code_p, f - exes.GAME_ENTRY)[0]
            if k != 'memcpy' and prologue >> 16 not in (0x27BD, 0x3C02, 0x3C03):
                p.append('%s: %s at %08X does not start like a function (%08X)' % (name, k, f, prologue))
    return p
