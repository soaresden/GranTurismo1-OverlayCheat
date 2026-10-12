"""Build the cheat: resident block + the two start-up stubs -> gt1cheat/payload.py.

    python build.py                 compile, link, check (verify.py), write gt1cheat/payload.py
    python build.py --list          also print the disassembly (build/*.dis)

Needs a MIPS GCC (mipsel-none-elf-* of PSn00bSDK, or mips-linux-gnu-*): on the PATH, in
tools/mips/bin, or in the directory named by the MIPS_BIN environment variable.
Only the generated gt1cheat/payload.py is needed to patch a disc (patch_disc.py).
"""
import glob
import os
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
BUILD = os.path.join(ROOT, 'build')
sys.path.insert(0, ROOT)
sys.path.insert(0, SRC)

from gt1cheat import exes  # noqa: E402
import font  # noqa: E402

PAYLOAD_MAGIC = 0x43315447      # "GT1C": first word of the resident block
END_MAGIC = 0x31444E45          # "END1": last word (both pieces are there)
# second word: CRC-32 of the block (computed with this word at 0), so that a stub never boots a
# first piece left in RAM by another build
CFLAGS = ['-Os', '-march=r3000', '-mtune=r3000', '-mabi=32', '-mno-abicalls', '-fno-pic', '-G0',
          '-msoft-float', '-mno-check-zero-division', '-ffreestanding', '-fno-builtin', '-nostdlib',
          '-fno-common', '-Wall', '-Wextra', '-Werror']


def tool(name):
    dirs = [os.environ.get('MIPS_BIN', ''), os.path.join(ROOT, 'tools', 'mips', 'bin'),
            r'D:\DOCS\Documents\GitHub\Resident Evil 1 Hotkey\tools\mips\bin']
    for prefix in ('mipsel-none-elf-', 'mips-linux-gnu-', 'mipsel-linux-gnu-'):
        for d in dirs:
            if d:
                hits = glob.glob(os.path.join(d, prefix + name + '*'))
                if hits:
                    return hits[0]
        w = shutil.which(prefix + name)
        if w:
            return w
    sys.exit('MIPS %s not found (MIPS_BIN, tools/mips/bin or PATH)' % name)


def run(*args):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(' '.join(map(str, args)) + '\n' + r.stdout + r.stderr)
    return r.stdout


def symbols(elf):
    out = run(tool('nm'), elf)
    return {n: int(a, 16) & 0xFFFFFFFF for a, t, n in (l.split() for l in out.splitlines() if len(l.split()) == 3)}


def build_payload(version):
    open(os.path.join(BUILD, 'font.h'), 'w', newline='\n').write(font.header())
    open(os.path.join(BUILD, 'exes.h'), 'w', newline='\n').write(exes.c_header())
    gcc = tool('gcc')
    defs = ['-DPAYLOAD_MAGIC=0x%08X' % PAYLOAD_MAGIC, '-DPAYLOAD_VERSION=0x%08X' % version]
    objs = []
    for src in ('start.S', 'cheat.c'):
        obj = os.path.join(BUILD, src.split('.')[0] + '.o')
        run(gcc, *CFLAGS, *defs, '-I', BUILD, '-c', os.path.join(SRC, src), '-o', obj)
        objs.append(obj)
    elf = os.path.join(BUILD, 'payload.elf')
    run(tool('ld'), '-T', os.path.join(SRC, 'payload.ld'), '-o', elf, *objs)
    und = [l for l in run(tool('nm'), '-u', elf).splitlines() if l.strip()]
    if und:
        sys.exit('undefined symbols: %s' % und)
    binf = os.path.join(BUILD, 'payload.bin')
    run(tool('objcopy'), '-O', 'binary', '-j', '.text', elf, binf)
    block = open(binf, 'rb').read()
    sym = symbols(elf)
    end = sym.get('_end', exes.RESIDENT + len(block))
    bss_end = max([a for n, a in sym.items() if a >= exes.RESIDENT] + [exes.RESIDENT + len(block)])
    if exes.RESIDENT + len(block) > exes.STATE or bss_end > exes.STATE:
        sys.exit('resident block too big: ends at %08X, state at %08X' % (max(end, bss_end), exes.STATE))
    return block, sym


def build_stub(name, sym, block_len, version, copy_dst=0, copy_words=0):
    e = exes.EXES[name]
    at = e['loader'] + exes.LOADER_SIZE
    tag = name.split('.')[0].lower()
    obj = os.path.join(BUILD, 'stub_%s.o' % tag)
    elf = os.path.join(BUILD, 'stub_%s.elf' % tag)
    binf = os.path.join(BUILD, 'stub_%s.bin' % tag)
    run(tool('gcc'), '-march=r3000', '-mabi=32', '-mno-abicalls', '-fno-pic', '-G0', '-c',
        '-DCOPY=%d' % (e['piece'] is not None), '-DBOOT=%d' % e['boot'],
        '-DEXE_ID=%d' % (e['id'] or 0), '-DRESIDENT=0x%08X' % exes.RESIDENT,
        '-DCOPY_DST=0x%08X' % copy_dst, '-DCOPY_WORDS=%d' % copy_words,
        '-DPAYLOAD_MAGIC=0x%08X' % PAYLOAD_MAGIC, '-DPAYLOAD_VERSION=0x%08X' % version,
        '-DEND_MAGIC=0x%08X' % END_MAGIC, '-DEND_MAGIC_AT=0x%08X' % (exes.RESIDENT + block_len - 4),
        '-DCHEAT_BOOT=0x%08X' % sym['cheat_boot'], '-DGAME_ENTRY=0x%08X' % exes.GAME_ENTRY,
        os.path.join(SRC, 'stub.S'), '-o', obj)
    run(tool('ld'), '-Ttext=0x%08X' % at, '-e', '_start', '-o', elf, obj)
    run(tool('objcopy'), '-O', 'binary', '-j', '.text', elf, binf)
    stub = open(binf, 'rb').read()
    if symbols(elf)['block'] != at + len(stub):
        sys.exit('stub: block label not at its end')
    return stub


def fits(name, ext):
    """The loader copies 16-byte blocks: what it copies must stay in the file."""
    return ((exes.LOADER_SIZE + ext + 15) & ~15) - exes.LOADER_SIZE <= exes.EXES[name]['room']


def split(block, sym, version):
    """Pieces 0 (GTOS) and 1 (GTMENU) of the block, as large a piece 1 as fits, and the stubs."""
    sizes = {n: len(build_stub(n, sym, len(block), version, exes.RESIDENT, 1)) for n in exes.EXES}
    n1 = len(block)
    while n1 and not fits('GTMENU.EXE', sizes['GTMENU.EXE'] + n1):
        n1 -= 4
    k = len(block) - n1
    if not fits('GTOS.EXE', sizes['GTOS.EXE'] + k):
        sys.exit('resident block too big: %d bytes, room for %d + %d'
                 % (len(block), n1, exes.EXES['GTOS.EXE']['room'] - sizes['GTOS.EXE']))
    pieces = {0: (exes.RESIDENT, block[:k]), 1: (exes.RESIDENT + k, block[k:])}
    stubs = {}
    for name, e in exes.EXES.items():
        dst, piece = pieces[e['piece']] if e['piece'] is not None else (0, b'')
        stubs[name] = build_stub(name, sym, len(block), version, dst, len(piece) // 4)
        assert len(stubs[name]) == sizes[name]
    return pieces, stubs


def write_payload_py(block, pieces, stubs, sym, version):
    def hexlines(b):
        return '\n'.join("    '%s'" % b[i:i + 48].hex() for i in range(0, len(b), 48))
    out = ['"""Generated by build.py: the compiled cheat (no game data). Do not edit."""',
           '', 'VERSION = 0x%08X' % version,
           'SYMBOLS = {%s}' % ', '.join("'%s': 0x%08X" % (n, sym[n]) for n in
                                       ('cheat_boot', 'pad_hook', 'draw_hook', 'tick_hook')),
           'BLOCK = bytes.fromhex(\n%s)' % hexlines(block),
           '# piece: (RAM address, bytes); 0 is carried by GTOS.EXE, 1 by GTMENU.EXE',
           'PIECES = {%s}' % ', '.join('%d: (0x%08X, BLOCK[%d:%d])' % (
               i, a, a - exes.RESIDENT, a - exes.RESIDENT + len(pc)) for i, (a, pc) in sorted(pieces.items())),
           'STUBS = {']
    for name, stub in stubs.items():
        out.append("    '%s': bytes.fromhex(\n%s)," % (name, hexlines(stub)))
    out.append('}')
    open(os.path.join(ROOT, 'gt1cheat', 'payload.py'), 'w', newline='\n').write('\n'.join(out) + '\n')


def main():
    os.makedirs(BUILD, exist_ok=True)
    import zlib
    block0, _ = build_payload(0)
    version = zlib.crc32(block0) | 1
    block, sym = build_payload(version)
    if block[:4] + block[8:] != block0[:4] + block0[8:]:
        sys.exit('the block changed with its version word')
    block += struct.pack('<I', END_MAGIC)
    if exes.RESIDENT + len(block) > exes.STATE:
        sys.exit('resident block too big: ends at %08X, state at %08X' % (exes.RESIDENT + len(block), exes.STATE))
    pieces, stubs = split(block, sym, version)
    import verify
    problems = verify.check_all(block, pieces, stubs, sym, listing='--list' in sys.argv, out_dir=BUILD)
    if problems:
        sys.exit('verify.py:\n  ' + '\n  '.join(problems))
    write_payload_py(block, pieces, stubs, sym, version)
    print('resident block %d bytes at %08X..%08X (state %08X), version %08X'
          % (len(block), exes.RESIDENT, exes.RESIDENT + len(block) - 1, exes.STATE, version))
    for name, e in exes.EXES.items():
        piece = pieces[e['piece']][1] if e['piece'] is not None else b''
        print('  %-10s stub %3d + piece %4d = %4d of %4d free bytes' % (
            name, len(stubs[name]), len(piece), len(stubs[name]) + len(piece), e['room']))
    print('cheat_boot %08X pad_hook %08X draw_hook %08X tick_hook %08X'
          % tuple(sym[n] for n in ('cheat_boot', 'pad_hook', 'draw_hook', 'tick_hook')))


if __name__ == '__main__':
    main()
