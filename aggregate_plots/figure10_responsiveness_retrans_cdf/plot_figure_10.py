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
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)
from core.config import *
from core.plotting import *

def get_df(ROOT_PATH, PROTOCOLS, RUNS, BW, DELAY, QMULT, loss=False):
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    start_time = 0
    end_time = 300

    data = []
    for protocol in PROTOCOLS:
        for run in RUNS:
            PATH = (
                f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_"
                f"{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{run}"
            )
            with open(f"{PATH}/emulation_info.json", 'r') as fin:
                emulation_info = json.load(fin)

            retr_mean = 0
            if loss:
                retr_rate = list(filter(lambda elem: elem[6] == 'netem', emulation_info['flows']))
                retr_rate = [x[-1][6] for x in retr_rate]
                if retr_rate:
                    retr_mean = np.mean(retr_rate)


            if protocol != 'vivace-uspace' and os.path.exists(f"{PATH}/sysstat/etcp_c1.log"):
                systat1 = pd.read_csv(f"{PATH}/sysstat/etcp_c1.log", sep=';').rename(columns={"# hostname": "hostname"})
                retr1 = systat1[['timestamp', 'retrans/s']]

                diff = retr1.diff()
                ind = diff.index[diff['timestamp'] >= 10].tolist()
                if ind:
                    shift_start = ind[0]
                    if shift_start >= 0:
                        retr1 = retr1.loc[shift_start + 1:, :]

                start_timestamp = retr1['timestamp'].iloc[0]
                time_diff = retr1['timestamp'].iloc[-1] - start_timestamp
                if not (time_diff <= 300):
                    continue

                retr1['timestamp'] = retr1['timestamp'] - start_timestamp + 1
                retr1 = retr1.rename(columns={'timestamp': 'time'})
            
            if protocol == 'vivace-uspace' and  os.path.exists(f"{PATH}/csvs/c1.csv"):
                systat1 = pd.read_csv(PATH + '/csvs/c1.csv').rename(columns={"retr": "retrans/s"})
                retr1 = systat1[['time', 'retrans/s']].copy()



            retr1['time'] = retr1['time'].apply(lambda x: int(float(x)))
            retr1 = retr1.drop_duplicates('time')

            retr1_total = retr1[(retr1['time'] > start_time) & (retr1['time'] < end_time)]
            retr1_total = retr1_total.set_index('time')

            avg_retrans_s = retr1_total['retrans/s'].mean()  # could be NaN if no data
            if not np.isnan(avg_retrans_s):
                rate_mbps = avg_retrans_s * 1500.0 * 8.0 / (1024.0 * 1024.0)
            else:
                rate_mbps = 0.0

            data.append([protocol, run, rate_mbps, retr_mean])

    COLUMNS = ['protocol', 'run_number', 'average_retr_rate', 'retr_rate']
    return pd.DataFrame(data, columns=COLUMNS)


BW = 50
DELAY = 50
QMULT = 1
RUNS_L = list(range(1,51))

bw_rtt_data = get_df(
    ROOT_PATH=f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt/fifo",
    PROTOCOLS=PROTOCOLS_EXTENSION,
    RUNS=RUNS_L,
    BW=BW,
    DELAY=DELAY,
    QMULT=QMULT
)

loss_data = get_df(
    ROOT_PATH=f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_loss/fifo",
    PROTOCOLS=PROTOCOLS_EXTENSION,
    RUNS=RUNS_L,
    BW=BW,
    DELAY=DELAY,
    QMULT=QMULT,
    loss=True
)

BINS = 50
fig, ax = plt.subplots(figsize=(3, 1.8)) 
fig.subplots_adjust(left=0.15, right=0.98, bottom=0.15, top=0.80)

optimals = bw_rtt_data[bw_rtt_data['protocol'] == 'cubic']['retr_rate']
vals, bins = np.histogram(optimals, bins=BINS)
cum = np.cumsum(vals)
# bw_rtt_line_handle, = ax.plot(
#     bins[:-1], cum / 50 * 100,
#     c='black', linestyle='-', linewidth=1.0
# )

optimals_loss = loss_data[loss_data['protocol'] == 'cubic']['retr_rate']
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
    data_rtt = bw_rtt_data[bw_rtt_data['protocol'] == protocol]['average_retr_rate']
    vals, bins = np.histogram(data_rtt, bins=BINS)
    cum = np.cumsum(vals)
    line, = ax.plot(bins[:-1], cum / 50 * 100, c=COLORS_EXTENSION[protocol], linewidth=1.0)
    protocol_handles.append(line)
    protocol_labels.append(PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol])
    
    # loss data
    data_loss = loss_data[loss_data['protocol'] == protocol]['average_retr_rate']
    vals, bins = np.histogram(data_loss, bins=BINS)
    cum = np.cumsum(vals)
    ax.plot(bins[:-1], cum / 50 * 100, c=COLORS_EXTENSION[protocol], linestyle='--', linewidth=1.0)

ax.set(xlabel="Average Goodput (Mbps)", ylabel="Percentage of Trials (%)")
# ax.annotate(
#     'link capacity',
#     xy=(76, 50), xytext=(32, 20), color='black',
#     arrowprops=dict(arrowstyle="->", linewidth=0.5, color='black')
# )
#ax.set_xlim(0, None)


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

fig.savefig("joined_retr_cdf.pdf", dpi=1080)
