import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import json
import os, sys
import matplotlib as mpl
import numpy as np
plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../../..')
sys.path.append( mymodule_dir )
from core.config import *
BW = 50         # in Mbit
DELAY = 50      # in ms
QMULT = 1
run = 1         # using run 1 as an example
start_time = 0
end_time = 300

# Calculate BDP in bytes and in packets (assuming packet size = 1500 bytes)
BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
BDP_IN_PKTS = BDP_IN_BYTES / 1500

# Define protocols and colors
PROTOCOLS = ['cubic', 'astraea', 'bbr3', 'bbr1', 'sage']
COLOR = {
    'cubic': '#0C5DA5',
    'bbr1': '#00B945',
    'bbr3': '#FF9500',
    'sage': '#FF2C01',
    'orca': '#845B97',
    'astraea': '#845B97',
}

# Root paths for the two conditions
ROOT_RTT = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_leo/fifo"
ROOT_LOSS = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_loss_leo/fifo"

def load_time_series(ROOT_PATH, protocol, run):
    """
    Loads the CSV file (x1.csv) for the specified protocol and run.
    Returns a DataFrame filtered between start_time and end_time.
    """
    PATH = os.path.join(
        ROOT_PATH,
        f"Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}",
        f"run{run}"
    )
    csv_path = os.path.join(PATH, 'csvs', 'x1.csv')
    if not os.path.exists(csv_path):
        print(f"CSV file not found for protocol {protocol} in run {run} at {csv_path}")
        return None

    df = pd.read_csv(csv_path).reset_index(drop=True)
    # Convert time to integer seconds
    df['time'] = df['time'].apply(lambda x: int(float(x)))
    # Filter data within the desired time range and remove duplicate time entries
    df = df[(df['time'] > start_time) & (df['time'] < end_time)]
    df = df.drop_duplicates('time').set_index('time')
    return df

# Create a grid: 5 protocols (rows) x 2 columns (non-loss and loss)
fig, axs = plt.subplots(nrows=len(PROTOCOLS), ncols=2, figsize=(10, 8), sharex=True, sharey=True)

for i, protocol in enumerate(PROTOCOLS):
    # Left subplot: non-loss condition (solid line)
    ax_non_loss = axs[i, 0]
    # Right subplot: loss condition (dotted line)
    ax_loss = axs[i, 1]
    
    # Load non-loss (RTT) time series
    df_non_loss = load_time_series(ROOT_RTT, protocol, run)
    if df_non_loss is not None:
        ax_non_loss.plot(
            df_non_loss.index, 
            df_non_loss['bandwidth'], 
            linestyle='-',  # solid line for non-loss
            c=COLOR[protocol]
        )
    # Load loss time series
    df_loss = load_time_series(ROOT_LOSS, protocol, run)
    if df_loss is not None:
        ax_loss.plot(
            df_loss.index, 
            df_loss['bandwidth'], 
            linestyle=':',  # dotted line for loss
            c=COLOR[protocol]
        )
    
    # Set subplot titles and labels
    ax_non_loss.set_title(f"{protocol} non-loss", fontsize=10)
    ax_loss.set_title("loss", fontsize=10)
    
    # Only add y-label on left column
    ax_non_loss.set_ylabel("Goodput (Mbps)", fontsize=9)
    # Add grid for both subplots
    ax_non_loss.grid(True)
    ax_loss.grid(True)

# Set common x-label for the bottom row
axs[-1, 0].set_xlabel("Time (s)", fontsize=9)
axs[-1, 1].set_xlabel("Time (s)", fontsize=9)

fig.tight_layout()

# Save the figure (adjust file format and DPI as needed)
for fmt in ['pdf']:
    fig.savefig(f"goodput_evolution_side_by_side_run{run}.{fmt}", dpi=720)

plt.savefig("goodput_evolution_side_by_side_run1.png", dpi=720)
