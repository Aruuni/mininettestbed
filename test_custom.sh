source common.sh
bash setup.sh
sudo insmod tcp_pcc.ko

PROTOCOLS="astraea"
BANDWIDTHS="100"
DELAYS="25"
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
                        run experiments_mininet/custom/experiment_custom.py $del $bw $qmult $protocol $run fifo 1 $flow
                    done
                done
            done
        done
    done
done
