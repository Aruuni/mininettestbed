import pandas as pd
import matplotlib.pyplot as plt
import os
import json
import numpy as np

# Color mapping for protocols
COLOR = {
    'cubic': '#0C5DA5',
    'orca': '#00B945',
    'bbr3': '#FF9500',
    'bbr': '#FF2C01',
    'sage': '#845B97',
    'pcc': '#686868',
}

# Function to get the data
def get_df(ROOT_PATH, PROTOCOLS, RUNS, BW, DELAY, QMULT):
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    start_time = 0
    end_time = 300

    data = []

    for protocol in PROTOCOLS:
        for run in RUNS:
            PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_1flows_22tcpbuf_%s/run%s' % (
                BW, DELAY, int(QMULT * BDP_IN_PKTS), protocol, run)

            # Compute the average optimal throughput
            if os.path.exists(PATH + '/csvs/x1.csv'):
                receiver = pd.read_csv(PATH + '/csvs/x1.csv').reset_index(drop=True)
                receiver['time'] = receiver['time'].apply(lambda x: int(float(x)))
                receiver = receiver[(receiver['time'] > start_time) & (receiver['time'] < end_time)]
                receiver = receiver.drop_duplicates('time')
                receiver = receiver.set_index('time')
                protocol_mean = receiver.mean()['bandwidth']
                data.append([protocol, run, protocol_mean])

    return pd.DataFrame(data, columns=['protocol', 'run_number', 'average_goodput'])


# Configuration
PROTOCOL = ['cubic']  # Only BBR protocol
BW = 50
DELAY = 50
QMULT = 1
RUNS = list(range(1, 51))

# File paths (replace these paths with your actual file paths)
HOME_DIR = os.getenv("HOME")  # Adjust this if needed
bw_rtt_path = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_leo/fifo"
loss_path = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_loss_leo/fifo"

# Load data
bw_rtt_data = get_df(bw_rtt_path, PROTOCOL, RUNS, BW, DELAY, QMULT)
loss_data = get_df(loss_path, PROTOCOL, RUNS, BW, DELAY, QMULT)

# Group data by run number
bbr_bw_rtt_avg = bw_rtt_data.groupby('run_number')['average_goodput'].mean()
bbr_loss_avg = loss_data.groupby('run_number')['average_goodput'].mean()

# Plotting
fig, ax = plt.subplots(figsize=(8, 5))

# Plot average goodput for BW-RTT experiment
ax.plot(
    bbr_bw_rtt_avg.index,
    bbr_bw_rtt_avg.values,
    label=f'{PROTOCOL[0]} (BW-RTT)',
    color=COLOR['bbr']
)

# Plot average goodput for Loss experiment with dotted line
ax.plot(
    bbr_loss_avg.index,
    bbr_loss_avg.values,
    label=f'{PROTOCOL[0]} (Loss)',
    linestyle='dotted',
    color=COLOR['bbr']
)

# Labels, title, and legend
ax.set_xlabel("Run Number")
ax.set_ylabel("Average Goodput (Mbps)")
ax.set_title(f"Average Goodput per Run for {PROTOCOL[0]}")
ax.legend()

# Save and show the plot
plt.tight_layout()
plt.savefig("bbr_goodput_per_run.png", dpi=300)
plt.show()
