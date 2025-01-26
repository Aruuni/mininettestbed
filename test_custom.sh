source common.sh
bash setup.sh

PROTOCOLS="astraea"
BANDWIDTHS="100"
DELAYS="20"
RUNS="1"
QMULTS="1"
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
                        run experiments_mininet/custom/experiment_custom.py $del $bw $qmult $protocol $run fifo 0 $flow
                    done
                done
            done
        done
    done
done


                               # delay bw qmult protocol run qdisc loss flows
             #   run experiments_mininet/parking_lot/experiment_parking_lot.py "20" "100" "1" "astraea" "1" "fifo" 0 "4"
