#!/bin/bash
# Guest side of benchmarks/vm/playback_power.py (runs as root on the console).
#   pb.sh start hw|sw[-next|-dmabuf][-fast] CLIP
#                                   loop CLIP fullscreen in mpv inside the Hyprland session
#   pb.sh start dec-hw|dec-sw CLIP  decode only: FFmpeg paced at the clip's frame rate
#                                   (-re), VA-API frames stay on the GPU, nothing displayed
#   pb.sh start vfill-FPS[-ds] -     display chain only: benchmarks/linux/vfill fullscreen
#                                   at FPS (0 = unpaced FIFO); -ds turns on Hyprland
#                                   direct scanout for the run
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
  case "$2" in vfill-*)
    fps=${2#vfill-}; ds=0
    case "$fps" in *-ds) ds=1; fps=${fps%-ds} ;; esac
    rm -f $R/vfillstats.txt
    "${U[@]}" hyprctl keyword render:direct_scanout $ds > /dev/null
    ( "${U[@]}" setsid vfill -f "$fps" -t 100000 -o $R/vfillstats.txt > $D/vfill-pb.log 2>&1 & )
    exit 0 ;;
  esac
  case "$2" in dec-*)
    hwa=(); [ "$2" = dec-hw ] && hwa=(-hwaccel vaapi -hwaccel_device /dev/dri/renderD128 -hwaccel_output_format vaapi)
    ( cd $D && setsid ffmpeg -hide_banner -loglevel error -nostdin -re -stream_loop -1 "${hwa[@]}" \
        -i "$3" -f null - > $D/ffmpeg-pb.log 2>&1 & )
    exit 0 ;;
  esac
  # hw|sw[-next|-dmabuf][-fast]: decode; renderer (default vo=gpu on OpenGL,
  # -next = gpu-next on OpenGL, -dmabuf = dmabuf-wayland, no mpv rendering);
  # -fast = mpv's fast profile (bilinear scaling, no linear-light passes)
  hw=no; vo=(--vo=gpu --gpu-api=opengl); extra=()
  case "$2" in hw*) hw=vaapi ;; esac
  case "$2" in *-next*) vo=(--vo=gpu-next --gpu-api=opengl) ;; *-dmabuf*) vo=(--vo=dmabuf-wayland) ;; esac
  case "$2" in *-fast*) extra=(--profile=fast) ;; esac
  rm -f $R/mpvstats.txt
  ( cd $D && "${U[@]}" setsid mpv --no-config --hwdec=$hw "${vo[@]}" "${extra[@]}" --fs \
      --loop-file=inf --script=$D/stats.lua --really-quiet "$3" > $D/mpv-pb.log 2>&1 & )
  ;;
snap)
  P=$(pgrep -n -x mpv || pgrep -n -x ffmpeg || pgrep -n -x vfill)
  read -r _ u n s i w q sq st _ < /proc/stat
  busy=$((u + n + s + q + sq + st)); total=$((busy + i + w))
  mt=0; [ -n "$P" ] && mt=$(awk '{print $14 + $15}' /proc/$P/stat)
  printf 'SNAP up=%s hz=%s busy=%s total=%s mpv=%s %s\n' "$(cut -d' ' -f1 /proc/uptime)" \
    "$(getconf CLK_TCK)" "$busy" "$total" "$mt" "$(cat $R/mpvstats.txt $R/vfillstats.txt 2>/dev/null | tr '\n' ' ')"
  ;;
stop)
  pkill -x mpv; pkill -x ffmpeg; pkill -x vfill
  "${U[@]}" hyprctl keyword render:direct_scanout 0 > /dev/null; sleep 1
  rm -f $R/mpvstats.txt $R/vfillstats.txt
  ;;
esac
