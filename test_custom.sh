source common.sh
bash setup.sh
sudo insmod PCC-Vivace/PCC-Kernel-Vivace-Loss/src/tcp_pcc.ko
PROTOCOLS="vivace-loss"
BANDWIDTHS="50"
DELAYS="25"
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
                        run experiments_mininet/custom/experiment.py $del $bw $qmult $protocol $run fifo 1 $flow
                    done
                done
            done
        done
    done
done
