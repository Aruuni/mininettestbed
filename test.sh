bash setup.sh
PROTOCOLS="orca"
BANDWIDTHS="100"
DELAYS="10"
RUNS="1"  
QMULTS="0.2"
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