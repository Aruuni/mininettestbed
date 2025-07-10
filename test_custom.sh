source common.sh
bash setup.sh

PROTOCOLS="bbr"
BANDWIDTHS="100"
DELAYS="20"
RUNS="1"
QMULTS=".2"
FLOWS="1"

for bw in $BANDWIDTHS
do
    for del in $DELAYS
    do
        for qmult in $QMULTS
        do
            for flow in $FLOWS
            do
                for protocol in $PROTOCOLS
                do
                    for run in $RUNS
                    do
                        run experiments_mininet/custom/experiment_basic_mp.py $del $bw $qmult $protocol $run fifo 0 $flow
                    done
                done
            done
        done
    done
done

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