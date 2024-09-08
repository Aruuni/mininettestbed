 PROTOCOLS="bbr1"
 BANDWIDTHS="150"
 DELAYS="10 20 30 40 50 60 70 80 90 100"
 RUNS="1"
 QMULTS="1"
 FLOWS="1"

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
             time sudo python3 experiments/single_flow_handover.py $del $bw $qmult $protocol $run fifo 0 $flow
         done
     done
     done
     done
     done
     done
