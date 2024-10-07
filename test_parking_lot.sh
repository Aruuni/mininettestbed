run() {
    UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')

    if [[ "$UBUNTU_VERSION" == "16.04" ]]; then
        time python3.7 "$@"
    else
        time python3 "$@"
    fi
}


bash setup.sh


PROTOCOLS="orca"
BANDWIDTHS="100"
DELAYS="10"
RUNS="1"  
QMULTS="1"
AQMS='fifo'
FLOWS='3'


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
           run experiments/fairness_parking_lot.py $del $bw $qmult $protocol $run $aqm 0 $flow
       done
   done
   done
   done
   done
   done
done