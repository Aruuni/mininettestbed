#!/bin/bash
source common.sh
bash setup.sh

PROTOCOLS="astraea orca bbr3 cubic vivace-uspace"
# PROTOCOLS="sage"

STEPS="10 20 30 40 50 60 70 80 90 100"
FLOWS_STEPS="3 5 7 9 11 13 15 17 19 21"
QMULTS="0.2 1 4"
RUNS="1 2 3 4 5"

# # FAIRNESS INTRA RTT 
# for del in $STEPS
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/intra_rtt_fairness/experiment_intra_rtt_fairness.py $del "100" $qmult $protocol $run fifo 0 "2"
#             done
#         done
#     done
# done


# FAIRNESS INTER RTT
#for del in $STEPS
#do
#    for qmult in $QMULTS
#    do
#        for protocol in $PROTOCOLS
#        do
#            for run in $RUNS
#            do
#                run experiments_mininet/inter_rtt_fairness/experiment_inter_rtt_fairness.py $del "100" $qmult $protocol $run fifo 0 "2"
#            done
#        done
#    done
#done



# FAIRNESS BANDWIDTH
#for bw in $STEPS
#do
#   for qmult in $QMULTS
#    do
#        for protocol in $PROTOCOLS
#        do
#            for run in $RUNS
#            do
#                run experiments_mininet/intra_bw_fairness/experiment_intra_bw_fairness.py "20" $bw $qmult $protocol $run fifo 0 "2"
#            done
#        done  
#    done
#done

# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY WITH FLOWS
for flows in $FLOWS_STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
              run experiments_mininet/cubic_flows_friendliness/experiment_cubic_flow_friendliness.py "15" "100" $qmult $protocol $run fifo 0 $flows
            done
        done
    done
done

# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY
#for del in $STEPS
#do
#    for qmult in $QMULTS
#    do
#        for protocol in $PROTOCOLS
#        do
#            for run in $RUNS
#            do
#               run experiments_mininet/cubic_rtt_friendliness/experiment_cubic_rtt_friendliness.py $del "100" $qmult $protocol $run fifo 0 "2"
#            done
#        done
#    done
#done


# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY [INVERSE]
#DELAYPOINT="50"

#for qmult in $QMULTS
#do
#    for protocol in $PROTOCOLS
#    do
#        for run in $RUNS
#        do
#            run experiments_mininet/cubic_rtt_friendliness_inverse/experiment_cubic_rtt_friendliness_inverse.py $DELAYPOINT "100" $qmult $protocol $run fifo 0 "2"
#        done
#    done
#done


# # # RESPONSIVENESS BANDWIDTH/RTT FOR LEO PAPER
# for protocol in $PROTOCOLS
# do
#     for run in {1..50}
#     do
#         run experiments_mininet/responsiveness_bw_rtt_leo/experiment_responsiveness_bw_rtt_leo.py "50" "50" "1" $protocol $run fifo 0 "1"
#     done
# done


#  # RESPONSIVENESS BANDWIDTH/RTT/LOSS FOR LEO PAPER
# for protocol in $PROTOCOLS
# do
#     for run in {1..50}
#     do
#          run experiments_mininet/responsiveness_bw_rtt_loss_leo/experiment_responsiveness_bw_rtt_loss_leo.py "50" "50" "1" $protocol $run fifo 0 "1"
#     done
# done

# # RESPONSIVENESS BW RTT 
# for protocol in $PROTOCOLS
# do
#     for run in {1..50}
#     do
#         run experiments_mininet/responsiveness_bw_rtt/experiment_responsiveness_bw_rtt.py "50" "50" "1" $protocol $run fifo 0 "1"
#     done
# done

# # RESPONSIVENESS LOSS
# for protocol in $PROTOCOLS
# do
#     for run in {1..50}
#     do
#         run experiments_mininet/responsiveness_loss/experiment_responsiveness_loss.py "50" "50" "1" $protocol $run fifo 0 "1"
#     done
# done


# # EFFICIENCY/CONVERGENCE 
# BANDWIDTH="100"
# DELAY="10 100"
# DELAY="50"
# AQMS='fifo'

# for del in $DELAY
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for aqm in $AQMS
#             do
#                 for run in $RUNS
#                 do
#                     run experiments_mininet/fairness_aqm/experiment_fairness_aqm.py $del "100" $qmult $protocol $run $aqm 0 "4"
#                 done
#             done
#         done
#     done
# done


# # PARKING LOT TOPOLOGY INTRA RTT
# for del in $STEPS
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/fairness_parking_lot_intra_rtt/experiment_parking_lot.py $del "100" $qmult $protocol $run "fifo" 0 "4"
#             done
#         done
#     done
# done

# # PARKING LOT TOPOLOGY INTER RTT
# for del in $STEPS
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/fairness_parking_lot_inter_rtt/experiment_parking_lot_inter.py $del "100" $qmult $protocol $run "fifo" 0 "4"
#             done
#         done
#     done
# done


# QMULTS="0.2 1 4"
# RUNS="1 2 3 4 5"
## left at 60  queue size 1
# need astraea and orca 10 to 60 full 


# aSteps="5 15 25 35 45"
# hSTEPS="5 10 15 20 25 30 35 40 45 50"

# STEPS="50 60 70 80 90 100"
# HOPS="3 5 6"
# RUNS="1 2 3 4 5"

# # PARKING LOT TOPOLOGY INTRA RTT
# for del in $STEPS
# do
#     for hop in $HOPS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/fairness_parking_lot_hop_count/experiment_parking__lot_hop_count.py $del "100" "1" $protocol $run "fifo" 0 $hop
#             done
#         done
#     done
# done








# PROTOCOLS="astraea orca bbr1 bbr3 cubic vivace"
# aSteps="35"
# QMULTS="0.2 1 4"
# RUNS="1 2 3 4 5"
# Fairness Cross path Inter
# for del in $aSteps
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/cross_path_fairness_inter_rtt/experiment_cross_path_fairness_inter_rtt.py $del "100" $qmult $protocol $run fifo 0 "2"
#             done
#         done
#     done
# done

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
# RUNS="1 2 3 4 5"
# PATHS=( "Starlink_SD_NY_15_ISL_path.log" \
#         "Starlink_SD_NY_15_BP_path.log" \
#         "Starlink_SEA_NY_15_ISL_path.log" \
#         "Starlink_SEA_NY_15_BP_path.log" \
#         "Starlink_SD_SEA_15_ISL_path.log" \
#         "Starlink_SD_SEA_15_BP_path.log" 
#         "Starlink_NY_LDN_15_ISL_path.log" \
#         "Starlink_SD_Shanghai_15_ISL_path.log" )
# QUEUE_PKTS=(522 408 388 326 582 219 696 740)

# for protocol in $PROTOCOLS; do
#     for idx in "${!PATHS[@]}"; do
#         path="${PATHS[$idx]}"
#         pkts="${QUEUE_PKTS[$idx]}"
#         for run in $RUNS; do
#             run experiments_mininet/LeoEM/emulator.py "$path" [0] 100 "$pkts" "$protocol" "$run" 300
#         done
#     done
# done


# PROTOCOLS="satcpbbr1"
# RUNS="6"
# PATHS=(  "Starlink_SD_SEA_15_ISL_path.log" )
# #\
# #         "Starlink_SD_SEA_15_BP_path.log"  ) 219
# QUEUE_PKTS=( 582 )

# for protocol in $PROTOCOLS; do
#     for idx in "${!PATHS[@]}"; do
#         path="${PATHS[$idx]}"
#         pkts="${QUEUE_PKTS[$idx]}"
#         for run in $RUNS; do
#             run experiments_mininet/LeoEM/emulator.py "$path" [0] 100 "$pkts" "$protocol" "$run" 100
#             sudo killall ss_script_iperf
#             sudo killall ss_script_sage
#         done
#     done
# done


# PROTOCOLS="ping"
# RUNS="1"

# # PATHS="Starlink_SEA_NY_15_ISL_path.log Starlink_SD_SEA_15_ISL_path.log Starlink_NY_LDN_15_ISL_path.log Starlink_SD_NY_15_BP_path.log Starlink_SD_NY_15_ISL_path.log Starlink_SEA_NY_15_BP_path.log Starlink_SD_Shanghai_15_ISL_path.log Starlink_SD_SEA_15_BP_path.log"
# PATHS=""
# for protocol in $PROTOCOLS
# do
#         for path in $PATHS
#         do 
#                 for run in $RUNS
#                 do
#                         run experiments_mininet/LeoEM/emulator.py $path [0] 1000 10000 $protocol $run 300
#                 done
#         done
# done


