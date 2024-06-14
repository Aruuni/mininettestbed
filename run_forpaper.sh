PROTOCOLS="bbr"
BANDWIDTHS="100"
DELAYS="20"
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
            sudo python3 experiments/fairness_friendly_rtt_async_inverse.py $del $bw $qmult $protocol $run fifo 0 $flow
        done
    done
    done
    done
    done
    done