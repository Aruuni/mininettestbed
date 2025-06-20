import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter
import numpy as np

plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 

EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_handover_hard/fifo" 
BW = 100
DELAY = 25
INTERRUPTS = [20, 40 , 60, 80, 100, 120, 140, 160, 180, 200]
QMULT = 1
data = []
for protocol in PROTOCOLS_LEO:
    for interupt in INTERRUPTS:
        start_time = 3*DELAY
        end_time = 4*DELAY-1
        keep_last_seconds = int(0.25*DELAY)

        BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
        BDP_IN_PKTS = BDP_IN_BYTES / 1500

        goodputs_total = []
        for run in RUNS:
            PATH = f"{EXPERIMENT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{interupt}ms_interrupt_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{run}" 
            if os.path.exists(f"{PATH}/csvs/x1.csv"):
                goodput = pd.read_csv(f"{PATH}/csvs/x1.csv").reset_index(drop=True)
                goodput = goodput[['time', 'bandwidth']]
                goodput['time'] = goodput['time'].apply(lambda x: int(float(x)))
                goodput = goodput[(goodput['time'] > start_time) & (goodput['time'] < end_time)]
                goodput = goodput.drop_duplicates('time')

                goodput = goodput.set_index('time')

                goodput = goodput[(goodput['bandwidth'] > 0)]
                goodputs_total.append(goodput)

            else:
                print(f"Folder {PATH} not found.")

        if  len(goodputs_total) > 0:
            goodputs_total = np.concatenate(goodputs_total, axis=0)   
            data_entry = [protocol, BW, DELAY, QMULT, interupt, goodputs_total.mean(), goodputs_total.std()]
            data.append(data_entry)

    summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'qmult', 'inerrupt', 'goodput_total_mean', 'goodput_total_std'])
fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
ax = axes
for protocol in PROTOCOLS_LEO:
    plot_points(ax, summary_data[summary_data['protocol'] == protocol].set_index('inerrupt'), 'goodput_total_mean', 'goodput_total_std', PROTOCOLS_MARKERS_LEO[protocol], COLORS_LEO[protocol], PROTOCOLS_FRIENDLY_NAME_LEO[protocol], False)


ax.set(yscale='linear',xlabel='Interrupt time (ms)', ylabel='Goodput')
for axis in [ax.xaxis, ax.yaxis]:
    axis.set_major_formatter(ScalarFormatter())
handles, labels = ax.get_legend_handles_labels()
handles = [h[0] for h in handles]
leg1 = fig.legend(
    handles[:3], labels[:3],
    ncol=3,
    loc='upper center',
    bbox_to_anchor=(0.5, 1.15),
    frameon=False,
    fontsize=7,
    columnspacing=0.8,
    handlelength=2.5,
    handletextpad=0.5
)
fig.add_artist(leg1)

leg2 = fig.legend(
    handles[3:], labels[3:],
    ncol=2,
    loc='upper center',
    bbox_to_anchor=(0.5, 1.05),
    frameon=False,
    fontsize=7,
    columnspacing=0.8,
    handlelength=2.5,
    handletextpad=0.5
)

#legend = fig.legend(handles, labels,ncol=3, loc='upper center',bbox_to_anchor=(0.5, 1.30),columnspacing=0.8,handletextpad=0.5)
plt.savefig(f"Avg_goodput_eth2.pdf" , dpi=1080)
