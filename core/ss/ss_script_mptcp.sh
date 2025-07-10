#!/bin/bash

# Ensure the script receives the required arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <interval> <experiment_path>"
    exit 1
fi

while true; do
    ss -OHtin | ts '%.s,' >> "$2" 
    sleep "$1"
done &
