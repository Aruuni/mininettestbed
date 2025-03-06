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
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)
from core.config import *  # e.g. HOME_DIR, etc.


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

def calculate_jains_index(bandwidths):
    n = len(bandwidths)
    sum_bw = sum(bandwidths)
    sum_bw_sq = sum(bw**2 for bw in bandwidths)
    return (sum_bw**2) / (n * sum_bw_sq) if sum_bw_sq != 0 else 0

def data_to_dd_df(root_path, aqm, bws, delays, qmults, protocols,
                  flows, runs, change1):

    results = []
    for mult in qmults:
        for bw in bws:
            for delay in delays:
                cross_start = change1
                cross_end = change1 + 50  # cross interval duration remains 50 seconds
                for protocol in protocols:
                    BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                    BDP_IN_PKTS = BDP_IN_BYTES / 1500
                    cross_jains_list = []
                    goodput_list = []
                    retr_list = []
                    util_list = []
                    rejoin_util_list = []  # List for rejoin utilization averages
                    rejoin_retr_list = []  # List for rejoin retransmission averages

                    for run in runs:
                        # Define the rejoin interval for retransmission calculations
                        rejoin_start = 200
                        rejoin_end = 200 + delay
                        # This list will hold rejoin retransmission values for each dumbbell/flow
                        rejoin_retr_values = []

                        receivers_goodput = { i: pd.DataFrame() for i in range(1, flows*2+1) }
                        retr_values = []
                        # For each dumbbell and flow, read goodput and retransmission files
                        for dumbbell in range(1, 3):
                            for flow_id in range(1, flows+1):
                                real_flow_id = flow_id + flows*(dumbbell-1)
                                # Read goodput CSV
                                csv_path = (f"{root_path}/{aqm}/DoubleDumbell_{bw}mbit_{delay}ms_"
                                            f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{flows}flows_22tcpbuf_"
                                            f"{protocol}/run{run}/csvs/x{dumbbell}_{flow_id}.csv")
                                if os.path.exists(csv_path):
                                    df_csv = pd.read_csv(csv_path, usecols=['time','bandwidth'])
                                    df_csv['time'] = df_csv['time'].astype(float).astype(int)
                                    df_csv = df_csv.drop_duplicates('time').set_index('time')
                                    receivers_goodput[real_flow_id] = df_csv
                                else:
                                    print(f"File {csv_path} not found")
                                
                                # Read retransmission sysstat file (for both cross and rejoin intervals)
                                sysstat_path = (f"{root_path}/{aqm}/DoubleDumbell_{bw}mbit_{delay}ms_"
                                                f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{flows}flows_22tcpbuf_"
                                                f"{protocol}/run{run}/sysstat/etcp_c{dumbbell}_{flow_id}.log")
                                if os.path.exists(sysstat_path):
                                    systat = pd.read_csv(sysstat_path, sep=';').rename(columns={"# hostname": "hostname"})
                                    retr_df = systat[['timestamp','retrans/s']]
                                    start_timestamp = retr_df['timestamp'].iloc[0]
                                    retr_df.loc[:, 'timestamp'] = retr_df['timestamp'] - start_timestamp + 1
                                    retr_df = retr_df.rename(columns={'timestamp':'time'})
                                    retr_df['time'] = retr_df['time'].astype(float).astype(int)
                                    # Compute for cross interval
                                    cross_df = retr_df[(retr_df['time'] >= cross_start) & (retr_df['time'] < cross_end)]
                                    cross_df = cross_df.drop_duplicates('time').set_index('time')
                                    retr_val = (cross_df * 1500 * 8 / (1024 * 1024)).mean().values[0]
                                    retr_values.append(retr_val)
                                    # Compute for rejoin interval
                                    rejoin_df = retr_df[(retr_df['time'] >= rejoin_start) & (retr_df['time'] < rejoin_end)]
                                    rejoin_df = rejoin_df.drop_duplicates('time').set_index('time')
                                    retr_rejoin_val = (rejoin_df * 1500 * 8 / (1024 * 1024)).mean().values[0]
                                    rejoin_retr_values.append(retr_rejoin_val)
                                else:
                                    retr_values.append(0)
                                    rejoin_retr_values.append(0)

                        # Process the dev util file for the cross interval (using r2a-eth1)
                        sysstat_path_dev = (f"{root_path}/{aqm}/DoubleDumbell_{bw}mbit_{delay}ms_"
                                            f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{flows}flows_22tcpbuf_"
                                            f"{protocol}/run{run}/sysstat/dev_r2a.log")
                        if os.path.exists(sysstat_path_dev):
                            print(sysstat_path_dev)
                            df_dev = pd.read_csv(sysstat_path_dev, sep=';').rename(columns={"# hostname": "hostname"})
                            util = df_dev[['timestamp', 'IFACE', 'txkB/s', '%ifutil']]
                            start_timestamp = util['timestamp'].iloc[0]
                            util.loc[:, 'timestamp'] = util['timestamp'] - start_timestamp + 1
                            util = util.rename(columns={'timestamp': 'time'})
                            util['time'] = util['time'].apply(lambda x: int(float(x)))
                            util_if = util[util['IFACE'] == "r2a-eth1"]
                            util_if = util_if[['time', 'txkB/s']].set_index('time')
                            print(util_if)
                            
                            # Convert txkB/s to Mbit/s
                            util_if['txkB/s'] = util_if['txkB/s'] * 8 / 1024
                            print(protocol)
                            print(util_list)

                            # Drop duplicate indices (keeping the first occurrence)
                            util_if = util_if[~util_if.index.duplicated(keep='first')]
                            
                            # Reindex the 'txkB/s' series over the desired range
                            util_series = util_if['txkB/s'].reindex(range(cross_start, cross_end), fill_value=0)
                            util_list.append(util_series.mean())
                        else:
                            util_list.append(0)
                        
                        # --- Compute rejoin utilization over the window [200, 200+delay] seconds ---
                        # r2a-eth1 rejoin (reuse the dev file if available)
                        util_rejoin_a = 0
                        if os.path.exists(sysstat_path_dev):
                            df_dev_rejoin_a = pd.read_csv(sysstat_path_dev, sep=';').rename(columns={"# hostname": "hostname"})
                            util_rejoin_a_df = df_dev_rejoin_a[['timestamp', 'IFACE', 'txkB/s', '%ifutil']]
                            start_timestamp_a = util_rejoin_a_df['timestamp'].iloc[0]
                            util_rejoin_a_df.loc[:, 'timestamp'] = util_rejoin_a_df['timestamp'] - start_timestamp_a + 1
                            util_rejoin_a_df = util_rejoin_a_df.rename(columns={'timestamp': 'time'})
                            util_rejoin_a_df['time'] = util_rejoin_a_df['time'].apply(lambda x: int(float(x)))
                            util_rejoin_a_df = util_rejoin_a_df[util_rejoin_a_df['IFACE'] == "r2a-eth1"]
                            util_rejoin_a_df = util_rejoin_a_df[['time', 'txkB/s']].set_index('time')
                            util_rejoin_a_df['txkB/s'] = util_rejoin_a_df['txkB/s'] * 8 / 1024
                            util_rejoin_a_df = util_rejoin_a_df[~util_rejoin_a_df.index.duplicated(keep='first')]
                            util_series_a = util_rejoin_a_df['txkB/s'].reindex(range(rejoin_start, rejoin_end), fill_value=0)
                            util_rejoin_a = util_series_a.mean()
                        # r2b-eth1 rejoin from a separate dev file
                        util_rejoin_b = 0
                        sysstat_path_dev_r2b = (f"{root_path}/{aqm}/DoubleDumbell_{bw}mbit_{delay}ms_"
                                                f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{flows}flows_22tcpbuf_"
                                                f"{protocol}/run{run}/sysstat/dev_r2b.log")
                        if os.path.exists(sysstat_path_dev_r2b):

                            df_dev_rejoin_b = pd.read_csv(sysstat_path_dev_r2b, sep=';').rename(columns={"# hostname": "hostname"})
                            util_rejoin_b_df = df_dev_rejoin_b[['timestamp', 'IFACE', 'txkB/s', '%ifutil']]
                            start_timestamp_b = util_rejoin_b_df['timestamp'].iloc[0]
                            util_rejoin_b_df.loc[:, 'timestamp'] = util_rejoin_b_df['timestamp'] - start_timestamp_b + 1
                            util_rejoin_b_df = util_rejoin_b_df.rename(columns={'timestamp': 'time'})
                            util_rejoin_b_df['time'] = util_rejoin_b_df['time'].apply(lambda x: int(float(x)))
                            util_rejoin_b_df = util_rejoin_b_df[util_rejoin_b_df['IFACE'] == "r2b-eth1"]
                            util_rejoin_b_df = util_rejoin_b_df[['time', 'txkB/s']].set_index('time')
                            util_rejoin_b_df['txkB/s'] = util_rejoin_b_df['txkB/s'] * 8 / 1024
                            util_series_b = util_rejoin_b_df['txkB/s'].reindex(range(rejoin_start, rejoin_end), fill_value=0)
                            util_rejoin_b = util_series_b.mean()
                        # Average the two rejoin utilizations
                        avg_rejoin_util = (util_rejoin_a + util_rejoin_b) / 2
                        rejoin_util_list.append(avg_rejoin_util)

                        # Compute Jain's fairness for this run using the goodput data
                        cross_averages = []
                        for f_id in range(1, flows*2+1):
                            df_flow = receivers_goodput[f_id]
                            if df_flow.empty:
                                cross_averages.append(0)
                            else:
                                cross_slice = df_flow[(df_flow.index >= cross_start) & (df_flow.index < cross_start+50)]
                                cross_averages.append(cross_slice['bandwidth'].mean() if not cross_slice.empty else 0)
                        cross_jain = calculate_jains_index(cross_averages)
                        cross_jains_list.append(cross_jain)
                        run_goodput = np.sum(cross_averages)
                        goodput_list.append(run_goodput)
                        run_retr = np.mean(retr_values) if retr_values else 0
                        retr_list.append(run_retr)
                        # Compute average rejoin retransmission for this run
                        run_retr_rejoin = np.mean(rejoin_retr_values) if rejoin_retr_values else 0
                        rejoin_retr_list.append(run_retr_rejoin)
                    # End runs loop

                    cross_mean = np.mean(cross_jains_list) if cross_jains_list else 0
                    cross_std  = np.std(cross_jains_list) if cross_jains_list else 0
                    goodput_mean = np.mean(goodput_list) if goodput_list else 0
                    goodput_std  = np.std(goodput_list) if goodput_list else 0
                    retr_mean = np.mean(retr_list) if retr_list else 0
                    retr_std  = np.std(retr_list) if retr_list else 0
                    util_mean = np.mean(util_list) if util_list else 0
                    util_std  = np.std(util_list) if util_list else 0
                    rejoin_util_mean = np.mean(rejoin_util_list) if rejoin_util_list else 0
                    rejoin_util_std  = np.std(rejoin_util_list) if rejoin_util_list else 0
                    retr_rejoin_mean = np.mean(rejoin_retr_list) if rejoin_retr_list else 0
                    retr_rejoin_std  = np.std(rejoin_retr_list) if rejoin_retr_list else 0

                    results.append([
                        protocol, bw, delay*2, mult,
                        cross_mean, cross_std,
                        goodput_mean, goodput_std,
                        retr_mean, retr_std, 
                        util_mean, util_std,
                        rejoin_util_mean, rejoin_util_std,
                        retr_rejoin_mean, retr_rejoin_std
                    ])

    columns = [
        'protocol','bandwidth','min_delay','qmult',
        'fairness_cross_mean','fairness_cross_std',
        'goodput_cross_mean','goodput_cross_std',
        'retr_cross_mean','retr_cross_std', 
        'util_mean', 'util_std',
        'rejoin_util_mean', 'rejoin_util_std',
        'retr_rejoin_mean', 'retr_rejoin_std'
    ]
    return pd.DataFrame(results, columns=columns)


def plot_dd_scatter_jains_vs_util(df, delays=[10,20], qmults=[0.2,1,4]):
    COLOR_MAP = {'cubic': '#0C5DA5',
             'bbr1': '#00B945',
             'bbr3': '#FF9500',
             'sage': '#FF2C01',
             'orca': '#845B97',
             'astraea': '#686868',
             }

    CROSS_MARKER   = '^'  # triangle for Cross
    REJOIN_MARKER  = '*'  # circle for Rejoin

    for q in qmults:
        fig, ax = plt.subplots(figsize=(5, 3))  # Adjust as desired

        # 1) Plot data (unfilled markers, no legend labels)
        for prot in df['protocol'].unique():
            sub_df = df[(df['qmult'] == q) & (df['protocol'] == prot)]
            if sub_df.empty:
                continue

            x = sub_df['fairness_cross_mean'].values
            y_cross = sub_df['util_mean'].values / 100.0
            y_cross_minus_retr = (
                sub_df['util_mean'].values
                - sub_df['retr_cross_mean'].values
            ) / 100.0
            y_rejoin = sub_df['rejoin_util_mean'].values / 100.0
            y_rejoin_minus_retr = (
                sub_df['rejoin_util_mean'].values
                - sub_df['retr_rejoin_mean'].values
            ) / 100.0

            # Cross (triangle)
            ax.scatter(
                x, y_cross,
                marker=CROSS_MARKER, s=60,
                facecolors='none',
                edgecolors=COLOR_MAP.get(prot, 'gray'),
                alpha=1.0
            )
            # Cross minus retrans
            ax.scatter(
                x, y_cross_minus_retr,
                marker=CROSS_MARKER, s=60,
                facecolors='none',
                edgecolors=COLOR_MAP.get(prot, 'gray'),
                alpha=0.5
            )
            # Rejoin (circle)
            ax.scatter(
                x, y_rejoin,
                marker=REJOIN_MARKER, s=60,
                facecolors='none',
                edgecolors=COLOR_MAP.get(prot, 'gray'),
                alpha=1.0
            )
            # Rejoin minus retrans
            ax.scatter(
                x, y_rejoin_minus_retr,
                marker=REJOIN_MARKER, s=60,
                facecolors='none',
                edgecolors=COLOR_MAP.get(prot, 'gray'),
                alpha=0.5
            )

        # 2) TOP LEGEND (protocols only) - in figure coords so it’s truly above
        protocol_handles = []
        protocol_labels  = []
        for prot in sorted(df['protocol'].unique()):
            # Dummy handle: unfilled circle in protocol color
            handle = ax.scatter(
                [], [],
                marker='o', s=80,
                facecolors=COLOR_MAP[prot],
                edgecolors=COLOR_MAP[prot],
            )
            protocol_handles.append(handle)
            protocol_labels.append(prot)

        top_legend = ax.legend(
            protocol_handles, protocol_labels,
            loc='center',
            bbox_to_anchor=(0.5, 0.92),  # well above axes
            bbox_transform=fig.transFigure,  # <--- key!
            ncol=4
        )
        # We add this legend to the figure (it’s already in figure coords)
        ax.add_artist(top_legend)

        # 3) IN-PLOT LEGEND: Cross vs Rejoin
        cross_handle = ax.scatter(
            [], [],
            marker=CROSS_MARKER, s=80,
            facecolors='none', edgecolors='black',
            label='Cross'
        )
        rejoin_handle = ax.scatter(
            [], [],
            marker=REJOIN_MARKER, s=80,
            facecolors='none', edgecolors='black',
            label='Rejoin'
        )
        shape_legend = ax.legend(
            [cross_handle, rejoin_handle],
            ['Cross', 'Rejoin'],
            loc='upper left'
        )
        ax.add_artist(shape_legend)

        # 4) Style and layout
        ax.set_xlabel("Jain's Fairness Index")
        ax.set_ylabel("Norm. Throughput")
        ax.set_xlim([0.6, 1.05])
        ax.set_ylim([0.5, 1.05])
        ax.grid(True)

        # Make sure there's enough space at the top for the protocol legend
        fig.tight_layout()
        # Then move the top margin down a bit so legend is visible
        plt.subplots_adjust(top=0.85)

        plt.savefig(f"jains_vs_util_qmult_{q}.pdf", dpi=720)
        plt.close(fig)

if __name__ == "__main__":
    ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_soft_handover_fairness_inter_rtt"
    AQM = "fifo"
    BWS = [100]       # in Mbit/s
    DELAYS = [10]     # base delays in ms; final stored as [20,40] in DF
    QMULTS = [0.2,1,4]
    PROTOCOLS = ['cubic','bbr1','bbr3','astraea', 'sage']
    FLOWS = 2
    RUNS = [1,2,3,4,5]
    CHANGE1 = 100     # cross interval start time

    # 1) Load the data (with retransmission calculations and rejoin utilization)
    dd_df = data_to_dd_df(ROOT_PATH, AQM, BWS, DELAYS, QMULTS,
                          PROTOCOLS, FLOWS, RUNS, CHANGE1)
    print(dd_df)
    dd_df.to_csv("dd_summary_data.csv", index=False)

    # 2) Plot: X = Jain's fairness, Y = normalized throughput (with secondary points subtracting retransmission,
    #    and additional rejoin utilization markers)
    plot_dd_scatter_jains_vs_util(dd_df, delays=DELAYS, qmults=QMULTS)
