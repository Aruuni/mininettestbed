source common.sh
bash setup.sh

PROTOCOLS="snap"
BANDWIDTHS="5"
DELAYS="10"
RUNS="1"
QMULTS="10"
FLOWS="2"

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
                        run oracle_test/experiment_custom.py $del $bw $qmult $protocol $run fifo 0 $flow
                    done
                done
            done
        done
    done
done


                               # delay bw qmult protocol run qdisc loss flows
             #   run experiments_mininet/parking_lot/experiment_parking_lot.py "20" "100" "1" "astraea" "1" "fifo" 0 "4"
