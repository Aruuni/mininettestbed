#!/bin/bash
source common.sh
bash setup.sh

# LeoEM single flow - ping results for bdp calculation
#       Starlink_SD_NY_15_ISL_path.log          62.727   522 pkts
#       Starlink_SD_NY_15_BP_path.log           49.043   408 pkts
#       Starlink_SEA_NY_15_ISL_path.log         46.551   388 pkts
#       Starlink_SEA_NY_15_BP_path.log          39.141   326 pkts
#       Starlink_SD_SEA_15_ISL_path.log         69.813   582 pkts
#       Starlink_SD_SEA_15_BP_path.log          26.270   219 pkts
#       Starlink_NY_LDN_15_ISL_path.log         83.566   696 pkts
#       Starlink_SD_Shanghai_15_ISL_path.log    88.811   740 pkts
#
# PROTOCOLS="satcp"

PATHS=( "Starlink_SD_NY_15_ISL_path.log" \
        "Starlink_SD_NY_15_BP_path.log" \
        "Starlink_SEA_NY_15_ISL_path.log" \
        "Starlink_SEA_NY_15_BP_path.log" \
        "Starlink_NY_LDN_15_ISL_path.log" \
        "Starlink_SD_Shanghai_15_ISL_path.log" )
QUEUE_PKTS=(522 408 388 326 696 740)

QMULTS="1"
RUNS="1 2 3 4 5"
PROTOCOLS="ping"
PROTOCOLS="sage"
PROTOCOLS="satcp"
PROTOCOLS="satcp vivace-uspace bbr3 astraea"


for qmult in $QMULTS; do
    for protocol in $PROTOCOLS; do
        for idx in "${!PATHS[@]}"; do
            path="${PATHS[$idx]}"
            base_pkts="${QUEUE_PKTS[$idx]}"
            adj_pkts=$(awk "BEGIN {printf \"%d\", $base_pkts * $qmult}")
            for run in $RUNS; do
                run experiments_mininet/LeoEM/emulator.py "$path" "[0]" 100 "$adj_pkts" "$protocol" "$run" 300
                sudo killall ss_script.sh > /dev/null 2>&1
                sudo killall ss_script_iperf.sh > /dev/null 2>&1
            done
        done
    done
done

for qmult in $QMULTS; do
    for protocol in $PROTOCOLS; do
        for idx in "${!PATHS[@]}"; do
            path="${PATHS[$idx]}"
            base_pkts="${QUEUE_PKTS[$idx]}"
            adj_pkts=$(awk "BEGIN {printf \"%d\", $base_pkts * $qmult}")
            for run in $RUNS; do
                run experiments_mininet/LeoEM/emulator.py "$path" "[0, 100]" 100 "$adj_pkts" "$protocol" "$run" 300 
                sudo killall ss_script.sh > /dev/null 2>&1
                sudo killall ss_script_iperf.sh > /dev/null 2>&1
            done
        done
    done
done


