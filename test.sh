 PROTOCOLS="cubic bbr"
 BANDWIDTHS="100"
 DELAYS="10"
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
            sudo python3 experiments/fairness_friendly_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
        done
    done
    done
    done
    done
    done