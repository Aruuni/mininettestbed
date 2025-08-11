import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import json
import os, sys
import matplotlib as mpl
pd.set_option('display.max_rows', None)
import numpy as np
from matplotlib.pyplot import figure
import statistics
from matplotlib.lines import Line2D
plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 

def get_df(ROOT_PATH, PROTOCOLS, RUNS, BW, DELAY, QMULT):
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    start_time = 0
    end_time = 300

    data = []
    for protocol in PROTOCOLS:
        for run in RUNS:
            PATH = f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{run}"
            with open(f"{PATH}/emulation_info.json", 'r') as fin:
                emulation_info = json.load(fin)
            bw_capacities = list(filter(lambda elem: elem[6] == 'tbf', emulation_info['flows']))
            bw_capacities = [x[-1][1] for x in bw_capacities]
            optimal_mean = sum(bw_capacities) / len(bw_capacities)

            if os.path.exists(PATH + '/csvs/x1.csv'):
                receiver = pd.read_csv(PATH + '/csvs/x1.csv').reset_index(drop=True)

                receiver['time'] = receiver['time'].apply(lambda x: int(float(x)))

                receiver = receiver[(receiver['time'] > start_time) & (receiver['time'] < end_time)]

                receiver = receiver.drop_duplicates('time')

                receiver = receiver.set_index('time')
                protocol_mean = receiver.mean()['bandwidth']
                data.append([protocol, run, protocol_mean, optimal_mean])

    COLUMNS = ['protocol', 'run_number', 'average_goodput', 'optimal_goodput']
    return pd.DataFrame(data, columns=COLUMNS)

BW = 50
DELAY = 50
QMULT = 1
RUNS_L = list(range(1,51))

bw_rtt_data = get_df(f"/{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt/fifo" ,  PROTOCOLS_EXTENSION, RUNS_L, BW, DELAY, QMULT)
loss_data =  get_df(f"/{HOME_DIR}/cctestbed/mininet/results_responsiveness_loss/fifo" ,  PROTOCOLS_EXTENSION, RUNS_L, BW, DELAY, QMULT)

BINS = 50
fig, ax = plt.subplots(figsize=(3, 1.8)) 
fig.subplots_adjust(left=0.15, right=0.98, bottom=0.15, top=0.80)

optimals = bw_rtt_data[bw_rtt_data['protocol'] == 'cubic']['optimal_goodput']
vals, bins = np.histogram(optimals, bins=BINS)
cum = np.cumsum(vals)
bw_rtt_line_handle, = ax.plot(
    bins[:-1], cum / 50 * 100,
    c='black', linestyle='-', linewidth=1.0
)

optimals_loss = loss_data[loss_data['protocol'] == 'cubic']['optimal_goodput']
vals, bins = np.histogram(optimals_loss, bins=BINS)
cum = np.cumsum(vals)
bw_rtt_loss = Line2D(
    [], [], 
    color='black', 
    linestyle='-', 
    linewidth=1.0
)
bw_rtt_loss_line = Line2D(
    [], [], 
    color='black', 
    linestyle='--', 
    linewidth=1.0
)
protocol_handles = []
protocol_labels = []
for protocol in PROTOCOLS_EXTENSION:
    data_rtt = bw_rtt_data[bw_rtt_data['protocol'] == protocol]['average_goodput']
    vals, bins = np.histogram(data_rtt, bins=BINS)
    cum = np.cumsum(vals)
    line, = ax.plot(bins[:-1], cum / 50 * 100, c=COLORS_EXTENSION[protocol], linewidth=1.0)
    protocol_handles.append(line)
    protocol_labels.append(PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol])
    
    # loss data
    data_loss = loss_data[loss_data['protocol'] == protocol]['average_goodput']
    vals, bins = np.histogram(data_loss, bins=BINS)
    cum = np.cumsum(vals)
    ax.plot(bins[:-1], cum / 50 * 100, c=COLORS_EXTENSION[protocol], linestyle='--', linewidth=1.0)

ax.set(xlabel="Average Goodput (Mbps)", ylabel="Percentage of Trials (%)")
# ax.annotate(
#     'link capacity',
#     xy=(76, 50), xytext=(32, 20), color='black',
#     arrowprops=dict(arrowstyle="->", linewidth=0.5, color='black')
# )
# ax.set_xlim(0, None)


all_handles = protocol_handles
all_labels = protocol_labels
fig.legend(
    all_handles, all_labels,
    loc='upper center', bbox_to_anchor=(0.5, 1),
    ncol=3, frameon=False,
    fontsize=7, columnspacing=1.0,
    handlelength=2.5, handletextpad=0.7
)
ax.legend(
    [bw_rtt_loss, bw_rtt_loss_line],
    ['bw-rtt', 'bw-loss'],
    loc='lower right',
    frameon=False,
    fontsize=6,
    handlelength=2,
    handletextpad=0.5,
    labelspacing=0.2
)

fig.savefig("joined_goodput_cdf.pdf", dpi=1080)
