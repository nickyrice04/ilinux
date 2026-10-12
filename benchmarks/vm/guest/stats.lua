-- mpv script used by pb.sh: rewrites playback counters once a second so the
-- host-side benchmark can take deltas over its measurement window.  mpv resets
-- its drop/delay counters on every seek, including --loop-file restarts, so
-- they are accumulated here from property-change events.
local out = "/run/user/1002/mpvstats.txt"
local totals = {}
for _, p in ipairs({"frame-drop-count", "decoder-frame-drop-count", "vo-delayed-frame-count"}) do
    local last = 0
    totals[p] = 0
    mp.observe_property(p, "number", function(_, v)
        v = v or 0
        if v > last then totals[p] = totals[p] + (v - last) end
        last = v
    end)
end
local props = {"hwdec-current", "estimated-vf-fps", "display-fps", "video-params/w", "video-params/h"}
mp.add_periodic_timer(1, function()
    local f = io.open(out .. ".tmp", "w")
    if not f then return end
    for p, v in pairs(totals) do f:write(p, "=", v, "\n") end
    for _, p in ipairs(props) do
        f:write((p:gsub("/", "_")), "=", tostring(mp.get_property(p)), "\n")
    end
    f:close()
    os.rename(out .. ".tmp", out)
end)
