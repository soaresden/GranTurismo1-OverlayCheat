"""A PlayStation disc image (.chd, or .bin / .cue with 2352-byte sectors): files of its ISO 9660
file system, and a .bin/.cue copy of it with some files replaced in place (same sectors, same
sizes).

Sectors are mode 2 form 1 (2048 bytes of data): a replaced sector keeps its header and subheader
and gets its EDC and ECC computed again.

Adapted from MazdaMx5NDRF/games/gran-turismo-ps1/disc.py (same author, GPL-3.0); reading
.bin/.cue images added.
"""
import os
import re
import struct

from . import chd

SECTOR = chd.SECTOR


def _edc_table():
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ (0xD8018001 if c & 1 else 0)
        t.append(c)
    return t


_EDC_TABLE = _edc_table()


def edc(data):
    """CD-ROM EDC: CRC-32 with the polynomial 0xD8018001 (reflected), table driven."""
    crc = 0
    t = _EDC_TABLE
    for b in data:
        crc = t[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc


def make_sector(original, data):
    """Mode 2 form 1 sector with the header and subheader of `original` and 2048 bytes of data."""
    s = bytearray(original[:24]) + bytearray(data.ljust(2048, b'\0')) + bytearray(SECTOR - 2072)
    struct.pack_into('<I', s, 2072, edc(s[16:2072]))
    chd.ecc_generate(s)
    return bytes(s)


class _Bin:
    """Raw image (first data track of a .bin, 2352-byte sectors): a path or a file object."""

    def __init__(self, path):
        self.f = open(path, 'rb') if isinstance(path, str) else path
        self.f.seek(0, 2)
        self.frames = self.f.tell() // SECTOR

    def sector(self, lba):
        self.f.seek(lba * SECTOR)
        return self.f.read(SECTOR)


def bin_of_cue(cue):
    """The .bin a .cue names (first FILE line), next to the .cue."""
    text = open(cue, 'r', errors='replace').read()
    m = re.search(r'FILE\s+"([^"]+)"', text) or re.search(r'FILE\s+(\S+)', text)
    if not m:
        raise ValueError('%s: no FILE line' % cue)
    return os.path.join(os.path.dirname(os.path.abspath(cue)), m.group(1))


class Disc:
    def __init__(self, path):
        """path: a .chd, .cue or .bin, or a file object of a .chd or a .bin (the browser page)."""
        if not isinstance(path, str):
            path.seek(0)
            magic = path.read(8)
            path.seek(0)
            self.c = chd.Chd(path) if magic == b'MComprHD' else _Bin(path)
            self.path = getattr(path, 'name', 'disc')
            self._open()
            return
        low = path.lower()
        if low.endswith('.chd'):
            self.c = chd.Chd(path)
        else:
            if low.endswith('.cue'):
                path = bin_of_cue(path)
            self.c = _Bin(path)
        self.path = path
        self._open()

    def _open(self):
        self.files = {}
        pvd = self.user_data(16)
        if pvd[1:6] != b'CD001':
            raise ValueError('%s: no ISO 9660 file system' % self.path)
        root = pvd[156:190]
        self._walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')

    def user_data(self, lba):
        s = self.c.sector(lba)
        if s[15] == 2:
            return s[24:24 + 2048]
        return s[16:16 + 2048]

    def _read(self, lba, count):
        return b''.join(self.user_data(lba + i) for i in range(count))

    def _walk(self, lba, size, path):
        d = self._read(lba, (size + 2047) // 2048)
        o = 0
        while o < len(d):
            n = d[o]
            if n == 0:
                o = (o // 2048 + 1) * 2048
                continue
            e_lba, = struct.unpack_from('<I', d, o + 2)
            e_size, = struct.unpack_from('<I', d, o + 10)
            flags, nl = d[o + 25], d[o + 32]
            name = d[o + 33:o + 33 + nl]
            if name not in (b'\0', b'\1'):
                nm = name.decode('ascii').split(';')[0]
                full = path + '/' + nm
                if flags & 2:
                    self._walk(e_lba, e_size, full)
                else:
                    self.files[full.lstrip('/')] = (e_lba, e_size, lba + (o // 2048), o % 2048)
            o += n

    @property
    def frames(self):
        return self.c.frames

    def read(self, name):
        lba, size = self.files[name][:2]
        return self._read(lba, (size + 2047) // 2048)[:size]

    def _sectors(self, replace):
        """{lba: new 2048 bytes} for replace = {file name: new bytes}."""
        sectors = {}
        for name, data in replace.items():
            lba, size = self.files[name][:2]
            if len(data) != size:
                raise ValueError('%s: %d bytes, the file has %d' % (name, len(data), size))
            for i in range((len(data) + 2047) // 2048):
                sectors[lba + i] = data[i * 2048:(i + 1) * 2048]
        return sectors

    def bin_chunks(self, replace, chunk=2048, progress=None):
        """The .bin (raw 2352-byte sectors), `chunk` sectors at a time (bytes): for the browser
        page, which writes each piece where it goes, and for write_bin."""
        sectors = self._sectors(replace)
        total = self.frames
        for start in range(0, total, chunk):
            out = []
            for lba in range(start, min(total, start + chunk)):
                raw = self.c.sector(lba)
                if lba in sectors:
                    raw = make_sector(raw, sectors[lba])
                out.append(raw)
            if progress:
                progress(min(total, start + chunk), total)
            yield b''.join(out)

    def write_bin(self, path, replace, progress=None):
        """Write the .bin and its .cue (see bin_chunks)."""
        # written under a temporary name and renamed once complete: a half-written image never
        # looks like a finished one
        part = path + '.part'
        with open(part, 'wb') as f:
            for piece in self.bin_chunks(replace, progress=progress):
                f.write(piece)
        os.replace(part, path)
        base = os.path.basename(path)
        with open(os.path.splitext(path)[0] + '.cue', 'w', newline='\r\n') as f:
            f.write('FILE "%s" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % base)
