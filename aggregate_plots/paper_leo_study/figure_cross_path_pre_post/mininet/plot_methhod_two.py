import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy as np
import os, sys

# Optional style imports
import scienceplots
plt.style.use('science')
import matplotlib as mpl
plt.rcParams['text.usetex'] = False
pd.set_option('display.max_rows', None)

script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../../..')
sys.path.append(mymodule_dir)

# Replace these with your actual modules as needed
from core.config import *
from core.utils import *

# -----------------
# CONFIGURATIONS
# -----------------
ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/cross_traffic_fairness_inter_rtt"
COLOR = {
    'cubic': '#0C5DA5',
    'orca': '#00B945',
    'bbr3': '#FF9500',
    'bbr': '#FF2C01',
    'sage': '#845B97',
    'pcc': '#686868'
}

BWS = [100]
DELAYS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
AQM = "fifo"
QMULTS = [0.2, 1, 4]
PROTOCOLS = ['cubic', 'orca', 'bbr', 'sage', 'pcc', 'bbr3']

# 2 flows per dumbbell => total 4 flows
FLOWS = 2
RUNS = [1, 2, 3, 4, 5]

# Time intervals
CHANGE1 = 100
CHANGE2 = 200

# -------------
# Helper function
# -------------
def calculate_jains_index(bandwidths):
    """Calculate Jain's Fairness Index for a given set of bandwidth values."""
    n = len(bandwidths)
    sum_bw = sum(bandwidths)
    sum_bw_sq = sum(bw ** 2 for bw in bandwidths)
    return (sum_bw ** 2) / (n * sum_bw_sq) if sum_bw_sq != 0 else 0


if __name__ == "__main__":
    # We will store the final results for each qmult in a list of DataFrames
    all_dataframes = []

    for mult in QMULTS:
        results = []  # store data rows for this qmult

        for bw in BWS:
            for delay in DELAYS:
                for protocol in PROTOCOLS:
                    # Calculate queue size in pkts
                    BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                    BDP_IN_PKTS = BDP_IN_BYTES / 1500

                    # Prepare lists to store Jain's indices across runs
                    cross_jains_list = []   # JFI for 4 flows in [CHANGE1+delay, ...]
                    return_jains_list = []  # average JFI of Dumbbell1 + Dumbbell2 in [CHANGE2+delay, ...]

                    for run in RUNS:
                        # Prepare data structures to store bandwidth per flow
                        # We'll have 4 flows total: 
                        #   flowID=1,2 on Dumbbell #1,
                        #   flowID=3,4 on Dumbbell #2.
                        # Because user used: flow + (FLOWS * (dumbbell - 1)) 
                        # => flows #1..2 = Dumbbell #1, flows #3..4 = Dumbbell #2
                        receivers_goodput = {
                            i: pd.DataFrame(columns=['time', 'bandwidth']) 
                            for i in range(1, FLOWS * 2 + 1)
                        }

                        # Path to CSV folder for this run
                        PATH = (f"{ROOT_PATH}/{AQM}/DoubleDumbell_{bw}mbit_{delay}ms_"
                                f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{FLOWS}flows_22tcpbuf_"
                                f"{protocol}/run{run}")

                        # Load the CSV data for each flow
                        # flow_id = flow + (FLOWS * (dumbbell - 1))
                        for dumbbell in range(1, 3):
                            for flow_id in range(1, FLOWS + 1):
                                csv_path = f"{PATH}/csvs/x{dumbbell}_{flow_id}.csv"
                                if os.path.exists(csv_path):
                                    df = pd.read_csv(csv_path, usecols=['time', 'bandwidth'])
                                    df['time'] = df['time'].astype(float).astype(int)
                                    df = df.drop_duplicates('time').set_index('time')

                                    real_flow_id = flow_id + (FLOWS * (dumbbell - 1))
                                    receivers_goodput[real_flow_id] = df

                        # ------------------------------------------------------
                        # CROSS Interval: [CHANGE1 + delay, CHANGE1 + delay + window)
                        # We compute average goodput for flows #1, #2, #3, #4
                        # then do a single Jain’s index across all 4 flows.
                        # ------------------------------------------------------
                        cross_start = CHANGE1 
                        cross_end   = CHANGE1 + 50

                        cross_averages = []
                        for flow_id in range(1, 4 + 1):  # 1..4
                            df_i = receivers_goodput[flow_id]
                            if df_i.empty:
                                cross_averages.append(0)
                            else:
                                cross_slice = df_i.loc[
                                    (df_i.index >= cross_start) & (df_i.index < cross_end),
                                    'bandwidth'
                                ]
                                cross_averages.append(cross_slice.mean() if len(cross_slice) > 0 else 0)
                        printRed(cross_averages)
                        cross_jain = calculate_jains_index(cross_averages)
                        cross_jains_list.append(cross_jain)

                        # ------------------------------------------------------
                        # RETURN Interval: [CHANGE2 + delay, CHANGE2 + delay + window)
                        # We compute average goodput for flows #1, #2 (Dumbbell #1)
                        # => compute JFI_1
                        # We compute average goodput for flows #3, #4 (Dumbbell #2)
                        # => compute JFI_2
                        # Then we take the average => (JFI_1 + JFI_2) / 2
                        # ------------------------------------------------------
                        return_start = CHANGE2 
                        return_end   = CHANGE2 + 50

                        # Dumbbell #1: flows #1, #2
                        d1_averages = []
                        for flow_id in [1, 2]:
                            df_i = receivers_goodput[flow_id]
                            if df_i.empty:
                                d1_averages.append(0)
                            else:
                                d1_slice = df_i.loc[
                                    (df_i.index >= return_start) & (df_i.index < return_end),
                                    'bandwidth'
                                ]
                                d1_averages.append(d1_slice.mean() if len(d1_slice) > 0 else 0)
                        JFI_d1 = calculate_jains_index(d1_averages)
                        printGreen(d1_averages)
                        # Dumbbell #2: flows #3, #4
                        d2_averages = []
                        for flow_id in [3, 4]:
                            df_i = receivers_goodput[flow_id]
                            if df_i.empty:
                                d2_averages.append(0)
                            else:
                                d2_slice = df_i.loc[
                                    (df_i.index >= return_start) & (df_i.index < return_end),
                                    'bandwidth'
                                ]
                                d2_averages.append(d2_slice.mean() if len(d2_slice) > 0 else 0)
                        JFI_d2 = calculate_jains_index(d2_averages)

                        # Average the two dumbbells' JFIs
                        return_jain = (JFI_d1 + JFI_d2) / 2
                        return_jains_list.append(return_jain)

                    # After collecting all runs, compute mean/std
                    cross_mean = np.mean(cross_jains_list) if len(cross_jains_list) > 0 else 0
                    cross_std  = np.std(cross_jains_list)  if len(cross_jains_list) > 0 else 0
                    ret_mean   = np.mean(return_jains_list) if len(return_jains_list) > 0 else 0
                    ret_std    = np.std(return_jains_list)  if len(return_jains_list) > 0 else 0

                    # Append to results for this parameter set
                    results.append([
                        protocol, bw, delay*2, mult,
                        cross_mean, cross_std,
                        ret_mean,   ret_std
                    ])

        # Convert to DataFrame
        summary_data = pd.DataFrame(results, columns=[
            'protocol', 'bandwidth', 'delay', 'qmult',
            'fairness_cross_mean', 'fairness_cross_std',
            'fairness_return_mean','fairness_return_std'
        ])

        # (Optional) Save or plot for this qmult

        # -------------
        # Example of plotting
        # -------------
        # We'll make two figures: cross scenario and return scenario
        fig_cross, ax_cross = plt.subplots(nrows=1, ncols=1,figsize=(3.7,1.8))
        fig_return, ax_return = plt.subplots(nrows=1, ncols=1,figsize=(3.7,1.8))

        markers_protocol = {
            'cubic': 'x',
            'orca': '+',
            'bbr': '.',
            'sage': '*',
            'pcc': '_',
            'bbr3': '^'
        }
        LINEWIDTH = 1
        ELINEWIDTH = 0.75
        CAPTHICK = ELINEWIDTH
        CAPSIZE = 2

        for protocol in PROTOCOLS:
            proto_data = summary_data[summary_data['protocol'] == protocol].copy()
            proto_data = proto_data.set_index('delay').sort_index()

            # color, marker
            color = COLOR.get(protocol, 'black')
            marker = markers_protocol.get(protocol, 'o')

            # CROSS scenario
            (m1, caps1, bars1) = ax_cross.errorbar(
                x=proto_data.index, 
                y=proto_data['fairness_cross_mean'],
                yerr=proto_data['fairness_cross_std'],
                marker=marker, linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE,
                capthick=CAPTHICK, color=color, label=f"{(lambda p: 'bbrv1' if p == 'bbr' else 'bbrv3' if p == 'bbr3' else 'vivace' if p == 'pcc' else p)(protocol)}-cross"
            )
            [bar.set_alpha(0.5) for bar in bars1]
            [cap.set_alpha(0.5) for cap in caps1]

            # RETURN scenario
            (m2, caps2, bars2) = ax_return.errorbar(
                x=proto_data.index,
                y=proto_data['fairness_return_mean'],
                yerr=proto_data['fairness_return_std'],
                marker=marker, linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE,
                capthick=CAPTHICK, color=color, label=f"{(lambda p: 'bbrv1' if p == 'bbr' else 'bbrv3' if p == 'bbr3' else 'vivace' if p == 'pcc' else p)(protocol)}-return"
            )
            [bar.set_alpha(0.5) for bar in bars2]
            [cap.set_alpha(0.5) for cap in caps2]

        # Style cross figure
        ax_cross.set_xlabel("RTT (ms)")
        ax_cross.set_ylabel("Jain's Index\n")
        ax_cross.set_ylim([0.4, 1.05])
        ax_cross.xaxis.set_major_formatter(ScalarFormatter())
        ax_cross.yaxis.set_major_formatter(ScalarFormatter())

        # Style return figure
        ax_return.set_xlabel("RTT (ms)")
        ax_return.set_ylabel("Jain's Index\n")
        ax_return.set_ylim([0.4, 1.05])
        ax_return.xaxis.set_major_formatter(ScalarFormatter())
        ax_return.yaxis.set_major_formatter(ScalarFormatter())

        # Get legend handles and labels from each axis
        cross_handles, cross_labels = ax_cross.get_legend_handles_labels()
        return_handles, return_labels = ax_return.get_legend_handles_labels()
        cross_handles = [h[0] for h in cross_handles]

        return_handles = [h[0] for h in return_handles]

        fig_cross.legend(cross_handles, cross_labels, ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.28), columnspacing=0.8, handletextpad=0.9)
        fig_return.legend(return_handles, return_labels, ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.28), columnspacing=0.8, handletextpad=0.9)
        # Save or show figures
        fig_cross.tight_layout()
        fig_cross.savefig(f"jains_cross_qmult_{mult}.pdf", dpi=1080)
        plt.close(fig_cross)

        fig_return.tight_layout()
        fig_return.savefig(f"jains_return_qmult_{mult}.pdf", dpi=1080)
        plt.close(fig_return)

        # Optionally store in a global list
        all_dataframes.append(summary_data)

    # Concatenate final DF if needed
    final_df = pd.concat(all_dataframes, ignore_index=True)

