#!/usr/bin/env python3
import os, sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import matplotlib as mpl
mpl.rcParams['text.usetex'] = False
pd.set_option('display.max_rows', None)

from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms

# --------------------------------------------------------------------
# Append project module path and import configuration
# --------------------------------------------------------------------
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../../..')
sys.path.append(mymodule_dir)
from core.config import *  # e.g. HOME_DIR, etc.

# --------------------------------------------------------------------
# Confidence Ellipse (from script 1)
# --------------------------------------------------------------------
def confidence_ellipse(x, y, ax, n_std=1.0, facecolor='none', **kwargs):
    if x.size != y.size:
        raise ValueError("x and y must be the same size")
    cov = np.cov(x, y)
    pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0),
                      width=ell_radius_x * 2,
                      height=ell_radius_y * 2,
                      facecolor=facecolor,
                      **kwargs)
    scale_x = np.sqrt(cov[0, 0]) * n_std
    mean_x = np.mean(x)
    scale_y = np.sqrt(cov[1, 1]) * n_std
    mean_y = np.mean(y)
    transf = (transforms.Affine2D()
              .rotate_deg(45)
              .scale(scale_x, scale_y)
              .translate(mean_x, mean_y))
    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)

# --------------------------------------------------------------------
# Jain's Fairness Index function
# --------------------------------------------------------------------
def calculate_jains_index(bandwidths):
    n = len(bandwidths)
    sum_bw = sum(bandwidths)
    sum_bw_sq = sum(bw**2 for bw in bandwidths)
    return (sum_bw**2) / (n * sum_bw_sq) if sum_bw_sq != 0 else 0

# --------------------------------------------------------------------
# data_to_dd_df:
#   Computes Jain's fairness index and total throughput over the cross interval only.
#   The final 'delay' is stored as delay*2.
# --------------------------------------------------------------------
def data_to_dd_df(root_path, aqm, bws, delays, qmults, protocols,
                  flows, runs, change1):
    """
    Loads CSVs from the double-dumbbell scenario and computes:
      - Jain's fairness index over the cross interval ([change1, change1+50))
      - The total throughput (sum across flows) over that interval
    The final 'delay' in the DataFrame is stored as delay*2.
    """
    results = []
    for mult in qmults:
        for bw in bws:
            for delay in delays:
                for protocol in protocols:
                    BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                    BDP_IN_PKTS = BDP_IN_BYTES / 1500
                    cross_jains_list = []
                    goodput_list = []

                    for run in runs:
                        receivers_goodput = {
                            i: pd.DataFrame()
                            for i in range(1, flows * 2 + 1)
                        }
                        for dumbbell in range(1, 3):
                            for flow_id in range(1, flows + 1):
                                real_flow_id = flow_id + flows*(dumbbell - 1)
                                csv_path = (f"{root_path}/{aqm}/DoubleDumbell_{bw}mbit_{delay}ms_"
                                            f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{flows}flows_22tcpbuf_"
                                            f"{protocol}/run{run}/csvs/x{dumbbell}_{flow_id}.csv")
                                if os.path.exists(csv_path):
                                    try:
                                        df_csv = pd.read_csv(csv_path, usecols=['time','bandwidth'])
                                        df_csv['time'] = df_csv['time'].astype(float).astype(int)
                                        df_csv = df_csv.drop_duplicates('time').set_index('time')
                                        receivers_goodput[real_flow_id] = df_csv
                                    except Exception as e:
                                        print(f"Error reading {csv_path}: {e}")
                                else:
                                    print(f"File {csv_path} not found")

                        # CROSS interval: [change1, change1+50)
                        cross_start = change1
                        cross_end = change1 + 50
                        cross_averages = []
                        for f_id in range(1, flows*2 + 1):
                            df_flow = receivers_goodput[f_id]
                            if df_flow.empty:
                                cross_averages.append(0)
                            else:
                                cross_slice = df_flow[
                                    (df_flow.index >= cross_start) &
                                    (df_flow.index < cross_end)
                                ]
                                cross_averages.append(
                                    cross_slice['bandwidth'].mean() if not cross_slice.empty else 0
                                )
                        print(f"Run {run} - {protocol} - {bw} Mbit/s - {delay} ms - {mult} - "
                              f"Jain's: {calculate_jains_index(cross_averages)} - "
                              f"Goodput: {np.sum(cross_averages)}")
                        cross_jain = calculate_jains_index(cross_averages)
                        cross_jains_list.append(cross_jain)
                        run_goodput = np.sum(cross_averages)
                        goodput_list.append(run_goodput)

                    cross_mean = np.mean(cross_jains_list) if cross_jains_list else 0
                    cross_std = np.std(cross_jains_list) if cross_jains_list else 0
                    goodput_mean = np.mean(goodput_list) if goodput_list else 0
                    goodput_std = np.std(goodput_list) if goodput_list else 0

                    results.append([
                        protocol, bw, delay*2, mult,
                        cross_mean, cross_std,
                        goodput_mean, goodput_std
                    ])

    columns = [
        'protocol','bandwidth','min_delay','qmult',
        'fairness_cross_mean','fairness_cross_std',
        'goodput_cross_mean','goodput_cross_std'
    ]
    return pd.DataFrame(results, columns=columns)

# --------------------------------------------------------------------
# New plot function: X = Jain's fairness, Y = normalized throughput.
# --------------------------------------------------------------------
def plot_dd_scatter_jains_vs_util(df, delays=[10,20], qmults=[0.2,1,4]):

    COLOR_MAP = {
        'cubic':   '#0C5DA5',
        'bbr1':    '#00B945',
        'bbr3':    '#FF9500',
        'astraea': '#686868',
    }
    MARKER_MAP = {
        20: '^',  # base delay=10 -> stored as 20
        40: 'o',  # base delay=20 -> stored as 40
    }

    for q in qmults:
        fig, ax = plt.subplots(figsize=(3.5,2.0))
        protocols_in_df = df['protocol'].unique()
        for prot in protocols_in_df:
            for d in sorted(df['min_delay'].unique()):
                subset = df[
                    (df['qmult'] == q) &
                    (df['protocol'] == prot) &
                    (df['min_delay'] == d)
                ]
                if subset.empty:
                    continue

                # x = Jain's fairness index
                x = subset['fairness_cross_mean'].values
                print(subset['fairness_cross_mean'].values)
                # y = normalized throughput (goodput_cross_mean / 100)
                y = subset['goodput_cross_mean'].values / 100.0

                color = COLOR_MAP.get(prot, 'gray')
                marker = MARKER_MAP.get(d, 'x')

                # Plot individual runs
                # ax.scatter(x, y,
                #            edgecolors=color,
                #            marker=marker,
                #            facecolors='none',
                #            alpha=0.4)
                # Plot mean point
                ax.scatter(np.mean(x), np.mean(y),
                           edgecolors=color,
                           marker=marker,
                           facecolors='none',
                           alpha=1.0,
                           label=f"{prot}-{d}ms")
                # # Draw confidence ellipse if more than one point exists
                # if len(x) > 1:
                #     confidence_ellipse(x, y, ax,
                #                        facecolor=color,
                #                        edgecolor='none',
                #                        alpha=0.1)
        ax.set_xlabel("Jain's Fairness Index (100–150s)")
        ax.set_ylabel("Norm. Throughput (Sum / 100 Mbit/s)")
        ax.set_xlim([0.6,1.05])
        ax.set_ylim([0,1.05])
        ax.grid(True)
        handles, labels = ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        ax.legend(unique.values(), unique.keys(),
                  ncol=2, loc='upper left',
                  bbox_to_anchor=(1.01,1.0))
        fig.tight_layout()
        plt.savefig(f"jains_vs_util_qmult_{q}.pdf", dpi=720)
        plt.close(fig)

# --------------------------------------------------------------------
# Main block
# --------------------------------------------------------------------
if __name__ == "__main__":
    ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/cross_traffic_fairness_inter_rtt"
    AQM = "fifo"
    BWS = [100]          # in Mbit/s
    DELAYS = [10,20]     # base delays in ms; final stored is delay*2: [20,40]
    QMULTS = [0.2,1,4]
    PROTOCOLS = ['cubic','bbr1','bbr3','astraea']
    FLOWS = 2
    RUNS = [1,2,3,4,5]
    CHANGE1 = 100       # use only cross interval
    # No CHANGE2 needed

    # 1) Load the data
    dd_df = data_to_dd_df(ROOT_PATH, AQM, BWS, DELAYS, QMULTS,
                          PROTOCOLS, FLOWS, RUNS, CHANGE1)
    print(dd_df)
    dd_df.to_csv("dd_summary_data.csv", index=False)

    # 2) Plot: X = Jain's fairness, Y = normalized throughput
    plot_dd_scatter_jains_vs_util(dd_df, delays=DELAYS, qmults=QMULTS)
