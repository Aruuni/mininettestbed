PROTOCOLS="bbr"
QMULTS="1"
RUNS="1"

# FAIRNESS INTRA RTT 

BANDWIDTHS="100"
DELAYS="10"
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
                        python experiments_ns3/fairness_intra_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
                    done
                done
            done
        done
    done
done
