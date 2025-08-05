#!/bin/bash
source common.sh
bash setup.sh

PROTOCOLS="sage"
PROTOCOLS="bbr3 cubic vivace-uspace astraea"

STEPS="10 20 30 40 50 60 70 80 90 100"
QMULTS="0.2 1 4"
RUNS="1 2 3 4 5"
HOPS="3 5 6"
AQMS='cake fq_codel fifo fq_pie'

# FAIRNESS INTRA RTT
for del in $STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments_mininet/fairness/experiment_intra_rtt_fairness.py $del "100" $qmult $protocol $run fifo 0 "2"
            done
        done
    done
done

# FAIRNESS INTER RTT
for del in $resumeSTEPS
do
   for qmult in $QMULTS
   do
       for protocol in $PROTOCOLS
       do
           for run in $RUNS
           do
               run experiments_mininet/fairness/experiment_inter_rtt_fairness.py $del "100" $qmult $protocol $run fifo 0 "2"
           done
       done
   done
done

# RESPONSIVENESS BANDWIDTH/RTT
for protocol in $PROTOCOLS
do
    for run in {1..50}
    do
        run experiments_mininet/responsiveness/experiment_responsiveness_bw_rtt_leo.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done

# RESPONSIVENESS BANDWIDTH/RTT/LOSS
for protocol in $PROTOCOLS
do
    for run in {1..50}
    do
         run experiments_mininet/responsiveness/experiment_responsiveness_bw_rtt_loss_leo.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done

# PARKING LOT TOPOLOGY INTRA RTT
for del in $STEPS
do
    for protocol in $PROTOCOLS
    do
        for run in $RUNS
        do
            run experiments_mininet/fairness/experiment_parking_lot_intra_rtt_fairness.py $del "100" "1" $protocol $run "sfq" 0 "4"
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
                run experiments_mininet/fairness/experiment_parking_lot_hops_intra_rtt_fairness.py $del "100" "1" $protocol $run "fifo" 0 $hop
            done
        done
    done
done

# Fairness Cross path Inter
for qmult in $QMULTS
do
    for protocol in $PROTOCOLS
    do
        for run in $RUNS
        do
            run experiments_mininet/cross_path/experiment_cross_path_intra.py "10" "100" $qmult $protocol $run fifo 0 "2"
        done
    done
done

# EFFICIENCY/CONVERGENCE
for protocol in $PROTOCOLS
do
    for aqm in $AQMS
    do
        for run in $RUNS
        do
            run experiments_mininet/efficiency_aqm/experiment_aqm.py "25" "100" "1" $protocol $run $aqm 0 "5"
        done
    done
done
