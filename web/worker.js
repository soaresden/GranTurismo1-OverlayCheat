// Web worker of the page (index.html): adds the cheat to the visitor's disc image with the
// project's Python (gt1cheat), run by Pyodide in the browser. Nothing is sent anywhere.
// The disc image is never loaded whole: Python reads slices of the chosen File with
// FileReaderSync (only in workers), and the patched .bin (~690 MB) is made a few MB at a time
// (Disc.bin_chunks), each piece going straight to its destination:
//   - the file chosen with showSaveFilePicker (Chrome, Edge), written from here;
//   - otherwise a file of the site's private storage (OPFS), offered as a download afterwards;
//   - otherwise (old browsers) a Blob made of the pieces.
// Adapted from the MX-5 project's gt1-worker.js (same author).

importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');

const PACKAGE = 'gt1cheat';
const SOURCES = ['__init__', 'chd', 'check', 'disc', 'exes', 'patcher', 'payload', 'ppf', 'pslz'];
const OPFS_NAME = 'gt1_cheat.bin';
// Python run once the disc is open as DISC: FILES = {name on the disc: new bytes}
const PATCH = `
from gt1cheat import patcher
FILES = {}
for _n in ('GTOS.EXE', 'GTMENU.EXE', 'GTMAIN.EXE'):
    if _n not in DISC.files:
        raise patcher.PatchError(T("%s absent : ce n'est pas Gran Turismo PAL (SCES-00984)",
                                   "%s missing: this is not Gran Turismo PAL (SCES-00984)") % _n)
    FILES[_n] = patcher.patch_exe(_n, DISC.read(_n))
    jslog(T('  %s : triche ajoutée', '  %s: cheat added') % _n)
`;

const say = (type, data) => postMessage({ type, ...data });
const EN = new URL(self.location).searchParams.get('lang') === 'en';
const T = (fr, en) => (EN ? en : fr);
let pyodide = null;

async function init() {
  say('log', { text: T('Chargement de Python (Pyodide)…', 'Loading Python (Pyodide)…') });
  pyodide = await loadPyodide();
  await pyodide.loadPackage(['lzma']);      // the codec of the CHD sectors
  pyodide.FS.mkdirTree('/app/' + PACKAGE);
  for (const m of SOURCES) {
    const res = await fetch(new URL(`../${PACKAGE}/${m}.py`, self.location));
    if (!res.ok) throw new Error(`${PACKAGE}/${m}.py : ${res.status}`);
    pyodide.FS.writeFile(`/app/${PACKAGE}/${m}.py`, new Uint8Array(await res.arrayBuffer()));
  }
  pyodide.globals.set('LANG_EN', EN);
  await pyodide.runPythonAsync(`
import io, sys
sys.path[:0] = ['/app']
from js import FileReaderSync

def T(fr, en):
    return en if LANG_EN else fr

class BlobFile(io.RawIOBase):
    """Read-only, seekable view of a browser File, read in slices."""
    def __init__(self, f):
        self.f, self.pos, self.size, self.r = f, 0, int(f.size), FileReaderSync.new()
        self.name = str(f.name)
    def readable(self):
        return True
    def seekable(self):
        return True
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def tell(self):
        return self.pos
    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        b[:n] = self.r.readAsArrayBuffer(self.f.slice(self.pos, self.pos + n)).to_py()
        self.pos += n
        return n

class UrlFile(BlobFile):
    """Same, over HTTP Range requests (test mode: tools/serve_test.py)."""
    def __init__(self, url):
        from js import XMLHttpRequest
        self.url, self.pos, self.X, self.name = url, 0, XMLHttpRequest, url.split('/')[-1]
        x = XMLHttpRequest.new(); x.open('HEAD', url, False); x.send()
        self.size = int(x.getResponseHeader('Content-Length'))
    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        x = self.X.new(); x.open('GET', self.url, False); x.responseType = 'arraybuffer'
        x.setRequestHeader('Range', 'bytes=%d-%d' % (self.pos, self.pos + n - 1)); x.send()
        b[:n] = x.response.to_py()
        self.pos += n
        return n

def open_disc(f):
    return io.BufferedReader(UrlFile(f) if isinstance(f, str) else BlobFile(f), 1 << 16)
`);
  say('ready', {});
}

const ready = init().catch((e) => say('error', { text: String(e) }));

async function openSink(target, size) {
  if (target) {
    const w = await target.createWritable();
    return { kind: 'file', write: (b) => w.write(b), close: async () => { await w.close(); return { saved: target.name }; },
             abort: () => w.abort().catch(() => {}) };
  }
  try {
    const root = await navigator.storage.getDirectory();
    const est = navigator.storage.estimate ? await navigator.storage.estimate() : null;
    try { await root.removeEntry(OPFS_NAME); } catch (_) { /* none yet */ }
    if (est && est.quota - est.usage < size + (64 << 20)) throw new Error('quota');
    const fh = await root.getFileHandle(OPFS_NAME, { create: true });
    const h = await fh.createSyncAccessHandle();
    h.truncate(0);
    let at = 0;
    let parts = null;          // the site's storage is full: the rest goes to memory (a Blob)
    const sink = {
      kind: 'opfs',
      write: (b) => {
        if (parts) { parts.push(new Blob([b])); return; }
        let n = 0;
        try { n = h.write(b, { at }); } catch (_) { n = -1; }
        if (n === b.byteLength) { at += n; return; }
        // storage full (the browser's quota can be smaller than its estimate): what is written
        // so far is read back into memory, and the image goes on there
        const head = new Uint8Array(at);
        h.read(head, { at: 0 });
        h.close();
        root.removeEntry(OPFS_NAME).catch(() => {});
        parts = [new Blob([head]), new Blob([b])];
        sink.kind = 'blob';
      },
      close: () => {
        if (parts) return { blob: new Blob(parts, { type: 'application/octet-stream' }) };
        h.flush(); h.close(); return { opfs: OPFS_NAME };
      },
      abort: () => { parts = null; try { h.close(); } catch (_) {} root.removeEntry(OPFS_NAME).catch(() => {}); },
    };
    return sink;
  } catch (_) {
    const parts = [];
    return { kind: 'blob', write: (b) => { parts.push(new Blob([b])); },
             close: () => ({ blob: new Blob(parts, { type: 'application/octet-stream' }) }), abort: () => { parts.length = 0; } };
  }
}

onmessage = async (ev) => {
  await ready;
  const { disc, target } = ev.data;
  let sink = null;
  try {
    const t0 = Date.now();
    pyodide.globals.set('DISC_FILE', disc);
    pyodide.globals.set('jslog', (text) => say('log', { text }));
    say('log', { text: T('Lecture du disque…', 'Reading the disc…') });
    await pyodide.runPythonAsync(`
from ${PACKAGE} import disc as _disc
DISC = _disc.Disc(open_disc(DISC_FILE))
` + PATCH + `
TOTAL = DISC.frames * 2352
GEN = DISC.bin_chunks(FILES)
def next_chunk():
    return next(GEN, None)
`);
    const total = pyodide.globals.get('TOTAL');
    say('log', { text: T("L'image disque (.bin), écrite au fur et à mesure", 'The disc image (.bin), written as it is made') });
    sink = await openSink(target, total);
    const next = pyodide.globals.get('next_chunk');
    let done = 0;
    for (;;) {
      const c = next();
      if (c === undefined || c === null) break;
      const bytes = c.toJs();
      c.destroy();
      await sink.write(bytes);
      done += bytes.byteLength;
      say('progress', { done, total });
    }
    next.destroy();
    pyodide.runPython('del FILES, DISC, GEN');
    const result = await sink.close();
    say('done', { ...result, kind: sink.kind, size: done, seconds: Math.round((Date.now() - t0) / 1000) });
  } catch (e) {
    if (sink) sink.abort();
    try { pyodide.runPython("for _k in ('FILES', 'DISC', 'GEN'): globals().pop(_k, None)"); } catch (_) {}
    let text = String(e);
    const m = text.match(/(PatchError|ValueError|KeyError): (.*)/);   // the Python message, not the traceback
    if (m) text = m[2];
    say('error', { text });
  }
};
