#!/bin/bash
 PROTOCOLS="cubic bbr bbr1"
 BANDWIDTHS="100"
 DELAYS="10 20 30 40 50 60 70 80 90 100"
 RUNS="1 2"
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
             sudo python3 experiments/fairness_intra_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
         done
     done
     done
     done
     done
     done