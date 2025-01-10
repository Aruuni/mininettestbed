#!/usr/bin/env bash

SOURCE_DIR="/home/mihai/cctestbed/ns3/results_responsiveness_bw_rtt_loss_leo/fifo/Dumbell_50mbit_50ms_436pkts_0loss_1flows_22tcpbuf_bbr"
DEST_DIR="/home/mihai/Desktop/NS3-Results_bbr_loss_responsiveness"

# Create destination folder if it doesn't exist
mkdir -p "$DEST_DIR"

for i in $(seq 1 50); do
    # Create the run folder under the destination
    mkdir -p "$DEST_DIR/run$i"

    # Copy the PDF only
    cp "$SOURCE_DIR/run$i/ns3_experiment_results.pdf" "$DEST_DIR/run$i/"
done