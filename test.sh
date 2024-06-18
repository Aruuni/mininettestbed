bash setup.sh
PROTOCOLS="orca"
BANDWIDTHS="100"
DELAYS="2"
RUNS="1"  
QMULTS="0.2"
AQMS='fifo'

FLOWS='2'

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
             sudo python experiments/fairness_intra_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
         done
     done
     done
     done
     done
     done

# FLOWS='4'


# for bw in $BANDWIDTHS
# do
# for del in $DELAYS
# do
# for qmult in $QMULTS
# do
# for flow in $FLOWS
# do
#    for protocol in $PROTOCOLS
#    do
#    for aqm in $AQMS
#    do
#        for run in $RUNS
#        do
#            time sudo python3.7 experiments/fairness_aqm.py $del $bw $qmult $protocol $run $aqm 0 $flow
#        done
#    done
#    done
#    done
#    done
#    done
# done