#!/bin/bash
source common.sh
bash setup.sh

PROTOCOLS="bbr"
QMULTS="0.2 1 4"
RUNS="1 2 3 4 5"

# FAIRNESS INTRA RTT 

# BANDWIDTHS="100"
# DELAYS="10 20 30 40 50 60 70 80 90 100"
# FLOWS="2"

# for bw in $BANDWIDTHS
#     do
#         for del in $DELAYS
#         do
#             for qmult in $QMULTS
#             do
#                 for flow in $FLOWS
#                 do
#                     for protocol in $PROTOCOLS
#                     do
#                         for run in $RUNS
#                         do
#                             run experiments/fairness_intra_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
#                         done
#                     done
#                 done
#             done
#         done
#     done
# done

# FAIRNESS INTER RTT

# BANDWIDTHS="100"
# DELAYS="100"
# FLOWS="2"

# for bw in $BANDWIDTHS
# do
#     for del in $DELAYS
#     do
#         for qmult in $QMULTS
#         do
#             for flow in $FLOWS
#             do
#                 for protocol in $PROTOCOLS
#                 do
#                     for run in $RUNS
#                     do
#                         run experiments/fairness_inter_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
#                     done
#                 done
#             done
#         done
#     done
# done

# FAIRNESS BANDWIDTH

# BANDWIDTHS="10 20 30 40 50 60 70 80 90 100"
# DELAYS="20"
# FLOWS="2"

# for bw in $BANDWIDTHS
# do
#     for del in $DELAYS
#     do
#         for qmult in $QMULTS
#         do
#             for flow in $FLOWS
#             do
#                 for protocol in $PROTOCOLS
#                 do
#                     for run in $RUNS
#                     do
#                         run experiments/fairness_bw_async.py $del $bw $qmult $protocol $run fifo 0 $flow
#                     done
#                 done
#             done
#         done
#     done
# done

# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY

# BANDWIDTHS="100"
# DELAYS="10 20 30 40 50 60 70 80 90 100"
# FLOWS="2"

# for bw in $BANDWIDTHS
# do
#     for del in $DELAYS
#     do
#         for qmult in $QMULTS
#         do
#             for flow in $FLOWS
#             do
#                 for protocol in $PROTOCOLS
#                 do
#                     for run in $RUNS
#                     do
#                         run experiments/fairness_friendly_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
#                     done
#                 done
#             done
#         done
#     done
# done

# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY [INVERSE]

# BANDWIDTHS="100"
# DELAYS="50"
# FLOWS="2"

# for bw in $BANDWIDTHS
# do
#     for del in $DELAYS
#     do
#         for qmult in $QMULTS
#         do
#             for flow in $FLOWS
#             do
#                 for protocol in $PROTOCOLS
#                 do
#                     for run in $RUNS
#                     do
#                         run experiments/fairness_friendly_rtt_async_inverse.py $del $bw $qmult $protocol $run fifo 0 $flow
#                     done
#                 done
#             done
#         done
#     done
# done

# RESPONSIVENESS BANDWIDTH/RTT 

BANDWIDTH="50"
DELAY="50"
QUEUE="1"
AQMS='fifo'
FLOWS='1'

for bw in $BANDWIDTH
do
    for del in $DELAY
    do
        for qmult in $QUEUE
        do
            for flow in $FLOWS
            do
                for protocol in $PROTOCOLS
                do
                    for aqm in $AQMS
                    do
                        for run in {1..1}
                        do
                            run experiments/responsiveness_bw_rtt_leo.py $del $bw $qmult $protocol $run $aqm 0 $flow
                        done
                    done
                done
            done
        done
   done
done

# RESPONSIVENESS LOSS

# BANDWIDTH="50"
# DELAY="50" 
# QUEUE="1"
# AQMS='fifo'
# FLOWS='1'


# for bw in $BANDWIDTH
# do
#     for del in $DELAY
#     do
#         for qmult in $QUEUE
#         do
#             for flow in $FLOWS
#             do
#                 for protocol in $PROTOCOLS
#                 do
#                     for aqm in $AQMS
#                     do
#                         for run in {1..50}
#                         do
#                             run experiments/responsiveness_loss.py $del $bw $qmult $protocol $run $aqm 0 $flow
#                         done
#                     done
#                 done
#             done
#         done
#     done
# done

# EFFICIENCY/CONVERGENCE 

# BANDWIDTH="100"
# DELAY="10 100"
# AQMS='fifo'
# FLOWS='4'


# for bw in $BANDWIDTH
# do
#     for del in $DELAY
#     do
#         for qmult in $QMULTS
#         do
#             for flow in $FLOWS
#             do
#                 for protocol in $PROTOCOLS
#                 do
#                     for aqm in $AQMS
#                     do
#                         for run in $RUNS
#                         do
#                             run experiments/fairness_aqm.py $del $bw $qmult $protocol $run $aqm 0 $flow
#                         done
#                     done
#                 done
#             done
#         done
#     done
# done