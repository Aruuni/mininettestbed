import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import matplotlib as mpl
from matplotlib.pyplot import figure

# Mandatory import settings
plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../../..')
sys.path.append(mymodule_dir)
from core.config import *

mpl.rcParams.update({'font.size': 12})
pd.set_option('display.max_rows', None)

# --- Constants and Settings ---
PROTOCOLS = ['cubic', 'astraea', 'bbr3', 'bbr1', 'sage']
BW = 50                # Bandwidth in Mbit/s
DELAY = 50             # Delay in ms
QMULT = 1
RUN = 16               # Run number to use
BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
BDP_IN_PKTS = BDP_IN_BYTES / 1500
start_time = 100       # Time window start (s)
end_time = 200         # Time window end (s)
LINEWIDTH = 2          # Thicker lines

# Colors for protocols
COLOR = {
    'cubic':   '#0C5DA5',
    'bbr1':    '#00B945',
    'bbr3':    '#FF9500',
    'sage':    '#FF2C01',
    'astraea': '#845B97'
}

# Updated ROOT paths for the experiments
ROOT_PATH_no_loss = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_leo/fifo"
ROOT_PATH_loss    = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_loss_leo/fifo"

# --- Create a figure with 5 subplots (side by side, left to right) ---
fig, axes = plt.subplots(1, len(PROTOCOLS), figsize=(15, 3), sharex=True)
if len(PROTOCOLS) == 1:
    axes = [axes]

for ax, protocol in zip(axes, PROTOCOLS):
    # Create a twin axis for the secondary metric (RTT or Loss Rate)
    ax2 = ax.twinx()
    
    # Build the paths for the current protocol (non-loss and loss experiments)
    PATH_no = os.path.join(
        ROOT_PATH_no_loss,
        f'Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{RUN}'
    )
    PATH_loss = os.path.join(
        ROOT_PATH_loss,
        f'Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{RUN}'
    )
    
    # Debug prints for paths and data verification
    print(f"Protocol: {protocol}")
    print("Non-loss Path:", PATH_no)
    print("Loss Path:", PATH_loss)
    
    # --- Load Data for the Non-Loss Experiment ---
    sender_no = None
    capacity_no = None
    min_rtt = None
    csv_no = os.path.join(PATH_no, 'csvs/c1.csv')
    info_no = os.path.join(PATH_no, 'emulation_info.json')
    if not os.path.exists(csv_no):
        print(f"File not found: {csv_no}")
    if not os.path.exists(info_no):
        print(f"File not found: {info_no}")
    if os.path.exists(csv_no) and os.path.exists(info_no):
        sender_no = pd.read_csv(csv_no).reset_index(drop=True)
        sender_no['time'] = sender_no['time'].apply(lambda x: int(float(x)))
        sender_no = sender_no[(sender_no['time'] > start_time) & (sender_no['time'] < end_time)]
        if sender_no.empty:
            print(f"No data in CSV for protocol {protocol} in non-loss experiment after filtering time.")
        else:
            print(f"Non-loss sender data for {protocol} (first few rows):")
            print(sender_no.head())
        sender_no = sender_no.drop_duplicates('time').set_index('time')
        with open(info_no, 'r') as fin:
            emulation_info = json.load(fin)
        flows = list(filter(lambda elem: start_time <= elem[4] <= end_time, emulation_info['flows']))
        capacity_flows = list(filter(lambda elem: elem[5] == 'tbf', flows))
        if capacity_flows:
            capacity_no = [x[-1][1] for x in capacity_flows]
        rtt_flows = list(filter(lambda elem: elem[5] == 'netem', flows))
        if rtt_flows:
            min_rtt = [x[-1][2] for x in rtt_flows]
    
    # --- Load Data for the Loss Experiment ---
    sender_loss = None
    capacity_loss = None
    loss_rate = None
    csv_loss = os.path.join(PATH_loss, 'csvs/c1.csv')
    info_loss = os.path.join(PATH_loss, 'emulation_info.json')
    if not os.path.exists(csv_loss):
        print(f"File not found: {csv_loss}")
    if not os.path.exists(info_loss):
        print(f"File not found: {info_loss}")
    if os.path.exists(csv_loss) and os.path.exists(info_loss):
        sender_loss = pd.read_csv(csv_loss).reset_index(drop=True)
        sender_loss['time'] = sender_loss['time'].apply(lambda x: int(float(x)))
        sender_loss = sender_loss[(sender_loss['time'] > start_time) & (sender_loss['time'] < end_time)]
        if sender_loss.empty:
            print(f"No data in CSV for protocol {protocol} in loss experiment after filtering time.")
        else:
            print(f"Loss sender data for {protocol} (first few rows):")
            print(sender_loss.head())
        sender_loss = sender_loss.drop_duplicates('time').set_index('time')
        with open(info_loss, 'r') as fin:
            emulation_info_loss = json.load(fin)
        flows_loss = list(filter(lambda elem: start_time <= elem[4] <= end_time, emulation_info_loss['flows']))
        capacity_loss_flows = list(filter(lambda elem: elem[5] == 'tbf', flows_loss))
        if capacity_loss_flows:
            capacity_loss = [x[-1][1] for x in capacity_loss_flows]
        loss_flows = list(filter(lambda elem: elem[5] == 'netem', flows_loss))
        if loss_flows:
            loss_rate = [x[-1][-2] for x in loss_flows]
    
    # --- Plot on Primary Axis (Left): Sender Bandwidth and Link Capacity ---
    step_times = np.arange(start_time, end_time + 1, 10)
    if sender_no is not None and not sender_no.empty:
        ax.plot(
            sender_no.index + 1,
            sender_no['bandwidth'],
            linewidth=LINEWIDTH,
            label='BW (non-loss)',
            color=COLOR[protocol],
            linestyle='-'
        )
    else:
        print(f"No non-loss sender data for protocol {protocol}")
    if sender_loss is not None and not sender_loss.empty:
        ax.plot(
            sender_loss.index + 1,
            sender_loss['bandwidth'],
            linewidth=LINEWIDTH,
            label='BW (loss)',
            color=COLOR[protocol],
            linestyle='--'
        )
    else:
        print(f"No loss sender data for protocol {protocol}")
    if capacity_no is not None:
        ax.step(
            step_times,
            capacity_no,
            where='post',
            color='black',
            linewidth=0.5 * LINEWIDTH,
            label='Capacity (non-loss)',
            alpha=0.5
        )
    if capacity_loss is not None:
        ax.step(
            step_times,
            capacity_loss,
            where='post',
            color='black',
            linewidth=0.5 * LINEWIDTH,
            linestyle='dashed',
            label='Capacity (loss)',
            alpha=0.5
        )
    
    # --- Plot on Secondary Axis (Right): min RTT and Loss Rate ---
    if min_rtt is not None:
        ax2.step(
            step_times,
            min_rtt,
            where='post',
            color='red',
            linewidth=0.5 * LINEWIDTH,
            label='min RTT',
            linestyle='dashed',
            alpha=0.5
        )
    if loss_rate is not None:
        ax2.step(
            step_times,
            loss_rate,
            where='post',
            color='blue',
            linewidth=0.5 * LINEWIDTH,
            label='Loss Rate',
            linestyle='-.',
            alpha=0.5
        )
    
    # --- Set subplot titles and labels ---
    ax.set_title(protocol)
    ax.set_xlabel("Time (s)")
    if ax == axes[0]:
        ax.set_ylabel("Sending Rate (Mbps)")
    ax2.set_ylabel("min RTT (ms) / Loss Rate (%)")

# --- Create a common legend for all subplots ---
lines_labels = [ax.get_legend_handles_labels() for ax in axes]
lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
fig.legend(lines, labels, ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.10),
           columnspacing=0.5, handletextpad=0.5, handlelength=1)

fig.tight_layout(rect=[0, 0, 1, 0.95])
for fmt in ['pdf']:
    fig.savefig(f"joined_sending_rate_combined.{fmt}", dpi=720)
plt.show()
