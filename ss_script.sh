#!/bin/bash

# Ensure the script receives the required arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <interval> <experiment_path> "
    exit 1
fi

INTERVAL=$1
OUTPUT_FILE=$2

while true; do
    ./ss -tin | sed -En \
        -e 's/.* cwnd:([0-9]*).* ssthresh:([0-9]*).* bytes_sent:([0-9]*).* bytes_retrans:([0-9]*).* bytes_acked:([0-9]*).*/\1;\2;\3;\4;\5;/p'  \
        | ts '%.s;' \
        >> "$OUTPUT_FILE"
    sleep 0.1
done &
# -e 's/.* cwnd:([0-9]*).* ssthresh:([0-9]*).*/\1;\2;/p' \
# -e 's/.* cwnd:([0-9]*).* rtt:([0-9.]*).* minrtt:([0-9.]*).* data_segs_in:([0-9]*).* data_segs_out:([0-9]*).* delivered:([0-9]*).*$/\1;\2;\3;\4;\5;\6/p' \

# sample output
#ESTAB    0         346072            10.0.0.1:4444            10.0.0.3:40624    
#cubic wscale:9,9 rto:208 rtt:4.065/0.03 ato:40 mss:1448 pmtu:1500 rcvmss:536 advmss:1448 cwnd:21 ssthresh:20 bytes_sent:3602128 bytes_retrans:205616 bytes_acked:3369000 bytes_received:38 segs_out:2489 segs_in:515 data_segs_out:2488 data_segs_in:1 send 59.8Mbps lastrcv:604 pacing_rate 62.0Mbps delivery_rate 48.6Mbps delivered:2328 busy:604ms unacked:19 retrans:0/142 rcv_space:14600 rcv_ssthresh:42230 notsent:318560 minrtt:4