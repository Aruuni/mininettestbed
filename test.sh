bash setup.sh

# PROTOCOLS="sage"
# BANDWIDTHS="100"
# DELAYS="4"
# RUNS="1"  
# QMULTS="1"
# AQMS='fifo'
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
#            sudo python3.7 experiments/fairness_aqm.py $del $bw $qmult $protocol $run $aqm 0 $flow
#        done
#    done
#    done
#    done
#    done
#    done
# done









PROTOCOLS="aurora"
BANDWIDTHS="100"
DELAYS="3"
RUNS="1"  
QMULTS="1"
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
             sudo python3.7 experiments/fairness_intra_rtt_async.py $del $bw $qmult $protocol $run fifo 0 $flow
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


# PROTOCOLS="orca"
# BANDWIDTHS="50"
# DELAYS="50"
# RUNS="1"  
# QMULTS="1"
# AQMS='fifo'
# FLOWS='1'


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
#        for run in {1..2}
#        do
#            sudo python3.7 experiments/responsiveness_bw_rtt.py $del $bw $qmult $protocol $run $aqm 0 $flow
#        done
#    done
#    done
#    done
#    done
#    done
# done