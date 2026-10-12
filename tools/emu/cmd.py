"""Send commands to the running drive.lua (see launch.py); waits for them, converts the shots to PNG,
puts them side by side in out/last.png and prints the end of the log."""
import os, sys, time, re
HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, 'out')
def rgb555(d, w, h):
    from PIL import Image
    import array
    a = array.array('H', d[:w*h*2])
    out = bytearray(w * h * 3)
    for i, v in enumerate(a):
        out[i*3] = (v & 31) << 3; out[i*3+1] = ((v >> 5) & 31) << 3; out[i*3+2] = ((v >> 10) & 31) << 3
    return Image.frombytes('RGB', (w, h), bytes(out))
def to_png(names=None):
    from PIL import Image
    for line in open(os.path.join(out, 'log.txt')):
        m = re.match(r'SHOT (\S+) (\d+)x(\d+) bpp=(\d)', line)
        if m and (names is None or m.group(1) in names):
            name, w, h, bpp = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            p = os.path.join(out, name + '.png')
            if os.path.exists(p) and os.path.getmtime(p) >= os.path.getmtime(os.path.join(out, name + '.raw')): continue
            d = open(os.path.join(out, name + '.raw'), 'rb').read()
            try:
                im = Image.frombytes('RGB', (w, h), d[:w*h*3]) if bpp == 1 else rgb555(d, w, h)
                im.save(p)
            except Exception as e: print('png fail', name, e)
        m = re.match(r'VRAM (\S+)', line)
        if m and (names is None or m.group(1) in names):
            p = os.path.join(out, m.group(1) + '_vram.png')
            if not os.path.exists(p):
                rgb555(open(os.path.join(out, m.group(1) + '.vram'), 'rb').read(), 1024, 512).save(p)
if __name__ == '__main__':
    tmp = os.path.join(out, 'cmd.tmp')
    with open(tmp, 'w', newline='\n') as f:
        f.write(sys.argv[1].replace('\n', '\n') + '\n')
    os.replace(tmp, os.path.join(out, 'cmd.txt'))
    t0 = time.time(); limit = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    log = os.path.join(out, 'log.txt')
    n0 = sum(1 for l in open(log) if 'CMDDONE' in l)
    while time.time() - t0 < limit:
        time.sleep(0.3)
        if sum(1 for l in open(log) if 'CMDDONE' in l) > n0: break
    to_png()
    print(''.join(open(log).readlines()[-6:]))
    names = [l.split()[1] for l in sys.argv[1].replace('\n', '\n').split('\n') if l.startswith('shot ')]
    if names:
        from PIL import Image
        ims = [Image.open(os.path.join(out, n + '.png')).resize((320, 240)) for n in names if os.path.exists(os.path.join(out, n + '.png'))]
        cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols
        o = Image.new('RGB', (320 * cols, 240 * rows))
        for i, im in enumerate(ims): o.paste(im, ((i % cols) * 320, (i // cols) * 240))
        o.save(os.path.join(out, 'last.png'))
