"""The PSLZ header of Gran Turismo's executables (layout from pez2k's GT1ExecutableTool).

A PS-X EXE whose code is packed (GT-ARC LZSS, written backwards) and unpacked in place by a
small loader at the entry point. The 0x1C-byte header sits just before the loader:

    +0x00 "PSLZ"   +0x04 end of the unpacked code   +0x08 unpacked size
    +0x0C end of the packed data (the loader reads backwards from there)
    +0x10 where the loader copies itself (header + loader): end of the unpacked code + 1
    +0x14 bytes copied there (396: this header and the loader)
    +0x18 where the loader jumps once done (0x80010000: the game's start)

The loader (entry point) copies `+0x14` bytes from the header to `+0x10`, unpacks, flushes the
cache (A0:44) and jumps to `+0x18`. The patch enlarges `+0x14` (the copy then takes the stub
written after the loader, in bytes of the file that are zeros and never used) and points
`+0x18` at that stub: the packed code itself is not touched.
"""
import struct

HEADER = 0x800


class Exe:
    def __init__(self, data):
        if data[:8] != b'PS-X EXE':
            raise ValueError('not a PS-X EXE')
        self.data = bytes(data)
        self.entry, = struct.unpack_from('<I', data, 0x10)
        self.load, = struct.unpack_from('<I', data, 0x18)
        self.base = self.load - HEADER         # RAM address of file offset 0
        self.hdr = self.entry - self.base - 0x1C
        if data[self.hdr:self.hdr + 4] != b'PSLZ':
            raise ValueError('no PSLZ header')
        (self.out_end, self.out_size, self.in_end, self.loader, self.loader_size,
         self.jump) = struct.unpack_from('<IiIIII', data, self.hdr + 4)

    def ram(self, offset):
        """RAM address of a file offset (before unpacking)."""
        return self.base + offset


def run_loader(data):
    """What the PSLZ loader leaves in RAM, computed as it does it (same pointers, same end test):
    returns (unpacked code from 0x80010000, bytes copied to `loader`, jump target, end pointers).
    Used to check a patched executable: the code must be the original one, the copy must hold
    the stub."""
    x = Exe(data)
    lo = x.base + HEADER
    size = max(x.out_end, x.loader) + 1 - lo
    mem = bytearray(size)
    mem[:len(data) - HEADER] = data[HEADER:]
    # the copy (header + loader + whatever +0x14 covers), in 16-byte blocks
    n = (x.loader_size + 15) >> 4 << 4
    copied = bytes(data[x.hdr:x.hdr + n])
    a1, a0 = x.out_end, x.in_end
    while True:
        t0 = mem[a0 - lo]
        a0 -= 1
        stop = False
        for _ in range(8):
            if not a0 < a1:
                stop = True
                break
            v1 = mem[a0 - lo]
            a0 -= 1
            if not t0 & 1:
                mem[a1 - lo] = v1
                a1 -= 1
            else:
                v0 = mem[a0 - lo]
                a0 -= 1
                if v0 & 0x80:
                    v0 = (v0 & 0x7F) << 8 | mem[a0 - lo]
                    a0 -= 1
                src = a1 + v0 + 1
                for _ in range(v1 + 3):
                    mem[a1 - lo] = mem[src - lo]
                    src -= 1
                    a1 -= 1
            t0 >>= 1
        if stop or not a0 < a1:
            break
    jump = struct.unpack_from('<I', copied, 0x18)[0]
    return bytes(mem[:x.out_end + 1 - lo]), copied, jump, (a0, a1)
