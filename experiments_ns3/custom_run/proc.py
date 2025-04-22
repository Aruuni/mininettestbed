#!/usr/bin/env python3
"""
This script extracts sequence numbers from an ns-3 TCP log file and plots them separately for the sender and receiver.

Sender-side events are extracted from log lines containing:
    TcpSocketBase:SendDataPacket(..., <seq>, ...)

Receiver-side events are extracted from log lines containing:
    TcpSocketBase:ReceivedData(... Seq=<seq> ...)

Each plot shows simulation time (s) on the x‑axis and the sequence number on the y‑axis.
The sender plot is saved as "sender_sequence_numbers.pdf"
and the receiver plot as "receiver_sequence_numbers.pdf".
"""

import re
import argparse
import matplotlib.pyplot as plt

def parse_sender_sequence_events(file_path):
    """
    Parse the log file and extract sender-side sequence numbers.
    
    Sender events are taken from log lines containing "SendDataPacket" from node 0.
    The sequence number is assumed to be the second argument in the function call.
    
    Returns:
         A list of dictionaries, each with:
           'time': simulation time (float)
           'seq': the sequence number (int)
    """
    sender_events = []
    # Regular expression to extract simulation time, node id and message.
    log_line_re = re.compile(r'^\+([\d\.]+)s\s+\d+\s+\[node\s+(\d+)\]\s+(.*)$')
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            match = log_line_re.match(line)
            if not match:
                continue
            time_val = float(match.group(1))
            node = int(match.group(2))
            message = match.group(3)
            
            # Filter for sender (node 0) and lines with "SendDataPacket"
            if node == 0 and "SendDataPacket" in message:
                # Example: TcpSocketBase:SendDataPacket(0x577d3742e1a0, 3916501, 1500, 1)
                seq_match = re.search(r'SendDataPacket\([^,]+,\s*(\d+),', message)
                if seq_match:
                    seq_num = int(seq_match.group(1))
                    sender_events.append({'time': time_val, 'seq': seq_num})
    
    return sender_events

def parse_receiver_sequence_events(file_path):
    """
    Parse the log file and extract receiver-side sequence numbers.
    
    Receiver events are taken from log lines containing "ReceivedData" from node 1.
    The sequence number is extracted from the pattern "Seq=<number>" in the log message.
    
    Returns:
         A list of dictionaries, each with:
           'time': simulation time (float)
           'seq': the sequence number (int)
    """
    receiver_events = []
    log_line_re = re.compile(r'^\+([\d\.]+)s\s+\d+\s+\[node\s+(\d+)\]\s+(.*)$')
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            match = log_line_re.match(line)
            if not match:
                continue
            time_val = float(match.group(1))
            node = int(match.group(2))
            message = match.group(3)
            
            # Filter for receiver (node 1) and lines with "ReceivedData"
            if node == 1 and "ReceivedData" in message:
                # Look for "Seq=<number>" in the message.
                seq_match = re.search(r'Seq=(\d+)', message)
                if seq_match:
                    seq_num = int(seq_match.group(1))
                    receiver_events.append({'time': time_val, 'seq': seq_num})
    
    return receiver_events

def plot_sender_sequence_numbers(events, filename="sender_sequence_numbers.pdf"):
    """
    Plot sender sequence numbers as a scatter plot.
    
    - X-axis: Simulation time (s)
    - Y-axis: Sequence number
    The plot is saved as a PDF file.
    """
    if not events:
        print("No sender sequence events found in the log.")
        return

    times = [e['time'] for e in events]
    seqs = [e['seq'] for e in events]
    
    plt.figure(figsize=(10, 6))
    plt.scatter(times, seqs, color='blue', label='Sender Seq')
    plt.xlabel("Simulation Time (s)")
    plt.ylabel("Sequence Number")
    plt.title("Sender Sequence Numbers Over Time")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def plot_receiver_sequence_numbers(events, filename="receiver_sequence_numbers.pdf"):
    """
    Plot receiver sequence numbers as a scatter plot.
    
    - X-axis: Simulation time (s)
    - Y-axis: Sequence number
    The plot is saved as a PDF file.
    """
    if not events:
        print("No receiver sequence events found in the log.")
        return

    times = [e['time'] for e in events]
    seqs = [e['seq'] for e in events]
    
    plt.figure(figsize=(10, 6))
    plt.scatter(times, seqs, color='green', label='Receiver Seq')
    plt.xlabel("Simulation Time (s)")
    plt.ylabel("Sequence Number")
    plt.title("Receiver Sequence Numbers Over Time")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Extract and plot sequence numbers from an ns-3 TCP log file."
    )
    parser.add_argument("logfile", help="Path to the TCP log file")
    args = parser.parse_args()
    
    # Parse sequence events for sender and receiver
    sender_events = parse_sender_sequence_events(args.logfile)
    receiver_events = parse_receiver_sequence_events(args.logfile)
    
    print("Total sender sequence events extracted:", len(sender_events))
    print("Total receiver sequence events extracted:", len(receiver_events))
    
    # Plot sender sequence numbers
    plot_sender_sequence_numbers(sender_events, filename="sender_sequence_numbers.pdf")
    print("Sender sequence numbers plot saved as sender_sequence_numbers.pdf")
    
    # Plot receiver sequence numbers
    plot_receiver_sequence_numbers(receiver_events, filename="receiver_sequence_numbers.pdf")
    print("Receiver sequence numbers plot saved as receiver_sequence_numbers.pdf")

if __name__ == "__main__":
    main()
