source common.sh
bash setup.sh

PROTOCOLS="bbr"
BANDWIDTHS="50"
DELAYS="15 30 45 60 75 90"
RUNS="1 2 3 4 5"
QMULTS="0.2 1 4"
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
