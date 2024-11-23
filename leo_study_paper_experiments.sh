#!/bin/bash
source common.sh
bash setup.sh

# PROTOCOLS="bbr cubic pcc"
# PROTOCOLS="orca sage"
# PROTOCOLS="bbr3"

QMULTS="0.2 1 4"
RUNS="1 2 3 4 5"
STEPS="10 20 30 40 50 60 70 80 90 100"
cSTEPS="90"


# FAIRNESS INTRA RTT 

for del in $STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments_mininet/intra_rtt_fairness/experiment.py $del "100" $qmult $protocol $run fifo 0 "2"
            done
        done
    done
done


# FAIRNESS INTER RTT

for del in $STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments_mininet/inter_rtt_fairness/experiment.py $del "100" $qmult $protocol $run fifo 0 "2"
            done
        done
    done
done


# FAIRNESS BANDWIDTH

for bw in $STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments_mininet/intra_bw_fairness/experiment.py "20" $bw $qmult $protocol $run fifo 0 "2"
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
                run experiments_mininet/cubic_rtt_friendliness/experiment.py $del "100" $qmult $protocol $run fifo 0 "2"
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
            run experiments_mininet/cubic_rtt_friendliness_inverse/experiment.py $DELAYPOINT "100" $qmult $protocol $run fifo 0 "2"
        done
    done
done
    

# RESPONSIVENESS BANDWIDTH/RTT FOR LEO PAPER

for protocol in $PROTOCOLS
do
    for run in {1..50}
    do
        run experiments_mininet/responsiveness_bw_rtt_leo/experiment.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done


# RESPONSIVENESS BANDWIDTH/RTT/LOSS FOR LEO PAPER

for protocol in $PROTOCOLS
do
    for run in {1..50}
    do
        run experiments_mininet/responsiveness_bw_rtt_loss_leo/experiment.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done

# RESPONSIVENESS BW RTT 

for protocol in $PROTOCOLS
do
    for run in {1..50}
    do
        run experiments_mininet/responsiveness_bw_rtt/experiment.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done


# RESPONSIVENESS LOSS

for protocol in $PROTOCOLS
do
    for run in {35..50}
    do
        run experiments_mininet/responsiveness_loss/experiment.py "50" "50" "1" $protocol $run fifo 0 "1"
    done
done


# EFFICIENCY/CONVERGENCE 

BANDWIDTH="100"
DELAY="10 100"
AQMS='fifo'

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
                    run experiments_mininet/fairness_aqm/experiment.py $del "100" $qmult $protocol $run $aqm 0 "4"
                done
            done
        done
    done
done


# PARKING LOT TOPOLOGY

for del in $STEPS
do
    for qmult in $QMULTS
    do
        for protocol in $PROTOCOLS
        do
            for run in $RUNS
            do
                run experiments_mininet/parking_lot/experiment.py $del "100" $qmult $protocol $run "fifo" 0 "4"
            done
        done
    done
done


# Fairness Cross path Inter

# for del in $STEPS
# do
#     for qmult in $QMULTS
#     do
#         for protocol in $PROTOCOLS
#         do
#             for run in $RUNS
#             do
#                 run experiments_mininet/inter_rtt_fairness.py $del "100" $qmult $protocol $run fifo 0 "2"
#             done
#         done
#     done
# done
