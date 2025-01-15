#!/bin/bash

# Ensure the script receives the required arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <interval> <experiment_path>"
    exit 1
fi

while true; do
    # filters out the iperf3 control socket which messes up the ss script as it looks at all sockets
    ss -OHtin sport = :11111 | ts '%.s,' >> "$2" 
    sleep "$1"
done &
