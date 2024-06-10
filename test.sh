sudo fuser -k 6653/tcp
sudo modprobe tcp_bbr
sudo modprobe tcp_cubic
sudo mn -c

PROTOCOLS="aurora"
BANDWIDTHS="100"
DELAYS="10"
RUNS="1"
QMULTS="1"
FLOWS="4"

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
            time sudo python3 experiments/fairness_aqm.py $del $bw $qmult $protocol $run fifo 0 $flow
        done
    done
    done
    done
    done
    done