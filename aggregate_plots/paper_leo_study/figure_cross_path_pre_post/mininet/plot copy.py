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
# Helper function: Confidence Ellipse (from script 1)
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
# Helper function: Jain's Fairness Index (from script 2)
# --------------------------------------------------------------------
def calculate_jains_index(bandwidths):
    n = len(bandwidths)
    sum_bw = sum(bandwidths)
    sum_bw_sq = sum(bw**2 for bw in bandwidths)
    return (sum_bw**2) / (n * sum_bw_sq) if sum_bw_sq != 0 else 0

# --------------------------------------------------------------------
# Modified data_to_dd_df: store TOTAL throughput across flows
# --------------------------------------------------------------------
def data_to_dd_df(root_path, aqm, bws, delays, qmults, protocols,
                  flows, runs, change1, change2):
    """
    Loads CSVs from the double-dumbbell scenario and computes:
      - Jain's fairness index over the cross interval ([change1, change1+50))
      - The total throughput (sum across flows) over that interval
      - The fairness index over the return interval ([change2, change2+50)) for reference
    The final 'delay' in the DataFrame is stored as delay*2.
    """
    results = []
    for mult in qmults:
        for bw in bws:
            for delay in delays:
                for protocol in protocols:
                    # Calculate BDP (used to determine queue size in pkts)
                    BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                    BDP_IN_PKTS = BDP_IN_BYTES / 1500
                    cross_jains_list = []
                    return_jains_list = []
                    goodput_list = []

                    for run in runs:
                        # Dictionary for 4 flows
                        receivers_goodput = {
                            i: pd.DataFrame()
                            for i in range(1, flows * 2 + 1)
                        }
                        # Loop over both dumbbells
                        for dumbbell in range(1, 3):
                            for flow_id in range(1, flows + 1):
                                real_flow_id = flow_id + flows*(dumbbell - 1)
                                csv_path = (f"{root_path}/{aqm}/DoubleDumbell_{bw}mbit_{delay}ms_"
                                            f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{flows}flows_22tcpbuf_"
                                            f"{protocol}/run{run}/csvs/x{dumbbell}_{flow_id}.csv")
                                if os.path.exists(csv_path):
                                    try:
                                        df = pd.read_csv(csv_path, usecols=['time','bandwidth'])
                                        df['time'] = df['time'].astype(float).astype(int)
                                        df = df.drop_duplicates('time').set_index('time')
                                        receivers_goodput[real_flow_id] = df
                                    except Exception as e:
                                        print(f"Error reading {csv_path}: {e}")
                                else:
                                    print(f"File {csv_path} not found")

                        # CROSS interval: [change1, change1+50)
                        cross_start = change1
                        cross_end   = change1 + 50
                        cross_averages = []
                        for f_id in range(1, flows*2 + 1):
                            df_flow = receivers_goodput[f_id]
                            if df_flow.empty:
                                cross_averages.append(0)
                            else:
                                cross_slice = df_flow[(df_flow.index >= cross_start) & (df_flow.index < cross_end)]
                                cross_averages.append(cross_slice['bandwidth'].mean() if not cross_slice.empty else 0)
                        
                        cross_jain = calculate_jains_index(cross_averages)
                        cross_jains_list.append(cross_jain)

                        # Now use the SUM across flows (total link usage)
                        run_goodput = np.sum(cross_averages)  
                        goodput_list.append(run_goodput)

                        # RETURN interval: [change2, change2+50)
                        return_start = change2
                        return_end   = change2 + 50
                        # Dumbbell 1 flows
                        d1_averages = []
                        for f_id in [1,2]:
                            df_flow = receivers_goodput[f_id]
                            if df_flow.empty:
                                d1_averages.append(0)
                            else:
                                slice_d1 = df_flow[(df_flow.index >= return_start) & (df_flow.index < return_end)]
                                d1_averages.append(slice_d1['bandwidth'].mean() if not slice_d1.empty else 0)
                        # Dumbbell 2 flows
                        d2_averages = []
                        for f_id in [3,4]:
                            df_flow = receivers_goodput[f_id]
                            if df_flow.empty:
                                d2_averages.append(0)
                            else:
                                slice_d2 = df_flow[(df_flow.index >= return_start) & (df_flow.index < return_end)]
                                d2_averages.append(slice_d2['bandwidth'].mean() if not slice_d2.empty else 0)
                        JFI_d1 = calculate_jains_index(d1_averages)
                        JFI_d2 = calculate_jains_index(d2_averages)
                        return_jain = (JFI_d1 + JFI_d2)/2
                        return_jains_list.append(return_jain)

                    # Aggregate over runs
                    cross_mean   = np.mean(cross_jains_list) if cross_jains_list else 0
                    cross_std    = np.std(cross_jains_list)  if cross_jains_list else 0
                    return_mean  = np.mean(return_jains_list) if return_jains_list else 0
                    return_std   = np.std(return_jains_list)  if return_jains_list else 0
                    goodput_mean = np.mean(goodput_list) if goodput_list else 0
                    goodput_std  = np.std(goodput_list)  if goodput_list else 0

                    # Remember: store final 'delay' as delay*2
                    results.append([
                        protocol, bw, delay*2, mult,
                        cross_mean, cross_std,
                        return_mean, return_std,
                        goodput_mean, goodput_std
                    ])

    columns = [
        'protocol','bandwidth','delay','qmult',
        'fairness_cross_mean','fairness_cross_std',
        'fairness_return_mean','fairness_return_std',
        'goodput_cross_mean','goodput_cross_std'
    ]
    return pd.DataFrame(results, columns=columns)

# --------------------------------------------------------------------
# Plotting: multiple DELAYS on one figure (per qmult),
#           color by PROTOCOL, marker by DELAY
# --------------------------------------------------------------------
def plot_dd_scatter_multiple_delays(df, delays=[10,20,30], qmults=[0.2,1,4]):
    """
    Produce one figure for each qmult. Plot points for *all* the delays and protocols
    in the same scatter. We color by protocol and change marker shape by delay.

    The x-axis is the fairness index (100–150s).
    The y-axis is the *total* throughput (in Mbit/s) normalized by 100 (i.e. fraction of link usage).
    """

    # Map protocols to colors
    COLOR_MAP = {
        'cubic':   '#0C5DA5',
        'bbr1':    '#00B945',
        'bbr3':    '#FF9500',
        'astraea': '#686868',
        # add more if needed
    }
    # Map the "delay * 2" to different marker shapes.
    # e.g. if you tested 10ms => stored 20 in df, 20ms => stored 40, etc.
    MARKER_MAP = {
        20: '^',  # for base delay=10 => 20 in the DF
        40: 'o',  # for base delay=20 => 40 in the DF
        60: 's',  # for base delay=30 => 60 in the DF
    }

    # For each qmult, make a figure
    for q in qmults:
        fig, ax = plt.subplots(figsize=(3.5, 2.0))

        # We'll loop over each protocol in the data
        protocols_in_df = df['protocol'].unique()

        for prot in protocols_in_df:
            # Now loop over each *stored* delay value in the DF
            # (or you can loop over the base delays you want)
            for d in sorted(df['delay'].unique()):
                subset = df[
                    (df['qmult'] == q) &
                    (df['protocol'] == prot) &
                    (df['delay'] == d)
                ]
                if subset.empty:
                    continue

                # x = fairness index
                x = subset['fairness_cross_mean'].values
                # y = total throughput across flows, normalized by 100 Mbit/s
                y = subset['goodput_cross_mean'].values / 100.0

                # pick color for protocol
                color = COLOR_MAP.get(prot, 'gray')
                # pick marker for delay
                marker = MARKER_MAP.get(d, 'x')

                # scatter the individual points
                ax.scatter(x, y,
                           edgecolors=color,
                           marker=marker,
                           facecolors='none',
                           alpha=0.4)

                # plot a single point for the mean
                ax.scatter(np.mean(x), np.mean(y),
                           edgecolors=color,
                           marker=marker,
                           facecolors='none',
                           alpha=1.0,
                           label=f"{prot}-{d}ms")

                # Optionally draw a confidence ellipse
                # (only if len(subset) > 1)
                if len(x) > 1:
                    confidence_ellipse(x, y, ax,
                                       facecolor=color,
                                       edgecolor='none',
                                       alpha=0.1)

        ax.set_xlabel("Jain's Fairness Index (100–150s)")
        ax.set_ylabel("Norm. Throughput (Sum / 100 Mbit/s)")
        ax.set_xlim([0.5, 1.05])   # typical range for fairness index
        ax.set_ylim([0, 1.05])   # up to 100% link usage
        ax.grid()

        # Build legend
        handles, labels = ax.get_legend_handles_labels()
        # remove duplicates if you want
        unique = list(dict(zip(labels, handles)).items())
        unique_labels = [u[0] for u in unique]
        unique_handles = [u[1] for u in unique]

        ax.legend(unique_handles, unique_labels, ncol=2, loc='upper left',
                  bbox_to_anchor=(1.01,1.0))
        fig.tight_layout()
        plt.savefig(f"dd_qmult_{q}.pdf", dpi=720)
        plt.close(fig)

# --------------------------------------------------------------------
# Main block
# --------------------------------------------------------------------
if __name__ == "__main__":
    # Example configuration
    ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/cross_traffic_fairness_inter_rtt"
    AQM = "fifo"
    BWS = [100]        # in Mbit/s
    DELAYS = [10, 20]  # base delays in ms, e.g. 10 => stored 20, 20 => stored 40
    QMULTS = [0.2, 1, 4]
    PROTOCOLS = ['cubic', 'bbr1', 'bbr3', 'astraea']
    FLOWS = 2
    RUNS = [1, 2, 3, 4, 5]
    CHANGE1 = 100
    CHANGE2 = 200

    # Load the data
    dd_df = data_to_dd_df(ROOT_PATH, AQM, BWS, DELAYS, QMULTS,
                          PROTOCOLS, FLOWS, RUNS, CHANGE1, CHANGE2)
    print(dd_df)
    dd_df.to_csv("dd_summary_data.csv", index=False)

    # Now plot multiple delays on the same figure (one figure per qmult).
    # In the function, we define which stored delays => which marker shape, etc.
    plot_dd_scatter_multiple_delays(dd_df, delays=DELAYS, qmults=QMULTS)
