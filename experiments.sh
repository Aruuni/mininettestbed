#!/bin/bash
source common.sh
bash setup.sh

# PROTOCOLS="astraea orca bbr1 bbr3 cubic vivace"
# PROTOCOLS="sage"
# STEPS="10 20 30 40 50 60 70 80 90 100"
# QMULTS="0.2 1 4"
# RUNS="1 2 3 4 5"

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


# # FAIRNESS INTER RTT
# for del in $cSTEPS
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/inter_rtt_fairness/experiment_inter_rtt_fairness.py $del "100" $qmult $protocol $run fifo 0 "2"
#             done
#         done
#     done
# done


# # FAIRNESS BANDWIDTH
# for bw in $STEPS
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/intra_bw_fairness/experiment_intra_bw_fairness.py "20" $bw $qmult $protocol $run fifo 0 "2"
#             done
#         done  
#     done
# done


# # CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY
# for del in $STEPS
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/cubic_rtt_friendliness/experiment_cubic_rtt_friendliness.py $del "100" $qmult $protocol $run fifo 0 "2"
#             done
#         done
#     done
# done


# # CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY [INVERSE]
# DELAYPOINT="50"

# for qmult in $QMULTS
# do
#     for protocol in $PROTOCOLS
#     do
#         for run in $RUNS
#         do
#             run experiments_mininet/cubic_rtt_friendliness_inverse/experiment_cubic_rtt_friendliness_inverse.py $DELAYPOINT "100" $qmult $protocol $run fifo 0 "2"
#         done
#     done
# done
    

# # RESPONSIVENESS BANDWIDTH/RTT FOR LEO PAPER
# for protocol in $PROTOCOLS
# do
#     for run in {1..50}
#     do
#         run experiments_mininet/responsiveness_bw_rtt_leo/experiment_responsiveness_bw_rtt_leo.py "50" "50" "1" $protocol $run fifo 0 "1"
#     done
# done


# # RESPONSIVENESS BANDWIDTH/RTT/LOSS FOR LEO PAPER
# for protocol in $PROTOCOLS
# do
#     for run in {1..50}
#     do
#         run experiments_mininet/responsiveness_bw_rtt_loss_leo/experiment_responsiveness_bw_rtt_loss_leo.py "50" "50" "1" $protocol $run fifo 0 "1"
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


# PROTOCOLS="bbr cubic pcc"
PROTOCOLS="astraea orca bbr1 bbr3 cubic vivace"



# QMULTS="0.2 1 4"
# RUNS="1 2 3 4 5"
## left at 60  queue size 1
# need astraea and orca 10 to 60 full 


# aSteps="5 15 25 35 45"
# hSTEPS="5 10 15 20 25 30 35 40 45 50"

STEPS="10 20 30 40 50 60 70 80 90 100"
HOPS="3 5 6"
RUNS="1 2 3 4 5"

# PARKING LOT TOPOLOGY INTRA RTT
for del in $STEPS
do
    for hop in $HOPS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments_mininet/fairness_parking_lot_hop_count/experiment_parking__lot_hop_count.py $del "100" "1" $protocol $run "fifo" 0 $hop
            done
        done
    done
done













# # Fairness Cross path Inter
# for del in $STEPS
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