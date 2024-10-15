source common.sh
bash setup.sh

PROTOCOLS="bbr"
BANDWIDTHS="100"
DELAYS="15"
RUNS="1"
QMULTS="1"
FLOWS="3"

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
                        run experiments/cross_traffic.py $del $bw $qmult $protocol $run fifo 0 $flow
                    done
                done
            done
        done
    done
done
