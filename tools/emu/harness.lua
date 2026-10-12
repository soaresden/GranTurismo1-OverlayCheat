-- generic harness (from the Resident Evil 1 Hotkey project): env HARNESS_SCRIPT (lua file returning
-- a table with step(n, api)), HARNESS_OUT (output dir); step is called at every vsync
local ffi = require('ffi')
local outdir = os.getenv('HARNESS_OUT') or 'out'   -- created by run.py
local cfg = dofile(os.getenv('HARNESS_SCRIPT'))
local n = 0
local mem = PCSX.getMemPtr()
local log = io.open(outdir..'/log.txt','w')
local function L(s) log:write(s..'\n'); log:flush() end
local function r8(a) return mem[a - 0x80000000] end
local function r16(a) return ffi.cast('uint16_t*', mem + (a - 0x80000000))[0] end
local function r32(a) return ffi.cast('uint32_t*', mem + (a - 0x80000000))[0] end
local function w8(a,v) mem[a - 0x80000000] = v end
local function w32(a,v) ffi.cast('uint32_t*', mem + (a - 0x80000000))[0] = v end
local pad = PCSX.SIO0.slots[1].pads[1]
local B = PCSX.CONSTS.PAD.BUTTON
local function vram(name)
  local file = Support.File.open(outdir..'/'..name..'.vram', 'TRUNCATE')
  file:writeMoveSlice(PCSX.GPU.getVRAM()); file:close()
  L('VRAM '..name)
end
local function dump(name)
  local f = io.open(outdir..'/'..name..'.ram', 'wb'); f:write(ffi.string(mem, 0x200000)); f:close()
  L('RAM '..name)
end
local function shot(name)
  local ss = PCSX.GPU.takeScreenShot()
  local file = Support.File.open(outdir..'/'..name..'.raw', 'TRUNCATE')
  file:writeMoveSlice(ss.data); file:close()
  L(string.format('SHOT %s %dx%d bpp=%d', name, ss.width, ss.height, tonumber(ss.bpp)))
end
local held = {}
local api = {r8=r8,r16=r16,r32=r32,w8=w8,w32=w32,L=L,shot=shot,vram=vram,dump=dump,B=B,
  press=function(btn, frames) pad.setOverride(btn); held[btn] = n + (frames or 4) end,
  save=function(name) local s = PCSX.createSaveState(); local f = Support.File.open(outdir..'/'..name..'.sstate','TRUNCATE'); f:writeMoveSlice(s); f:close(); L('SAVED '..name) end,
  load=function(path) local f = Support.File.open(path, 'READ'); PCSX.loadSaveState(f); f:close(); L('LOADED '..path) end,
  quit=function() log:close(); PCSX.quit(0) end,
}
HARNESS_LISTENER = PCSX.Events.createEventListener('GPU::Vsync', function()
  n = n + 1
  for btn, until_ in pairs(held) do if n >= until_ then pad.clearOverride(btn); held[btn] = nil end end
  local ok, err = pcall(cfg.step, n, api)
  if not ok then L('ERR '..tostring(err)); PCSX.quit(1) end
end)
