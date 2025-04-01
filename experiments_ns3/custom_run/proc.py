#!/usr/bin/env python3
"""
This script extracts SACK events from an ns-3 TCP log file and plots them as horizontal bars.
It handles two SACK formats:
  1. Sender-side events with lines like:
       ns3::TcpOptionSack(blocks: 3,[5052001,5247001][4534501,5050501][4011001,4533001])
  2. Receiver-side events with lines like:
       +3.455186480s 1  [node 1] TcpSocketBase:AddOptionSack(): [INFO ] 1 Add option SACK {[2536501;2566501]}
       +3.647722320s 1  [node 1] TcpSocketBase:AddOptionSack(): [INFO ] 1 Add option SACK {[4534501;4873501][4011001;4533001]}
       
Each SACK block is plotted as a horizontal bar at its simulation time, with the x‑axis showing the sequence range.
The plot is saved as a PDF file.
"""

import re
import argparse
import matplotlib.pyplot as plt

def parse_sack_events(file_path):
    """
    Parse the log file and extract SACK events.
    
    Returns:
         A list of dictionaries, each with:
           'time': simulation time (float)
           'node': node id (int)
           'sack_blocks': list of tuples (start, end)
           'message': the full log message (string)
    """
    sack_events = []
    # Regular expression to extract simulation time, node number, and message.
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
            
            # --- Process sender-side SACK events: look for "TcpOptionSack(" ---
            if re.search(r'TcpOptionSack\(', message, re.IGNORECASE):
                sack_match = re.search(r'TcpOptionSack\(([^)]+)\)', message, re.IGNORECASE)
                if sack_match:
                    sack_str = sack_match.group(1)
                    # Extract blocks of the form [number, number]
                    blocks = re.findall(r'\[(\d+),\s*(\d+)\]', sack_str)
                    sack_blocks = [(int(start), int(end)) for start, end in blocks]
                    if sack_blocks:
                        sack_events.append({
                            'time': time_val,
                            'node': node,
                            'sack_blocks': sack_blocks,
                            'message': message
                        })
            
            # --- Process receiver-side SACK events: look for "AddOptionSack(" ---
            if re.search(r'AddOptionSack\(', message, re.IGNORECASE):
                sack_match = re.search(r'Add\s+option\s+SACK\s*\{([^}]+)\}', message, re.IGNORECASE)
                if sack_match:
                    sack_str = sack_match.group(1)
                    # Extract blocks in the form [number;number]
                    blocks = re.findall(r'\[(\d+);(\d+)\]', sack_str)
                    sack_blocks = [(int(start), int(end)) for start, end in blocks]
                    if sack_blocks:
                        sack_events.append({
                            'time': time_val,
                            'node': node,
                            'sack_blocks': sack_blocks,
                            'message': message
                        })
    
    return sack_events

def plot_sack_bars(sack_events, filename="sack_events.pdf"):
    """
    Plot SACK blocks as horizontal bars using matplotlib's broken_barh.
    
    - X-axis: Sequence numbers (range of each block)
    - Y-axis: Simulation time (each block is centered at its event time)
    
    Blocks from node 0 (sender) are drawn in blue;
    blocks from node 1 (receiver) are drawn in green.
    The plot is saved as a PDF file.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_height = 0.05  # Fixed vertical height for each bar.
    
    for event in sack_events:
        t = event['time']
        y = t - bar_height / 2.0  # Center the bar at t.
        for block in event['sack_blocks']:
            start = block[0]
            width = block[1] - block[0]
            # Use blue for sender (node 0) and green for receiver (node 1).
            color = 'blue' if event['node'] == 0 else 'green'
            ax.broken_barh([(start, width)], (y, bar_height), facecolors=color)
    
    ax.set_xlabel("Sequence Number")
    ax.set_ylabel("Simulation Time (s)")
    ax.set_title("SACK Blocks Over Time")
    ax.grid(True)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Extract and plot SACK events from an ns-3 TCP log file."
    )
    parser.add_argument("logfile", help="Path to the TCP log file")
    args = parser.parse_args()
    
    sack_events = parse_sack_events(args.logfile)
    print("Total SACK events extracted:", len(sack_events))
    
    if sack_events:
        plot_sack_bars(sack_events, filename="sack_events.pdf")
        print("SACK events plot saved as sack_events.pdf")
    else:
        print("No SACK events found in the log.")

if __name__ == "__main__":
    main()
