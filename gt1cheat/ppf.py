"""PPF 3.0 patches (BIN image, no block check, no undo data), written and applied."""
import struct


def header(description):
    desc = description.encode('ascii', 'replace')[:50].ljust(50, b' ')
    return b'PPF30' + bytes([2]) + desc + bytes([0, 0, 0, 0])


def records(changes):
    """changes: [(offset, old bytes, new bytes)] -> PPF records of the runs of changed bytes
    only (no unchanged byte of the image is copied into the patch)."""
    out = bytearray()
    for off, old, new in changes:
        i = 0
        while i < len(new):
            if old[i] == new[i]:
                i += 1
                continue
            j = i
            while j < len(new) and j - i < 255 and old[j] != new[j]:
                j += 1
            out += struct.pack('<QB', off + i, j - i) + new[i:j]
            i = j
    return bytes(out)


def make(changes, description):
    return header(description) + records(changes)


def apply(ppf, f):
    """Apply a PPF 3.0 patch (as made here) to the open file f (r+b)."""
    if ppf[:5] != b'PPF30' or ppf[5] != 2:
        raise ValueError('not a PPF 3.0 patch')
    if ppf[57] != 0 or ppf[58] != 0:
        raise ValueError('PPF with block check / undo data: not supported here')
    i = 60
    n = 0
    while i < len(ppf):
        off, ln = struct.unpack_from('<QB', ppf, i)
        i += 9
        f.seek(off)
        f.write(ppf[i:i + ln])
        i += ln
        n += 1
    return n
