source common.sh
bash setup.sh

PROTOCOLS="bbr"
BANDWIDTHS="50"
DELAYS="10"
RUNS="8"
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
                        run experiments_mininet/cross_path_inter/experiment.py $del $bw $qmult $protocol $run fifo 0 $flow
                    done
                done
            done
        done
    done
done
