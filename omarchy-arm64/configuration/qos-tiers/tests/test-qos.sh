#!/bin/bash
# Functional test for omarchy-qos inside a disposable Linux VM (as the
# logged-in desktop user, with omarchy-qos installed).  Checks mechanics
# only: slice placement, CPU restriction, uclamp values.  Performance effects
# need heterogeneous native hardware.
set -uo pipefail
pass=0 fail=0
ok() { echo "PASS $*"; pass=$((pass + 1)); }
ko() { echo "FAIL $*"; fail=$((fail + 1)); }

ncpu=$(nproc)
[ "$ncpu" -ge 2 ] || { echo "need >= 2 CPUs"; exit 2; }
export OMARCHY_QOS_EFFICIENT_CPUS="0"   # pretend cpu0 is the efficient cluster

omarchy-qos apply && ok "apply" || ko "apply"
omarchy-qos status

cg=$(omarchy-qos run background -- cat /proc/self/cgroup)
[[ "$cg" == *background.slice* ]] && ok "background tier lands in background.slice" || ko "cgroup: $cg"
cpus=$(omarchy-qos run background -- awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)
[ "$cpus" = "0" ] && ok "background restricted to efficient set (0)" || ko "Cpus_allowed_list=$cpus"
cpus_app=$(omarchy-qos run default -- awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)
[ "$cpus_app" != "0" ] && ok "default tier unrestricted ($cpus_app)" || ko "default restricted"
cg=$(omarchy-qos run utility -- cat /proc/self/cgroup)
[[ "$cg" == *utility.slice* ]] && ok "utility tier lands in utility.slice" || ko "cgroup: $cg"

base=/sys/fs/cgroup$(systemctl --user show -P ControlGroup background.slice)
if [ -r "$base/cpu.uclamp.max" ]; then
  v=$(cat "$base/cpu.uclamp.max")
  [ "$v" = "30.00" ] && ok "background uclamp.max=30.00" || ko "background uclamp.max=$v"
else
  echo "SKIP uclamp (kernel lacks CONFIG_UCLAMP_TASK_GROUP or cpu controller not enabled)"
fi
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
