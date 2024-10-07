source common.sh
bash setup.sh


PROTOCOLS="bbr"
BANDWIDTHS="100"
DELAYS="10"
RUNS="1"  
QMULTS="1"
AQMS='fifo'
FLOWS='5'


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
                    for aqm in $AQMS
                    do
                        for run in $RUNS
                        do
                            run experiments/fairness_parking_lot.py $del $bw $qmult $protocol $run $aqm 0 $flow
                        done
                    done
                done
            done
        done
    done
done