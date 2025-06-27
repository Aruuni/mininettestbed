import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter, LogLocator, LogFormatter, FuncFormatter, NullFormatter
import numpy as np
from mpl_toolkits.axes_grid1 import ImageGrid
import numpy as np


plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 


EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_friendly_intra_rtt_async/fifo" 
BWS = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
RUNS = [1, 2, 3, 4, 5]
LOSSES=[0]

for mult in QMULTS:
    data = []
    for protocol in PROTOCOLS_EXTENSION:
        for bw in BWS:
            for delay in DELAYS:
                start_time = 3*delay
                end_time = 4*delay

                BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                BDP_IN_PKTS = BDP_IN_BYTES / 1500

                goodput_ratios_total = []

                for run in RUNS:
                    PATH = f"{EXPERIMENT_PATH}/Dumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{run}" 
                    if os.path.exists(f"{PATH}/csvs/x1.csv") and os.path.exists(f"{PATH}/csvs/x2.csv"):
                        receiver1_total = pd.read_csv(f"{PATH}/csvs/x1.csv").reset_index(drop=True)
                        receiver2_total = pd.read_csv(f"{PATH}/csvs/x2.csv").reset_index(drop=True)

                        receiver1_total['time'] = receiver1_total['time'].apply(lambda x: int(float(x)))
                        receiver2_total['time'] = receiver2_total['time'].apply(lambda x: int(float(x)))

                        receiver1_total = receiver1_total[(receiver1_total['time'] > start_time) & (receiver1_total['time'] < end_time)]
                        receiver2_total = receiver2_total[(receiver2_total['time'] > start_time) & (receiver2_total['time'] < end_time)]

                        receiver1_total = receiver1_total.drop_duplicates('time')
                        receiver2_total = receiver2_total.drop_duplicates('time')

                        receiver1_total = receiver1_total.set_index('time')
                        receiver2_total = receiver2_total.set_index('time')

                        total = receiver1_total.join(receiver2_total, how='inner', lsuffix='1', rsuffix='2')[['bandwidth1', 'bandwidth2']]
                        total['bandwidth1'] = total['bandwidth1'].clip(lower=1)
                        total['bandwidth2'] = total['bandwidth2'].clip(lower=1)
                        ratio = total['bandwidth2'] / total['bandwidth1']
                        print(ratio)
                        goodput_ratios_total.append(ratio)
                    else:
                        print(f"Folder {PATH} not found.")

                if len(goodput_ratios_total) > 0:
                    goodput_ratios_total = np.concatenate(goodput_ratios_total, axis=0)

                    if len(goodput_ratios_total) > 0:
                        data_entry = [protocol, bw, delay, delay/10, mult, goodput_ratios_total.mean(), goodput_ratios_total.std()]
                        data.append(data_entry)

    summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])
    fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
    ax = axes

    for protocol in PROTOCOLS_EXTENSION:
        plot_points(ax, summary_data[summary_data['protocol'] == protocol].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std', PROTOCOLS_MARKERS_EXTENSION[protocol], COLORS_EXTENSION[protocol], PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol], delay=True)

    ax.set(yscale='log',xlabel='RTT (ms)', ylabel='Goodput Ratio', ylim=[0.011, 101])
    # x-axis remains linear; use ScalarFormatter to keep “100”, “200”, … style
    # 1) nuke all x‐ticks & labels

    # 1) Explicitly pin the major ticks to the decades you want:
    decades = [1e-2, 1e-1, 1e0, 1e1, 1e2]
    ax.set_yticks(decades)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f"{y:g}"))

    # 3) minor y‐ticks at 2×,3×,…,9× each decade
    ax.yaxis.set_minor_locator(LogLocator(base=10, subs=range(2, 10), numticks=50))
    ax.yaxis.set_minor_formatter(NullFormatter())

    # 4) give them a little tick‐length so you actually see them
    ax.tick_params(axis='y', which='minor', length=4)
    ax.tick_params(axis='y', which='major', length=6)

    # handles, labels = ax.get_legend_handles_labels()
    # handles = [h[0] for h in handles]
    # legend = fig.legend(handles, labels,ncol=3, loc='upper center',bbox_to_anchor=(0.5, 1.30),columnspacing=0.8,handletextpad=0.5)

    plt.savefig(f"goodput_friendly_rtt_qmult{mult}.pdf", dpi=1080)
















