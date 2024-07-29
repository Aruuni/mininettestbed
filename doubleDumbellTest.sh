bash setup.sh

PROTOCOLS="bbr"
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
   for aqm in $AQMS
   do
       for run in $RUNS
       do
           sudo python3 experiments/fairness_cross_traffic.py $del $bw $qmult $protocol $run $aqm 0 $flow
       done
   done
   done
   done
   done
   done
done