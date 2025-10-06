#!/bin/bash
source common.sh
bash setup.sh

# PROTOCOLS="sage"
# PROTOCOLS="astraea cubic bbr3 vivace-uspace"
# PROTOCOLS="vivace-uspace"
PROTOCOLS="sage-new"
STEPS="10 20 30 40 50 60 70 80 90 100"
bwSTEPS="150 200 250 300 350 400 450 500"
FLOWS_STEPS="3 5 7 9 11 13 15 17 19 21"
QMULTS="0.2 1 4"
RUNS="1 2 3 4 5"
HOPS="3 5 6"

# FAIRNESS INTRA RTT 
for del in $STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments/fairness/experiment_intra_rtt_fairness.py $del "100" $qmult $protocol $run fifo 0 "2"
            done
        done
    done
done


#FAIRNESS INTER RTT
for del in $STEPS
do
   for qmult in $QMULTS
   do
       for protocol in $PROTOCOLS
       do
           for run in $RUNS
           do
               run experiments/fairness/experiment_inter_rtt_fairness.py $del "100" $qmult $protocol $run sfq 0 "2"
           done
       done
   done
done

# FAIRNESS BANDWIDTH
for bw in $bwSTEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments/fairness/experiment_intra_bw_fairness.py "20" $bw $qmult $protocol $run fifo 0 "2"
            done
        done  
    done
done

# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY WITH FLOWS
for flows in $FLOWS_STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
              run experiments/friendly/experiment_cubic_flow_friendliness.py "15" "100" $qmult $protocol $run fifo 0 $flows
            done
        done
    done
done

# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY
for del in $STEPS
do
   for qmult in $QMULTS
   do
       for protocol in $PROTOCOLS
       do
           for run in $RUNS
           do
              run experiments/friendly/experiment_cubic_rtt_friendliness.py $del "100" $qmult $protocol $run fifo 0 "2"
           done
       done
   done
done


# CUBIC COEXISTANCE/BACKWARDS COMPATIBILITY [INVERSE]
DELAYPOINT="50"
for qmult in $QMULTS
do
   for protocol in $PROTOCOLS
   do
       for run in $RUNS
       do
           run experiments/friendly/experiment_cubic_rtt_friendliness_inverse.py $DELAYPOINT "100" $qmult $protocol $run fifo 0 "2"
       done
   done
done

# RESPONSIVENESS BW RTT 
for protocol in $PROTOCOLS
do
    for run in {1..50}
    do
        run experiments/responsiveness/experiment_responsiveness_bw_rtt.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done

# RESPONSIVENESS LOSS
for protocol in $PROTOCOLS
do
    for run in {1..50}
    do
        run experiments/responsiveness/experiment_responsiveness_bw_loss.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done

# EFFICIENCY/CONVERGENCE 
DELAY="10 100"
DELAY="50"
AQMS='fifo sfq fq_codel fq_pie cake'

for del in $DELAY
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for aqm in $AQMS
            do
                for run in $RUNS
                do
                    run experiments/fairness/experiment_fairness_aqm.py $del "100" $qmult $protocol $run $aqm 0 "4"
                done
            done
        done
    done
done

# PARKING LOT TOPOLOGY INTRA RTT
for del in $STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments/fairness/experiment_parking_lot_intra_rtt_fairness.py $del "100" $qmult $protocol $run "sfq" 0 "4"
            done
        done
    done
done


# PARKING LOT TOPOLOGY INTRA RTT
for del in $STEPS
do
    for hop in $HOPS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments/fairness/experiment_parking_lot_hop_count.py $del "100" "1" $protocol $run "fifo" 0 $hop
            done
        done
    done
done

