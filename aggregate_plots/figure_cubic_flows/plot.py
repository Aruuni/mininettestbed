import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter, LogLocator, LogFormatter, FuncFormatter
import numpy as np

plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 
sys.dont_write_bytecode = True
EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_friendly_intra_rtt_flows/fifo" 

BWS = [100]
DELAY = 15
FLOWS = [3, 5, 7, 9, 11, 13, 15, 17, 19, 21]
for mult in QMULTS:
    data = []
    for protocol in PROTOCOLS_EXTENSION:
        for bw in BWS:
            for flows in FLOWS:
                start_time = 3*DELAY
                end_time = 4*DELAY-1
                keep_last_seconds = int(0.25*DELAY)

                BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
                BDP_IN_PKTS = BDP_IN_BYTES / 1500

                goodput_ratios_total = []
                delay_ratios_total = []
                for run in RUNS:
                    PATH = f"{EXPERIMENT_PATH}/Dumbell_{bw}mbit_{DELAY}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_{flows}flows_22tcpbuf_{protocol}/run{run}" 
                    csvs = [f"{PATH}/csvs/x{i}.csv" for i in range(1, flows+1)]
                    if not all(os.path.exists(p) for p in csvs):
                        print(f"Missing CSVs in {PATH}, skipping")
                        continue
                    # load each flow into a DataFrame, index by time
                    dfs = {}
                    for i, path in enumerate(csvs, start=1):
                        df = pd.read_csv(path)
                        df['time'] = df['time'].astype(float).astype(int)
                        df = (
                            df[(df.time > start_time) & (df.time < end_time)]
                            .drop_duplicates('time')
                            .set_index('time')
                        )
                        dfs[f"bw{i}"] = df.bandwidth
                    total = pd.concat(dfs, axis=1, join='inner')
                    total = total[(total > 0).any(axis=1)]  # drop all-zero rows

                    # compute avg of flows 2…FLOWS
                    total['others_avg'] = total[[f"bw{i}" for i in range(2, flows+1)]].mean(axis=1)

                    # ratio = min(bw1, others_avg) / max(bw1, others_avg)
                    # ratio = total[['bw1', 'others_avg']].min(axis=1) / total[['bw1', 'others_avg']].max(axis=1)
                    ratio = total['bw1'] / total['others_avg']
                    goodput_ratios_total.append(ratio.values)


                # after all runs
                if goodput_ratios_total:
                    all_ratios = np.concatenate(goodput_ratios_total)
                    entry = [protocol, bw, DELAY, flows-1, mult, all_ratios.mean(), all_ratios.std()]
                    data.append(entry)

                
    summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'flows', 'qmult', 'goodput_ratio_total_mean',  'goodput_ratio_total_std'])
    fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
    ax = axes
    for protocol in PROTOCOLS_EXTENSION:
        plot_points(
            ax, 
            summary_data[summary_data['protocol'] == protocol].set_index('flows'), 
            'goodput_ratio_total_mean', 
            'goodput_ratio_total_std', 
            PROTOCOLS_MARKERS_EXTENSION[protocol], 
            COLORS_EXTENSION[protocol], 
            PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol], 
            delay=False
        )

    ax.set(
        yscale='log',
        xlabel='Number of Cubic Flows',
        ylabel='Goodput Ratio',
        ylim=[0.1, 100]
    )

    # x-axis remains linear; use ScalarFormatter to keep “100”, “200”, … style
    ax.xaxis.set_major_formatter(ScalarFormatter())

    # for the log-y axis, put ticks at each power of ten
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f"{y:g}"))

    # rebuild the legend
    # handles, labels = ax.get_legend_handles_labels()
    # handles = [h[0] for h in handles]
    # fig.legend(
    #     handles, labels,
    #     ncol=3, loc='upper center',
    #     bbox_to_anchor=(0.5, 1.30),
    #     columnspacing=0.8,
    #     handletextpad=0.5
    # )


    plt.savefig(f"friendly_flows_random_start_qmult{mult}.pdf" , dpi=1080)


