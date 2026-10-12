#!/bin/bash
# Guest side of benchmarks/vm/playback_power.py (runs as root on the console).
#   pb.sh start hw|sw CLIP          loop CLIP fullscreen in mpv inside the Hyprland session
#   pb.sh start dec-hw|dec-sw CLIP  decode only: FFmpeg paced at the clip's frame rate
#                                   (-re), VA-API frames stay on the GPU, nothing displayed
#   pb.sh snap                      one line: uptime, guest busy/total jiffies, player CPU
#                                   ticks, and mpv's playback counters (from stats.lua)
#   pb.sh stop                      stop playback
set -u
D=/var/tmp/vt
R=/run/user/1002
S=$(ls $R/hypr | head -1)
U=(sudo -u omarchy XDG_RUNTIME_DIR=$R WAYLAND_DISPLAY=wayland-1 HYPRLAND_INSTANCE_SIGNATURE=$S)
case "$1" in
start)
  case "$2" in dec-*)
    hwa=(); [ "$2" = dec-hw ] && hwa=(-hwaccel vaapi -hwaccel_device /dev/dri/renderD128 -hwaccel_output_format vaapi)
    ( cd $D && setsid ffmpeg -hide_banner -loglevel error -nostdin -re -stream_loop -1 "${hwa[@]}" \
        -i "$3" -f null - > $D/ffmpeg-pb.log 2>&1 & )
    exit 0 ;;
  esac
  hw=no; [ "$2" = hw ] && hw=vaapi
  rm -f $R/mpvstats.txt
  ( cd $D && "${U[@]}" setsid mpv --no-config --hwdec=$hw --vo=gpu --gpu-api=opengl --fs \
      --loop-file=inf --script=$D/stats.lua --really-quiet "$3" > $D/mpv-pb.log 2>&1 & )
  ;;
snap)
  P=$(pgrep -n -x mpv || pgrep -n -x ffmpeg)
  read -r _ u n s i w q sq st _ < /proc/stat
  busy=$((u + n + s + q + sq + st)); total=$((busy + i + w))
  mt=0; [ -n "$P" ] && mt=$(awk '{print $14 + $15}' /proc/$P/stat)
  printf 'SNAP up=%s hz=%s busy=%s total=%s mpv=%s %s\n' "$(cut -d' ' -f1 /proc/uptime)" \
    "$(getconf CLK_TCK)" "$busy" "$total" "$mt" "$(tr '\n' ' ' < $R/mpvstats.txt 2>/dev/null)"
  ;;
stop)
  pkill -x mpv; pkill -x ffmpeg; sleep 1
  ;;
esac
