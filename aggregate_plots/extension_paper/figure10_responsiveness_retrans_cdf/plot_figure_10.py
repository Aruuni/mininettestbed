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
from matplotlib.ticker import LogLocator, FuncFormatter, FixedLocator, Formatter, ScalarFormatter
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

            log_path = f"{PATH}/sysstat/etcp_c1.log"
            if os.path.exists(log_path):
                systat1 = pd.read_csv(log_path, sep=';').rename(columns={"# hostname": "hostname"})
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

                valid = True
            else:
                valid = False

            if valid:
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
fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(3,1.5))
ax = axes

# optimals = loss_data[loss_data['protocol'] == 'cubic']['retr_rate']
# values, base = np.histogram(optimals, bins=BINS)
# cumulative = np.cumsum(values)
# ax.plot(base[:-1], cumulative/50*100, c='black')

# Plot each protocol’s data
for protocol in PROTOCOLS_EXTENSION:
    # RTT scenario
    avg_rates_rtt = bw_rtt_data[bw_rtt_data['protocol'] == protocol]['average_retr_rate']
    values, base = np.histogram(avg_rates_rtt, bins=BINS)
    cumulative = np.cumsum(values)
    ax.plot(base[:-1], cumulative/50*100, label=f"{protocol}-rtt", c=COLORS_EXTENSION[protocol])

    # Loss scenario
    avg_rates_loss = loss_data[loss_data['protocol'] == protocol]['average_retr_rate']
    values, base = np.histogram(avg_rates_loss, bins=BINS)
    cumulative = np.cumsum(values)
    ax.plot(base[:-1], cumulative / 50 * 100, label=f"{protocol}-loss",
            c=COLORS_EXTENSION[protocol], linestyle='dashed')

ax.set(xlabel="Average Retr. Rate (Mbps)", ylabel="Percentage of Trials (%)")

def clean_log_format(x, pos):
    if x < 0.1:
        return f"{x:.3f}".rstrip('0').rstrip('.')
    elif x < 1:
        return f"{x:.2f}".rstrip('0').rstrip('.')
    else:
        return f"{x:.0f}"

ax.set_xscale('log')
ax.set_xticks([0.001, 0.01, 0.1, 1, 10, 100])
ax.xaxis.set_major_formatter(FuncFormatter(clean_log_format))
ax.xaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(1, 10)*0.1, numticks=100))

fig.legend(
    ncol=3, loc='upper center',
    bbox_to_anchor=(0.5, 1.50),
    columnspacing=0.5,
    handletextpad=0.5,
    handlelength=1
)
fig.savefig("joined_retr_cdf_log.pdf", dpi=1080)
