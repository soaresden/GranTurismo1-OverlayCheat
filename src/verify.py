"""Static checks of the compiled cheat (run by build.py), with capstone.

R3000 rules checked on every instruction of the resident code and of both stubs:
  - load delay: the instruction after a load does not read the loaded register (also at the
    target of a branch whose delay slot holds a load);
  - no branch or jump in a delay slot;
  - mfhi / mflo: no mult / div / mthi / mtlo in the next two instructions;
  - every jal / j / branch target is code of the block (jalr: function pointers, checked below);
  - each function: the registers saved by the prologue are restored, from the same stack slots,
    before every jr $ra, and $sp is given back.
Tables: the exe table (EXES) and the hook table of cheat_boot hold the expected values.
Stubs: copy loop, the call of cheat_boot, FlushCache, jump to the game.
"""
import os
import struct

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS32, Cs

from gt1cheat import exes

md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
md.detail = False

LOADS = {0x20: 'lb', 0x21: 'lh', 0x22: 'lwl', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu', 0x26: 'lwr', 0x32: 'lwc2'}


def rs(w): return (w >> 21) & 31
def rt(w): return (w >> 16) & 31
def rd(w): return (w >> 11) & 31


def is_branch(w):
    op = w >> 26
    if op in (2, 3, 4, 5, 6, 7):
        return True
    if op == 1:
        return True                       # bltz / bgez / bltzal / bgezal
    if op == 0 and (w & 0x3F) in (8, 9):  # jr / jalr
        return True
    return False


def reads(w):
    """Registers an instruction reads."""
    op = w >> 26
    if w == 0:
        return set()
    if op == 0:
        f = w & 0x3F
        if f in (0, 2, 3):                # sll srl sra: rt
            return {rt(w)}
        if f in (8,):                     # jr
            return {rs(w)}
        if f == 9:
            return {rs(w)}
        if f in (0x10, 0x12):             # mfhi mflo
            return set()
        if f in (0x11, 0x13):             # mthi mtlo
            return {rs(w)}
        if f in (0x0C, 0x0D):             # syscall break
            return {2, 4} if f == 0x0C else set()
        return {rs(w), rt(w)}
    if op in (2, 3, 0x0F):
        return set()
    if op == 1:
        return {rs(w)}
    if op in (4, 5):
        return {rs(w), rt(w)}
    if op in (6, 7):
        return {rs(w)}
    if op in LOADS:
        return {rs(w)} | ({rt(w)} if op in (0x22, 0x26) else set())
    if op in (0x28, 0x29, 0x2A, 0x2B, 0x2E):   # stores
        return {rs(w), rt(w)}
    return {rs(w)}                         # immediates


def branch_target(w, pc):
    op = w >> 26
    if op in (2, 3):
        return (pc & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
    if op in (1, 4, 5, 6, 7):
        off = w & 0xFFFF
        if off & 0x8000:
            off -= 0x10000
        return pc + 4 + (off << 2)
    return None


def words(blob):
    return list(struct.unpack('<%dI' % (len(blob) // 4), blob[:len(blob) // 4 * 4]))


def check_code(ws, base, lo, hi, name, external=()):
    """ws: words from base; checks [lo, hi)."""
    p = []
    at = lambda a: ws[(a - base) // 4]
    for a in range(lo, hi, 4):
        w = at(a)
        nxt = at(a + 4) if a + 4 < hi else None
        if is_branch(w) and nxt is not None and is_branch(nxt):
            p.append('%s %08X: branch in a delay slot' % (name, a + 4))
        if (w >> 26) in LOADS and rt(w) != 0 and nxt is not None:
            if rt(w) in reads(nxt) and not ((nxt >> 26) in (0x22, 0x26) and (w >> 26) in (0x22, 0x26)):
                p.append('%s %08X: load delay (next instruction reads $%d)' % (name, a, rt(w)))
            # a load in a delay slot: the next executed instruction is the branch target
            prev = at(a - 4) if a > lo else 0
            if is_branch(prev):
                t = branch_target(prev, a - 4)
                if t is not None and lo <= t < hi and rt(w) in reads(at(t)):
                    p.append('%s %08X: load in delay slot, target reads $%d' % (name, a, rt(w)))
        if (w >> 26) == 0 and (w & 0x3F) in (0x10, 0x12):
            for k in (1, 2):
                if a + 4 * k < hi:
                    x = at(a + 4 * k)
                    if (x >> 26) == 0 and (x & 0x3F) in (0x11, 0x13, 0x18, 0x19, 0x1A, 0x1B):
                        p.append('%s %08X: mult/div within 2 of mfhi/mflo' % (name, a + 4 * k))
        t = branch_target(w, a)
        if t is not None and not (lo <= t < hi) and t not in external:
            p.append('%s %08X: target %08X outside the code' % (name, a, t))
    return p


def functions(sym, lo, hi):
    starts = sorted(a for n, a in sym.items() if lo <= a < hi and not n.startswith(('_', '.')))
    return [(s, (starts + [hi])[i + 1]) for i, s in enumerate(starts)]


def check_frames(ws, base, funcs, sym):
    p = []
    names = {a: n for n, a in sym.items()}
    at = lambda a: ws[(a - base) // 4]
    for lo, hi in funcs:
        frame = 0
        saved = {}
        w = at(lo)
        if w >> 16 == 0x27BD and w & 0x8000:      # addiu sp, sp, -N
            frame = 0x10000 - (w & 0xFFFF)
            a = lo + 4
            while a < hi:
                x = at(a)
                # sw of a callee-saved register ($s0-$s7, $fp, $ra) to the frame
                if x >> 26 == 0x2B and rs(x) == 29 and (16 <= rt(x) <= 23 or rt(x) in (30, 31)):
                    saved.setdefault(rt(x), x & 0xFFFF)
                a += 4
        for a in range(lo, hi, 4):
            if at(a) != 0x03E00008:
                continue
            # restore window: from the last call (or function start) up to the delay slot
            b = a
            while b > lo and not (at(b - 4) >> 26 == 3 or (at(b - 4) >> 26 == 0 and at(b - 4) & 0x3F == 9)):
                b -= 4
            body = [at(c) for c in range(b, a + 8, 4)]
            got = {rt(x): x & 0xFFFF for x in body if x >> 26 == 0x23 and rs(x) == 29}
            for r, off in saved.items():
                if r in (29,):
                    continue
                if got.get(r) != off:
                    p.append('%s: $%d saved at sp+%d not restored before jr $ra at %08X'
                             % (names.get(lo, hex(lo)), r, off, a))
            if frame and (0x27BD0000 | frame) not in body:
                p.append('%s: $sp not given back before jr $ra at %08X' % (names.get(lo, hex(lo)), a))
    return p


def disasm_listing(ws, base, lo, hi, sym):
    names = {}
    for n, a in sym.items():
        names.setdefault(a, n)
    out = []
    blob = struct.pack('<%dI' % len(ws), *ws)
    for i in md.disasm(blob[lo - base:hi - base], lo):
        if i.address in names:
            out.append('\n%s:' % names[i.address])
        out.append('%08x: %08x  %s %s' % (i.address, ws[(i.address - base) // 4], i.mnemonic, i.op_str))
    return '\n'.join(out) + '\n'


def check_all(block, pieces, stubs, sym, listing=False, out_dir=None):
    listing_ = listing
    p = []
    base = exes.RESIDENT
    ws = words(block)
    code_lo, code_hi = base + 8, sym['__code_end']
    ext = [exes.EXES[n][k] for n in exes.EXES for k in ('memcpy', 'drawsync', 'drawotag', 'tick') if exes.EXES[n].get(k)]
    p += check_code(ws, base, code_lo, code_hi, 'block', ext)
    p += check_frames(ws, base, functions(sym, code_lo, code_hi), sym)
    if ws[0] != 0x43315447 or ws[-1] != 0x31444E45:
        p.append('block: magic words')
    if pieces[0][0] != base or pieces[1][0] != base + len(pieces[0][1]) or             pieces[0][1] + pieces[1][1] != block:
        p.append('pieces do not make the block')
    # exe table: struct exe { memcpy, drawsync, drawotag, tick, clock, money, mode, site[3], orig[3] }
    t = (sym['EXES'] - base) // 4
    for name in ('GTMAIN.EXE', 'GTMENU.EXE'):
        e = exes.EXES[name]
        sites = [s or (0, 0) for s in e['sites']]
        want = [e['memcpy'], e['drawsync'], e['drawotag'], e['tick'], e['clock'], e['money'], e['mode']] + \
            [a for a, _ in sites] + [exes.jal(tg) if a else 0 for a, tg in sites]
        if ws[t:t + 13] != want:
            p.append('EXES[%s] = %s' % (name, ['%08X' % v for v in ws[t:t + 13]]))
        t += 13
    fn = [a for n, a in sym.items() if n.startswith('fn.')]
    if len(fn) != 1 or ws[(fn[0] - base) // 4:(fn[0] - base) // 4 + 3] != [sym['pad_hook'], sym['draw_hook'], sym['tick_hook']]:
        p.append('cheat_boot hook table')
    # stubs
    for name, stub in stubs.items():
        e = exes.EXES[name]
        sb = e['loader'] + exes.LOADER_SIZE
        sw = words(stub)
        p += check_code(sw, sb, sb, sb + len(stub), name + ' stub',
                        (sym['cheat_boot'],))
        calls = [branch_target(w, sb + 4 * i) for i, w in enumerate(sw) if w >> 26 == 3]
        if calls != ([sym['cheat_boot']] if e['boot'] else []):
            p.append('%s stub: calls %s' % (name, calls))
        n = 2 if e['boot'] else 0
        if sw.count(0x24090044) != n or sw.count(0x240A00A0) != n or sw.count(0x0000000C) != 2 * n:
            p.append('%s stub: FlushCache sequences' % name)
        if sw[-2:] != [0x01000008, 0] or sw[-4] != 0x3C080000 | (exes.GAME_ENTRY >> 16):
            p.append('%s stub: final jump to the game' % name)
        if e['piece'] is not None:
            dst, piece = pieces[e['piece']]
            if (0x240A0000 | (len(piece) // 4)) not in sw or len(piece) % 4:
                p.append('%s stub: copy count' % name)
            if [w for w in sw if w >> 16 == 0x3C09] != [0x3C090000 | ((dst + 0x8000) >> 16)]:
                p.append('%s stub: copy destination' % name)
        if e['boot']:
            hi = 0x3C0D0000 | ((base + len(block) - 4 + 0x8000) >> 16)
            if hi not in sw:
                p.append('%s stub: end magic address' % name)
        if out_dir and listing_:
            open(os.path.join(out_dir, 'stub_%s.dis' % name.split('.')[0].lower()), 'w').write(disasm_listing(sw, sb, sb, sb + len(stub), {'stub': sb}))
    if out_dir and listing_:
        open(os.path.join(out_dir, 'payload.dis'), 'w').write(disasm_listing(ws, base, base + 8, code_hi, sym))
    return p
