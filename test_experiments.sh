sudo fuser -k 6653/tcp
sudo modprobe tcp_bbr
#sudo insmod /home/mihai/PCC-Kernel/src/tcp_pcc.ko

# PROTOCOLS="sage"
# BANDWIDTHS="100"
# DELAYS="10"
# RUNS="5"  
# QMULTS="4"
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
#            time sudo python3.7 experiments/fairness_aqm.py $del $bw $qmult $protocol $run $aqm 0 $flow
#        done
#    done
#    done
#    done
#    done
#    done
# done


PROTOCOLS="orca sage"
BANDWIDTHS="100"
DELAYS="10 100"
RUNS="1 2 3 4 5"  
QMULTS="0.2 1 4"
AQMS='fifo'
FLOWS='4'


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
   for aqm in $AQMS
   do
       for run in $RUNS
       do
           time sudo python3.7 experiments/fairness_aqm.py $del $bw $qmult $protocol $run $aqm 0 $flow
       done
   done
   done
   done
   done
   done
done