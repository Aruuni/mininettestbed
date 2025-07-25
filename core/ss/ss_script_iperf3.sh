#!/bin/bash

# Ensure the script receives the required arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <interval> <experiment_path> <duration>"
    exit 1
fi

interval="$1"               # e.g., 0.2
experiment_path="$2"
duration="$3"               # e.g., 30.5
start_time=$(date +%s.%N)

while true; do
    # filters out the iperf3 control socket which messes up the ss script as it looks at all sockets
    ss -OHtin sport = :11111 | ts '%.s,' >> "$experiment_path" 
    sleep "$interval"

    current_time=$(date +%s.%N)
    elapsed=$(echo "$current_time - $start_time" | bc)

    if (( $(echo "$elapsed >= $duration" | bc -l) )); then
        break
    fi
done &
