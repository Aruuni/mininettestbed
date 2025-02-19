import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter

plt.rcParams['text.usetex'] = False

script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)
from core.config import *
from core.

# Configuration
ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_parking_lot/fifo" 
PROTOCOLS = ['cubic', 'astraea', 'bbr3', 'bbr1', 'sage']
BWS = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
QMULTS = [0.2, 1, 4]
RUNS = [1, 2, 3, 4, 5]
FLOWS = 4

# Ideal allocation: flow 1 gets 25, flows 2..4 get 75 each
ideal_allocation = np.array([25, 75, 75, 75])

def export_legend(legend, bbox=None, filename="legend.png"):
    fig = legend.figure
    fig.canvas.draw()
    if not bbox:
        bbox = legend.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(filename, dpi=1080, bbox_inches=bbox)

# Loop over each QMULT separately
for mult in QMULTS:
    data = []  # will store rows of [protocol, bw, delay, qmult, diff_mean, diff_std]

    for protocol in PROTOCOLS:
        for bw in BWS:
            for delay in DELAYS:
                # We collect "difference" values for each run
                difference_values = []

                # Define time window
                start_time = 2 * delay
                BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                BDP_IN_PKTS  = BDP_IN_BYTES / 1500

                for run in RUNS:
                    path = (f"{ROOT_PATH}/ParkingLot_{bw}mbit_{delay}ms_"
                            f"{int(mult * BDP_IN_PKTS)}pkts_0loss_{FLOWS}flows_22tcpbuf_{protocol}/run{run}")
                    spine_file = f"{path}/csvs/x1.csv"
                    rib_files  = [f"{path}/csvs/x{i}.csv" for i in range(2, FLOWS+1)]

                    # Check all files exist
                    if all(os.path.exists(f) for f in rib_files) and os.path.exists(spine_file):
                        # Flow 1 (spine)
                        df_spine = pd.read_csv(spine_file).reset_index(drop=True)
                        df_spine['time'] = df_spine['time'].astype(float).astype(int)
                        df_spine = df_spine[df_spine['time'] >= start_time]
                        df_spine = df_spine.drop_duplicates('time').set_index('time')
                        achieved_spine = df_spine['bandwidth'].mean()

                        # Flows 2..4 (ribs)
                        achieved_flows = [achieved_spine]  # start with flow 1's rate
                        for ribf in rib_files:
                            df_rib = pd.read_csv(ribf).reset_index(drop=True)
                            df_rib['time'] = df_rib['time'].astype(float).astype(int)
                            df_rib = df_rib[df_rib['time'] >= start_time]
                            df_rib = df_rib.drop_duplicates('time').set_index('time')
                            achieved_rib = df_rib['bandwidth'].mean()
                            achieved_flows.append(achieved_rib)

                        achieved_allocation = np.array(achieved_flows)
                        print(achieved_allocation)
                        # difference = sum( (achieved_i - ideal_i) / ideal_i ) for i=1..4
                        relative_diff = (achieved_allocation - ideal_allocation) / ideal_allocation
                        print(relative_diff)
                        diff_value = np.sum(relative_diff)
                        print(diff_value)
                        difference_values.append(diff_value)
                    else:
                        print(f"Folder or files missing for {path}")

                # After collecting difference_values for all runs
                if difference_values:
                    difference_values = np.array(difference_values)
                    mean_diff = difference_values.mean()
                    std_diff  = difference_values.std()
                    print(f" The data  {protocol}  {delay} {mean_diff} {mult}")
                    data.append([protocol, bw, delay, mult, mean_diff, std_diff])

    # Convert data to a DataFrame
    summary_df = pd.DataFrame(data, columns=[
        'protocol', 'bandwidth', 'delay', 'qmult', 'diff_mean', 'diff_std'
    ])
    
    # Subset by protocol
    cubic_df   = summary_df[summary_df['protocol'] == 'cubic'].set_index('delay')
    bbr3_df    = summary_df[summary_df['protocol'] == 'bbr3'].set_index('delay')
    bbr1_df    = summary_df[summary_df['protocol'] == 'bbr1'].set_index('delay')
    sage_df    = summary_df[summary_df['protocol'] == 'sage'].set_index('delay')
    astraea_df = summary_df[summary_df['protocol'] == 'astraea'].set_index('delay')

    # Plot settings
    LINEWIDTH   = 0.20
    ELINEWIDTH  = 0.75
    CAPTHICK    = ELINEWIDTH
    CAPSIZE     = 2

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(3, 1.2))

    def plot_diff(df, marker, label):
        if not df.empty:
            xvals = df.index * 2  # convert "delay" to RTT in ms
            yvals = df['diff_mean']
            yerr  = df['diff_std']
            markers, caps, bars = ax.errorbar(
                xvals, yvals,
                yerr=yerr,
                marker=marker,
                linewidth=LINEWIDTH,
                elinewidth=ELINEWIDTH,
                capsize=CAPSIZE,
                capthick=CAPTHICK,
                label=label
            )
            [bar.set_alpha(0.5) for bar in bars]
            [cap.set_alpha(0.5) for cap in caps]

    # Plot each protocol
    plot_diff(cubic_df,   'x', 'cubic')
    plot_diff(bbr1_df,    '.', 'bbrv1')
    plot_diff(bbr3_df,    '^', 'bbrv3')
    plot_diff(sage_df,    '*', 'sage')
    plot_diff(astraea_df, '2', 'astraea')

    # Perfect line at 0
    ax.axhline(0, color='red', linestyle='--', linewidth=ELINEWIDTH)
    ax.text(ax.get_xlim()[1], 0, ' perfect', color='red',
            fontsize=7, va='bottom', ha='right')

    # Labels
    ax.set(
        yscale='linear',
        xlabel='RTT (ms)',
        ylabel='Proportional Fairness',
        ylim=[-2, 0.4]  # Invert if you want 1 at the bottom & 0 at the top
    )
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_major_formatter(ScalarFormatter())

    # Build a 2-row "pyramid" legend
    handles, labels = ax.get_legend_handles_labels()
    # Convert errorbar handles if needed
    line_handles = [h[0] if isinstance(h, tuple) else h for h in handles]
    legend_map   = dict(zip(labels, line_handles))

    # Decide which protocols go top vs. bottom row
    handles_top = [legend_map.get('cubic'), legend_map.get('bbrv1'), legend_map.get('bbrv3')]
    labels_top  = ['cubic', 'bbrv1', 'bbrv3']

    handles_bottom = [legend_map.get('sage'), legend_map.get('astraea')]
    labels_bottom  = ['sage', 'astraea']


    legend_top = plt.legend(
        handles_top, labels_top,
        ncol=3,
        loc='upper center',
        bbox_to_anchor=(0.5, 1.4),
        columnspacing=1.0,
        handletextpad=0.5,
        labelspacing=0.1,
        borderaxespad=0.0
    )
    plt.gca().add_artist(legend_top)

    legend_bottom = plt.legend(
        handles_bottom, labels_bottom,
        ncol=2,
        loc='upper center',
        bbox_to_anchor=(0.5, 1.2),
        columnspacing=1.0,
        handletextpad=0.5,
        labelspacing=0.1,
        borderaxespad=0.0
    )

    # Save the plot for the current QMULT
    for fmt in ['pdf']:
        plt.savefig(f'allocation_diff_q{mult}.{fmt}', dpi=1080)
    plt.close(fig)
