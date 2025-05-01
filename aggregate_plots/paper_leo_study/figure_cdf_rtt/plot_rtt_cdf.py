import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import json
import os, sys
import matplotlib as mpl
import numpy as np
from matplotlib.pyplot import figure
from matplotlib.lines import Line2D
plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import *

BW = 50
DELAY = 50
QMULT = 1
RUNS = list(range(1, 51))
BINS = 50

def get_rtt_df(ROOT_PATH, RUNS, BW, DELAY, QMULT):
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    start_time = 0
    end_time = 300
    data = []

    for protocol in PROTOCOLS_LEO:
        for run in RUNS:
            PATH = f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{run}"
            with open(f"{PATH}/emulation_info.json", 'r') as fin:
                emulation_info = json.load(fin)
            rtt_capacities = [x[-1][2] for x in filter(lambda elem: elem[6] == 'netem', emulation_info['flows'])]
            optimal_mean = sum(rtt_capacities) / len(rtt_capacities)
            if protocol == 'astraea' or protocol == 'vivace-uspace':
                if os.path.exists(f"{PATH}/csvs/c1.csv"):
                    rtt_data = pd.read_csv(f"{PATH}/csvs/c1.csv").reset_index(drop=True)
                    rtt_data['time'] = rtt_data['time'].apply(lambda x: int(float(x)))
                    rtt_data = rtt_data[(rtt_data['time'] > start_time) & (rtt_data['time'] < end_time)]
                    rtt_data = rtt_data.drop_duplicates('time').set_index('time')
                    mean_rtt = rtt_data.mean()['srtt']
                    data.append([protocol, run, mean_rtt, optimal_mean])
            if os.path.exists(f"{PATH}/csvs/c1_ss.csv"):
                rtt_data = pd.read_csv(f"{PATH}/csvs/c1_ss.csv").reset_index(drop=True)
                rtt_data['time'] = rtt_data['time'].apply(lambda x: int(float(x)))
                rtt_data = rtt_data[(rtt_data['time'] > start_time) & (rtt_data['time'] < end_time)]
                rtt_data = rtt_data.drop_duplicates('time').set_index('time')
                mean_rtt = rtt_data.mean()['srtt']
                data.append([protocol, run, mean_rtt, optimal_mean])

    COLUMNS = ['protocol', 'run_number', 'srtt', 'optimal_srtt']
    return pd.DataFrame(data, columns=COLUMNS)

# Load RTT Data
rtt_data_bw_rtt = get_rtt_df(f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_leo/fifo", RUNS, BW, DELAY, QMULT)
rtt_data_loss = get_rtt_df(f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_loss_leo/fifo", RUNS, BW, DELAY, QMULT)

fig, ax = plt.subplots(figsize=(3, 1.8))
fig.subplots_adjust(left=0.15, right=0.98, bottom=0.15, top=0.80)

# Base RTT (“link capacity”) lines
optimals = rtt_data_bw_rtt[rtt_data_bw_rtt['protocol'] == 'cubic']['optimal_srtt']
vals, bins = np.histogram(optimals, bins=BINS)
cum = np.cumsum(vals)
optimal_line, =ax.plot(
    bins[:-1], cum / 50 * 100,
    c='black', linestyle='-', linewidth=1.0
)

optimals_loss = rtt_data_loss[rtt_data_loss['protocol'] == 'cubic']['optimal_srtt']
vals, bins = np.histogram(optimals_loss, bins=BINS)
cum = np.cumsum(vals)

protocol_handles = []
protocol_labels = []

for protocol in PROTOCOLS_LEO:
    # “rtt” curve
    rtts = rtt_data_bw_rtt[rtt_data_bw_rtt['protocol'] == protocol]['srtt']
    vals, bins = np.histogram(rtts, bins=BINS)
    cum = np.cumsum(vals)
    line, = ax.plot(
        bins[:-1], cum / 50 * 100,
        c=COLORS_LEO[protocol], linewidth=1.0
    )
    # “loss” curve (dashed)
    rtts_loss = rtt_data_loss[rtt_data_loss['protocol'] == protocol]['srtt']
    vals, bins = np.histogram(rtts_loss, bins=BINS)
    cum = np.cumsum(vals)
    ax.plot(
        bins[:-1], cum / 50 * 100,
        c=COLORS_LEO[protocol], linestyle='--', linewidth=1.0
    )
    protocol_handles.append(line)
    protocol_labels.append(PROTOCOLS_FRIENDLY_NAME_LEO[protocol])

# Axes labels & limits
ax.set(xlabel="Average RTT (ms)", ylabel="Percent of Trials (%)")
ax.set_xlim(30, None)

# Top‐center global legend (link capacity + protocols)
all_handles = [optimal_line] + protocol_handles
all_labels = ['Optimal'] + protocol_labels
fig.legend(
    all_handles, all_labels,
    loc='upper center', bbox_to_anchor=(0.5, 1),
    ncol=3, frameon=False,
    fontsize=7, columnspacing=1.0,
    handlelength=2.5, handletextpad=0.7
)

# Legend for loss and no loss legends
ax.legend(
    [Line2D([], [], 
        color='black', 
        linestyle='-', 
        linewidth=1.0
    ), 
    Line2D([], [], 
        color='black', 
        linestyle='--', 
        linewidth=1.0
    )],
    ['bw-rtt', 'bw-rtt-loss'],
    loc='upper left',
    frameon=False,
    fontsize=6,
    handlelength=2,
    handletextpad=0.5,
    labelspacing=0.2
)
# Save out
fig.savefig("joined_rtt_cdf.pdf", dpi=720, bbox_inches='tight')