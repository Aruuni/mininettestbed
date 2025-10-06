source common.sh
bash setup.sh

PROTOCOLS="astraea-tcpdatagen"
BANDWIDTHS="20 50 100 200"
DELAYS="10 20 40 50 100"
RUNS="1"
QMULTS="1 2 8"
FLOWS="2"

PROTOCOLS="cubic"
BANDWIDTHS="100"
DELAYS="20"
RUNS="2"
QMULTS="1"
FLOWS="2"

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
#                         run experiments/tcpdatagen/single_flow.py $del $bw $qmult $protocol $run fifo 0 $flow
#                     done
#                 done
#             done
#         done
#     done
# done

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
                        run experiments/custom/experiment_custom.py $del $bw $qmult $protocol $run fifo 0 $flow
                    done
                done
            done
        done
    done
done