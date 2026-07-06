#!/bin/bash
# /home/gs_zone.sh — start/stop individual PWI game zone processes, or bulk start/stop.
# Invoked by pwadmin-py (app/routers/server.py) via `sudo`.
#
# Usage:
#   gs_zone.sh start <zone>
#   gs_zone.sh stop <zone>
#   gs_zone.sh startmaps <zone> [<zone> ...]      # start every listed zone not already running
#   gs_zone.sh stopmaps <protected-zone> [...]    # stop every running zone except gs01 and the listed ones

set -u
GAMED=/home/gamed
LOGS=/home/logs
CONF_ARGS=(gs.conf gmserver.conf gsalias.conf)
STAGGER=20
# Each zone process measured at ~500-540MB RSS regardless of zone type
# (dominated by static game-data tables, not by zone size/type). An OOM-kill
# inside pwserver.service's cgroup takes down the WHOLE stack (systemd's
# default OOMPolicy), so we stop launching well before actually hitting zero
# rather than relying on the kernel OOM-killer as a backstop.
MIN_FREE_MB=1536

mkdir -p "$LOGS"
cd "$GAMED" || { echo "Cannot cd to $GAMED"; exit 1; }

mem_available_mb() {
  awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo
}

# Print the PID of the "./gs <zone> ..." process for $1, if running.
zone_pid() {
  local zone="$1" pid a0 a1
  for pid in $(pgrep -x gs 2>/dev/null); do
    { read -r -d '' a0; read -r -d '' a1; } < "/proc/$pid/cmdline" 2>/dev/null
    case "$a0" in
      *gs) [ "$a1" = "$zone" ] && { echo "$pid"; return 0; } ;;
    esac
  done
  return 1
}

start_zone() {
  local zone="$1" avail
  if zone_pid "$zone" >/dev/null; then
    echo "Already running"
    return 1
  fi
  avail=$(mem_available_mb)
  if [ "$avail" -lt "$MIN_FREE_MB" ]; then
    echo "Insufficient memory (${avail}MB free, need ${MIN_FREE_MB}MB)"
    return 1
  fi
  ./gs "$zone" "${CONF_ARGS[@]}" < /dev/null > "$LOGS/$zone.log" 2>&1 &
  disown
  echo "Started $zone"
}

stop_zone() {
  local zone="$1" pid
  if pid=$(zone_pid "$zone"); then
    kill -15 "$pid"
    echo "Stopped $zone (pid $pid)"
  else
    echo "Not running"
  fi
}

case "${1:-}" in
  start)
    start_zone "$2"
    ;;
  stop)
    stop_zone "$2"
    ;;
  startmaps)
    shift
    : > "$LOGS/startmaps.log"
    for z in "$@"; do
      if zone_pid "$z" >/dev/null; then
        continue
      fi
      avail=$(mem_available_mb)
      if [ "$avail" -lt "$MIN_FREE_MB" ]; then
        echo "$(date '+%F %T'): stopping, only ${avail}MB free (need ${MIN_FREE_MB}MB) - '$z' and any zones after it were not started" >> "$LOGS/startmaps.log"
        break
      fi
      ./gs "$z" "${CONF_ARGS[@]}" < /dev/null > "$LOGS/$z.log" 2>&1 &
      disown
      echo "$(date '+%F %T'): started $z (${avail}MB were free)" >> "$LOGS/startmaps.log"
      sleep "$STAGGER"
    done
    ;;
  stopmaps)
    shift
    protected=("gs01" "$@")
    for pid in $(pgrep -x gs 2>/dev/null); do
      { read -r -d '' a0; read -r -d '' a1; } < "/proc/$pid/cmdline" 2>/dev/null
      skip=0
      for w in "${protected[@]}"; do
        [ "$a1" = "$w" ] && skip=1 && break
      done
      [ "$skip" = "0" ] && kill -15 "$pid"
    done
    ;;
  *)
    echo "Usage: $0 {start <zone>|stop <zone>|startmaps <zones...>|stopmaps <protected...>}"
    exit 1
    ;;
esac
