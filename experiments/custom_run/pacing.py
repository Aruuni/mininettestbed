#!/usr/bin/env python3
"""
This script extracts pacing rate events from an ns-3 TCP log file and plots them in Mbps as a continuous line.
It searches for log lines containing "Current Pacing Rate <value>bps", converts the value
to Mbps, and then plots the pacing rate over simulation time. The plot is saved as "pacing_rate.pdf".
"""

import re
import argparse
import matplotlib.pyplot as plt

def parse_pacing_rate_events(file_path):
    """
    Parse the log file and extract pacing rate events.
    
    Pacing rate events are taken from log lines containing "Current Pacing Rate".
    The extracted rate is converted from bps to Mbps.
    
    Returns:
         A list of dictionaries, each with:
           'time': simulation time (float)
           'pacing_rate_mbps': pacing rate in Mbps (float)
    """
    pacing_events = []
    # Regular expression to extract simulation time, node id, and message.
    log_line_re = re.compile(r'^\+([\d\.]+)s\s+\d+\s+\[node\s+(\d+)\]\s+(.*)$')
    # Regular expression to extract the pacing rate (in bps) from the message.
    pacing_rate_re = re.compile(r'Current Pacing Rate\s+(\d+)\s*bps')
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            match = log_line_re.match(line)
            if not match:
                continue
            time_val = float(match.group(1))
            message = match.group(3)
            
            if "Current Pacing Rate" in message:
                pr_match = pacing_rate_re.search(message)
                if pr_match:
                    pacing_rate_bps = int(pr_match.group(1))
                    pacing_rate_mbps = pacing_rate_bps / 1e6  # convert bps to Mbps
                    pacing_events.append({
                        'time': time_val,
                        'pacing_rate_mbps': pacing_rate_mbps
                    })
    return pacing_events

def plot_pacing_rate(events, filename="pacing_rate.pdf"):
    """
    Plot pacing rate over simulation time as a continuous line.
    
    - X-axis: Simulation time (s)
    - Y-axis: Pacing rate (Mbps)
    
    The plot uses a smaller figure size and is saved as a PDF file.
    """
    if not events:
        print("No pacing rate events found in the log.")
        return
    
    times = [event['time'] for event in events]
    rates = [event['pacing_rate_mbps'] for event in events]
    
    plt.figure(figsize=(5, 3))  # smaller plot size
    plt.plot(times, rates, linestyle='-', color='red')  # continuous line plot
    plt.xlabel("Simulation Time (s)")
    plt.ylabel("Pacing Rate (Mbps)")
    plt.title("Pacing Rate Over Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Extract and plot pacing rate from an ns-3 TCP log file."
    )
    parser.add_argument("logfile", help="Path to the TCP log file")
    args = parser.parse_args()
    
    events = parse_pacing_rate_events(args.logfile)
    print("Total pacing rate events extracted:", len(events))
    
    if events:
        plot_pacing_rate(events, filename="pacing_rate.pdf")
        print("Pacing rate plot saved as pacing_rate.pdf")
    else:
        print("No pacing rate events found in the log.")

if __name__ == "__main__":
    main()
