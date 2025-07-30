source common.sh
bash setup.sh

PROTOCOLS="cubic"
BANDWIDTHS="100"
DELAYS="50"
RUNS="3"
QMULTS="2"
FLOWS="6"
LOSS="0"

AQM="fifo"
SUBFLOWS="8"
MESH_SIZES="5"

# MANHATTAN RANDOM POSITIONS
for bw in $BANDWIDTHS
do
    for del in $DELAYS
    do
        for qmult in $QMULTS
        do
            for flow in $FLOWS
            do
                for loss in $LOSS
                do
                    for subflow in $SUBFLOWS
                    do
                        for mesh_size in $MESH_SIZES
                        do
                            for protocol in $PROTOCOLS
                            do
                                for run in $RUNS
                                do
                                    run experiments_mininet/custom/experiment_manhattan_varied.py $del $bw $qmult $protocol $run $AQM $loss $flow $subflow $mesh_size
                                done
                            done
                        done
                    done
                done
            done
        done
    done
done


# PROTOCOLS="cubic"
# BANDWIDTHS="103"
# DELAYS="5"
# RUNS="1"
# QMULTS=".2"
# FLOWS="5"

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
#                         run experiments_mininet/custom/experiment_manhattan_anim.py $del $bw $qmult $protocol $run fifo 0 $flow
#                     done
#                 done
#             done
#         done
#     done
# done

# STEPS="10 20 30 40 50 60 70 80 90 100"
# QMULTS="0.2 1 4"
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