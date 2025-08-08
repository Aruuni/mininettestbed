source common.sh
bash setup.sh

# Hosts parameters
PROTOCOLS="cubic"
SUBFLOWS="8"

# Link parameters
BANDWIDTHS="10"
DELAYS="50"
LOSS="0"
QMULTS="1"
AQM="fifo"

# Controller parameters
CONTROLLERS="multipath_switch"
PATH_SELECTORS="k_shortest_pseudo_disjoint_paths" # i am bad at naming things
PATH_NUM=""


# Experiment parameters
MESH_SIZES="5"
FLOWS="5"
RUNS="3"
SEEDS="14801482"

sudo mn -c

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
                                for controller in $CONTROLLERS
                                do
                                    for run in $RUNS
                                    do  
                                        for seed in $SEEDS
                                        do
                                            run experiments_mininet/custom/experiment_manhattan_openflow.py $del $bw $qmult $protocol $run $AQM $loss $flow $subflow $mesh_size $controller $seed
                                        done
                                    done
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