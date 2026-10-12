-- interactive driver: polls CMD_FILE every 2 frames; commands are queued (wait n delays the next ones)
local CMD = os.getenv('CMD_FILE') or 'cmd.txt'
local queue = {}   -- {frame, fn}
local waitn = 0
return { step = function(n, a)
  if n % 2 == 0 then
    local f = io.open(CMD,'r')
    if f then
      local cmds = f:read('*a'); f:close(); os.remove(CMD)
      local t = n
      for line in cmds:gmatch('[^\n]+') do
        local op, arg1, arg2 = line:match('(%S+)%s*(%S*)%s*(%S*)')
        local tt = t
        if op == 'press' then queue[#queue+1] = {tt, function() a.press(a.B[arg1], tonumber(arg2) or 4) end}
        elseif op == 'hold' then queue[#queue+1] = {tt, function() a.press(a.B[arg1], tonumber(arg2) or 4) end}; 
        elseif op == 'wait' then t = t + (tonumber(arg1) or 1)
        elseif op == 'shot' then queue[#queue+1] = {tt, function() a.shot(arg1) end}
        elseif op == 'dump' then queue[#queue+1] = {tt, function() a.dump(arg1) end}
        elseif op == 'vram' then queue[#queue+1] = {tt, function() a.vram(arg1) end}
        elseif op == 'save' then queue[#queue+1] = {tt, function() a.save(arg1) end}
        elseif op == 'load' then queue[#queue+1] = {tt, function() a.load(arg1) end}
        elseif op == 'r32' then queue[#queue+1] = {tt, function() a.L(string.format('R32 %s = %08x', arg1, a.r32(tonumber(arg1)))) end}
        elseif op == 'w32' then queue[#queue+1] = {tt, function() a.w32(tonumber(arg1), tonumber(arg2)) end}
        elseif op == 'w8' then queue[#queue+1] = {tt, function() a.w8(tonumber(arg1), tonumber(arg2)) end}
        elseif op == 'lua' then local code = "local a, n = ...; " .. line:match('lua%s+(.*)$'); local fn, err = loadstring(code); queue[#queue+1] = {tt, function() if fn then local ok, e2 = pcall(fn, a, n); a.L('LUA '..tostring(ok)..' '..tostring(e2)) else a.L('LUAERR '..tostring(err)) end end}
        elseif op == 'quit' then queue[#queue+1] = {tt, function() a.quit() end}
        end
      end
      queue[#queue+1] = {t, function() a.L('CMDDONE F'..n) end}
    end
  end
  local rest = {}
  for _, q in ipairs(queue) do
    if n >= q[1] then q[2]() else rest[#rest+1] = q end
  end
  queue = rest
  if a.tick then a.tick(n) end
end }
