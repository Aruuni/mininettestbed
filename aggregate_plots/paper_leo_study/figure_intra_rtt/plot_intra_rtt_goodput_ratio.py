import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter
import numpy as np

plt.rcParams['text.usetex'] = True
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 

EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_intra_rtt/fifo" 
BWS = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

for mult in QMULTS:
    data = []
    for protocol in PROTOCOLS_LEO:
        for bw in BWS:
            for delay in DELAYS:
                start_time = 3*delay
                end_time = 4*delay-1
                keep_last_seconds = int(0.25*delay)

                BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                BDP_IN_PKTS = BDP_IN_BYTES / 1500

                goodput_ratios_total = []
                delay_ratios_total = []
                for run in RUNS:
                    PATH = f"{EXPERIMENT_PATH}/Dumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{run}" 
                    if os.path.exists(f"{PATH}/csvs/x1.csv") and os.path.exists(f"{PATH}/csvs/x2.csv"):
                        receiver1_goodput = pd.read_csv(f"{PATH}/csvs/x1.csv").reset_index(drop=True)
                        receiver2_goodput = pd.read_csv(f"{PATH}/csvs/x2.csv").reset_index(drop=True)
                        if protocol == 'vivace-uspace' or protocol == 'astraea':
                            receiver1_srtt = pd.read_csv(f"{PATH}/csvs/c1.csv").reset_index(drop=True)
                            receiver2_srtt = pd.read_csv(f"{PATH}/csvs/c2.csv").reset_index(drop=True)
                        else:
                            receiver1_srtt = pd.read_csv(f"{PATH}/csvs/c1_ss.csv").reset_index(drop=True)
                            receiver2_srtt = pd.read_csv(f"{PATH}/csvs/c2_ss.csv").reset_index(drop=True)

                        receiver1_goodput['time'] = receiver1_goodput['time'].apply(lambda x: int(float(x)))
                        receiver2_goodput['time'] = receiver2_goodput['time'].apply(lambda x: int(float(x)))

                        receiver1_srtt['time'] = receiver1_srtt['time'].apply(lambda x: int(float(x)))
                        receiver2_srtt['time'] = receiver2_srtt['time'].apply(lambda x: int(float(x)))

                        receiver1_goodput = receiver1_goodput[(receiver1_goodput['time'] > start_time) & (receiver1_goodput['time'] < end_time)]
                        receiver2_goodput = receiver2_goodput[(receiver2_goodput['time'] > start_time) & (receiver2_goodput['time'] < end_time)]
                        receiver1_srtt = receiver1_srtt[(receiver1_srtt['time'] > start_time) & (receiver1_srtt['time'] < end_time)]
                        receiver2_srtt = receiver2_srtt[(receiver2_srtt['time'] > start_time) & (receiver2_srtt['time'] < end_time)]

                        receiver1_goodput = receiver1_goodput.drop_duplicates('time')
                        receiver2_goodput = receiver2_goodput.drop_duplicates('time')
                        receiver1_srtt = receiver1_srtt.drop_duplicates('time')
                        receiver2_srtt = receiver2_srtt.drop_duplicates('time')

                        receiver1_goodput = receiver1_goodput[receiver1_goodput['time'] <= end_time].reset_index(drop=True)
                        receiver2_goodput = receiver2_goodput[receiver2_goodput['time'] <= end_time].reset_index(drop=True)
                        receiver1_srtt = receiver1_srtt[receiver1_srtt['time'] <= end_time].reset_index(drop=True)
                        receiver2_srtt = receiver2_srtt[receiver2_srtt['time'] <= end_time].reset_index(drop=True)


                        receiver1_goodput = receiver1_goodput.set_index('time')
                        receiver2_goodput = receiver2_goodput.set_index('time')
                        receiver1_srtt = receiver1_srtt.set_index('time')
                        receiver2_srtt = receiver2_srtt.set_index('time')

                        total = receiver1_goodput.join(receiver2_goodput, how='inner', lsuffix='1', rsuffix='2')[['bandwidth1', 'bandwidth2']]
                        total = total[(total['bandwidth1'] > 0) | (total['bandwidth2'] > 0)] # if one datapoint contains a nan from the divide by 0, the enire datapoint will not be plotted.
                        
                        goodput_ratios_total.append(total.min(axis=1)/total.max(axis=1))
                        delay_ratios_total.append(((receiver1_srtt['srtt']/(2*delay))+(receiver2_srtt['srtt']/(2*delay)))/2)
                    else:
                        print(f"Folder {PATH} not found.")

                if  len(goodput_ratios_total) > 0:
                    goodput_ratios_total = np.concatenate(goodput_ratios_total, axis=0)
                    delay_ratios_total = np.concatenate(delay_ratios_total, axis=0)
                    if len(goodput_ratios_total) > 0:
                        data_entry = [protocol, bw, delay, delay_ratios_total.mean(), delay_ratios_total.std() , mult, goodput_ratios_total.mean(), goodput_ratios_total.std()]
                        data.append(data_entry)

        summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'delay_ratio_mean', 'delay_ratio_std', 'qmult', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])
    fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(4,1.2))
    ax = axes
    for protocol in PROTOCOLS_LEO:
        plot_points(ax, summary_data[summary_data['protocol'] == protocol].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std', PROTOCOLS_MARKERS_LEO[protocol], COLORS_LEO[protocol], PROTOCOLS_FRIENDLY_NAME_LEO[protocol], True)


    ax.set(yscale='linear',xlabel='RTT (ms)', ylabel='Goodput Ratio')
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_major_formatter(ScalarFormatter())
    handles, labels = ax.get_legend_handles_labels()
    handles = [h[0] for h in handles]
    leg1 = fig.legend(
        handles, labels,
        ncol=5,
        loc='upper center',
        bbox_to_anchor=(0.5, 1.08),
        frameon=False,
        fontsize=7,
        columnspacing=0.8,
        handlelength=2.5,
        handletextpad=0.5
    )
    fig.add_artist(leg1)

    #legend = fig.legend(handles, labels,ncol=3, loc='upper center',bbox_to_anchor=(0.5, 1.30),columnspacing=0.8,handletextpad=0.5)
    plt.savefig(f"goodput_ratio_intra_rtt_{mult}.pdf" , dpi=1080)

    fig2, ax2 = plt.subplots(nrows=1, ncols=1, figsize=(4, 1.2))
    for protocol in PROTOCOLS_LEO:
        plot_points(
            ax2,
            summary_data[summary_data['protocol'] == protocol].set_index('delay'),
            'delay_ratio_mean', 
            'delay_ratio_std',             
            PROTOCOLS_MARKERS_LEO[protocol],
            COLORS_LEO[protocol],
            PROTOCOLS_FRIENDLY_NAME_LEO[protocol],
            delay=True
        )

    ax2.set(yscale='linear', xlabel='RTT (ms)', ylabel='Delay Ratio')

    for axis in [ax2.xaxis, ax2.yaxis]:
        axis.set_major_formatter(ScalarFormatter())

    handles, labels = ax2.get_legend_handles_labels()
    handles = [h[0] for h in handles]
    leg1 = fig2.legend(
        handles[:3], labels[:3],
        ncol=3,
        loc='upper center',
        bbox_to_anchor=(0.5, 1.0),
        frameon=False,
        fontsize=7,
        columnspacing=0.8,
        handlelength=2.5,
        handletextpad=0.5
    )
    fig2.add_artist(leg1)

    leg2 = fig2.legend(
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

    plt.savefig(f"delay_intra_rtt_qmult{mult}.pdf", dpi=1080)

