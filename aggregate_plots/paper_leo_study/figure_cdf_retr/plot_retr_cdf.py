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
from matplotlib.ticker import LogLocator, FuncFormatter, FixedLocator
from matplotlib.lines import Line2D
plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import *

def get_df(ROOT_PATH, RUNS, BW, DELAY, QMULT):
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    start_time = 0
    end_time = 300

    # List containing each data point (each run). Values for each datapoint: protocol, run_number, average_goodput, optimal_goodput
    data = []

    for protocol in PROTOCOLS_LEO:
        optimals = []
        for run in RUNS:
            PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_1flows_22tcpbuf_%s/run%s' % (BW, DELAY, int(QMULT * BDP_IN_PKTS), protocol, run)
            # Compute the average optimal throughput
            with open(PATH + '/emulation_info.json', 'r') as fin:
                emulation_info = json.load(fin)

            bw_capacities = list(filter(lambda elem: elem[6] == 'tbf', emulation_info['flows']))
            bw_capacities = [x[-1][1] for x in bw_capacities]
            optimal_mean = sum(bw_capacities)/len(bw_capacities)

            if protocol != 'vivace-uspace':
                if os.path.exists(PATH + '/sysstat/etcp_c1.log'):
                    systat1 = pd.read_csv(PATH + '/sysstat/etcp_c1.log', sep=';').rename(
                        columns={"# hostname": "hostname"})
                    retr1 = systat1[['timestamp', 'retrans/s']]

                    diff = retr1.diff()
                    ind = diff.index[diff['timestamp'] >= 10].tolist()
                    if len(ind) > 0:
                        ind = ind[0]
                        if ind >= 0:
                            retr1 = retr1.loc[ind+1:,:]

                    start_timestamp = retr1['timestamp'].iloc[0]


                    time_diff = retr1['timestamp'].iloc[-1] - start_timestamp
                    if not (time_diff <= 300):
                        continue


                    retr1.loc[:, 'timestamp'] = retr1['timestamp'] - start_timestamp + 1

                    retr1 = retr1.rename(columns={'timestamp': 'time'})
                    valid = True

                else:
                    valid = False
            else:
                if os.path.exists(PATH + '/csvs/c1.csv'):
                    systat1 = pd.read_csv(PATH + '/csvs/c1.csv').rename(
                        columns={"retr": "retrans/s"})
                    retr1 = systat1[['time', 'retrans/s']].copy()
                    valid = True
                else:
                    valid = False

            if valid:
                retr1['time'] = retr1['time'].apply(lambda x: int(float(x)))
                retr1 = retr1.drop_duplicates('time')
                retr1_total = retr1[(retr1['time'] > start_time) & (retr1['time'] < end_time)]
                retr1_total = retr1_total.set_index('time')
                if protocol == 'sage':
                    print(retr1_total)
                    print(f"run number: {run} protocol: {protocol}")
                data.append([protocol, run, retr1_total.mean()['retrans/s']*1500*8/(1024*1024)])

    COLUMNS = ['protocol', 'run_number', 'average_retr_rate']
    return pd.DataFrame(data, columns=COLUMNS)


BW = 50
DELAY = 50
QMULT = 1
RUNS = list(range(1,51))

bw_rtt_data = get_df(f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_leo/fifo", RUNS, BW, DELAY, QMULT)
loss_data =  get_df(f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_loss_leo/fifo", RUNS, BW, DELAY, QMULT)

BINS = 50

fig, ax = plt.subplots(figsize=(3, 1.8))
fig.subplots_adjust(left=0.15, right=0.98, bottom=0.15, top=0.80)

protocol_handles = []
protocol_labels = []
for protocol in PROTOCOLS_LEO:
    # RTT-only curve
    data_rtt = bw_rtt_data[bw_rtt_data['protocol'] == protocol]['average_retr_rate']
    vals, bins = np.histogram(data_rtt, bins=BINS)
    cum = np.cumsum(vals)
    line, = ax.plot(
        bins[:-1], cum / 50 * 100,
        c=COLORS_LEO[protocol], linewidth=1.0
    )
    # Loss curve (dashed)
    data_loss = loss_data[loss_data['protocol'] == protocol]['average_retr_rate']
    vals, bins = np.histogram(data_loss, bins=BINS)
    cum = np.cumsum(vals)
    ax.plot(
        bins[:-1], cum / 50 * 100,
        c=COLORS_LEO[protocol], linestyle='--', linewidth=1.0
    )
    protocol_handles.append(line)
    protocol_labels.append(PROTOCOLS_FRIENDLY_NAME_LEO[protocol])

ax.set(xlabel="Average Retr. Rate (Mbps)", ylabel="Percent of Trials (%)")


fig.legend(
    protocol_handles, protocol_labels,
    loc='upper center', bbox_to_anchor=(0.5, 1),
    ncol=3, frameon=False,
    fontsize=7, columnspacing=1.0,
    handlelength=2.5, handletextpad=0.7
)
bw_rtt = Line2D(
    [], [], 
    color='black', 
    linestyle='-', 
    linewidth=1.0
)

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
    loc='lower right',
    frameon=False,
    fontsize=6,
    handlelength=2,
    handletextpad=0.5,
    labelspacing=0.2
)
for ext in ['pdf']:
    fig.savefig(f"joined_retr_cdf_nonlog.{ext}", dpi=720, bbox_inches='tight')