import os
import sys
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# disable LaTeX so that matplotlib doesn’t require a TeX installation
plt.rcParams['text.usetex'] = True
plt.rcParams['xtick.labelsize'] = 16
plt.rcParams['ytick.labelsize'] = 16
# add project root to path so we can import core modules
tb_dir = os.path.dirname(__file__)
root = os.path.abspath(os.path.join(tb_dir, '../../../..'))
sys.path.append(root)

from core.config import *
from core.plotting import *

num_flows = 2
plot_start = 200
plot_end   = 299 
base_results_dir = os.path.join(HOME_DIR, 'cctestbed', 'LeoEM', 'results_LeoEM')

paths_info = {
    "Starlink_SEA_NY_15_ISL_path": {"queue": 388, "label": "Seattle→New York (ISL)"},
    "Starlink_SEA_NY_15_BP_path":  {"queue": 326, "label": "Seattle→New York (BP)"},
    "Starlink_SD_NY_15_ISL_path": {"queue": 522, "label": "San Diego→New York (ISL)"},
    "Starlink_SD_NY_15_BP_path":  {"queue": 408, "label": "San Diego→New York (BP)"},
    "Starlink_NY_LDN_15_ISL_path": {"queue": 696, "label": "New York→London (ISL)"},
    "Starlink_SD_Shanghai_15_ISL_path": {"queue": 740, "label": "San Diego→Shanghai (ISL)"}
}

path_key = "Starlink_SD_NY_15_BP_path"
bent_pipe_link_bandwidth = 100
switch_q = paths_info[path_key]["queue"]
protocols = ['cubic', 'satcp', 'bbr3', 'vivace-uspace', 'sage', 'astraea']

def parse_ping(txt_path):
    """Return list of RTTs (ms) read from a ping.txt file."""
    rtts = []
    if not os.path.isfile(txt_path):
        return rtts
    with open(txt_path, 'r') as f:
        for line in f:
            m = re.search(r"time=([0-9.]+)\s*ms", line)
            if m:
                rtts.append(float(m.group(1)))
    return rtts

def load_sendrate(run_dir, num_flows=2):
    """
    Load per-flow sendrate series from x1.csv, x2.csv, ... files under run_dir/csvs.
    Returns a list of pandas.Series, one per flow.
    """
    csv_dir = os.path.join(run_dir, 'csvs')
    series_list = []
    for flow_id in range(1, num_flows + 1):
        fp = os.path.join(csv_dir, f'x{flow_id}.csv')
        if not os.path.isfile(fp):
            continue
        df = pd.read_csv(fp, sep=',', engine='python', encoding='utf-8-sig')
        df.columns = (df.columns
                        .str.strip()
                        .str.lower()
                        .str.replace(r'\s+', '_', regex=True))
        if 'time' not in df.columns or 'bandwidth' not in df.columns:
            continue
        df['time'] = df['time'].astype(float).astype(int)
        df = df.drop_duplicates('time').set_index('time')
        series_list.append(df['bandwidth'])
    return series_list

ping_dir = os.path.join(
    base_results_dir,
    f"{path_key}_{bent_pipe_link_bandwidth}mbit_{switch_q}pkts_1flows_ping",
    "run1"
)
txt_path = os.path.join(ping_dir, 'ping.txt')
print(f"Reading ping file: {txt_path}")
base_rtts = parse_ping(txt_path)
rtt_series = pd.Series(base_rtts, index=np.arange(len(base_rtts)))

for proto in protocols:
    friendly = PROTOCOLS_FRIENDLY_NAME_LEO[proto]
    color    = COLORS_LEO[proto]

    # create figure + primary axis
    fig, ax = plt.subplots(figsize=(8, 3))

    # collect sendrate data across runs
    runs = range(1, 6)
    flows_data = {j: [] for j in range(num_flows)}
    for run in runs:
        exp_dir = os.path.join(
            base_results_dir,
            f"{path_key}_{bent_pipe_link_bandwidth}mbit_{switch_q}pkts_{num_flows}flows_{proto}"
        )
        run_dir = os.path.join(exp_dir, f"run{run}")
        flows = load_sendrate(run_dir, num_flows=num_flows)
        for j in range(num_flows):
            if j < len(flows):
                ser = flows[j].sort_index().loc[plot_start:plot_end]
            else:
                ser = pd.Series(np.nan, index=np.arange(plot_start, plot_end+1))
            flows_data[j].append(ser)

    # compute mean ± std and plot with shaded error band
    for j in range(num_flows):
        df = pd.concat(flows_data[j], axis=1)
        mean_ser = df.mean(axis=1)
        std_ser  = df.std(axis=1)

        style = '-' if j == 0 else '--'
        ax.plot(mean_ser.index, mean_ser.values,
                style, color=color, lw=1.5,
                label=f"{friendly} flow#{j+1}")
        ax.fill_between(mean_ser.index,
                        mean_ser - std_ser,
                        mean_ser + std_ser,
                        color=color, alpha=0.2)

    # overlay RTT on twin Y-axis
    ax_rtt = ax.twinx()
    rtt_window = rtt_series.loc[plot_start:plot_end]
    if not rtt_window.empty:
        ax_rtt.plot(rtt_window.index, rtt_window.values,
                    linestyle=':', color='red', lw=1,
                    label='RTT')

    # pad axis limits
    ax.set_xlim(plot_start - 1, plot_end + 1)
    y1_min, y1_max = ax.get_ylim()
    ax.set_ylim(y1_min - 1, y1_max + 1)
    y2_min, y2_max = ax_rtt.get_ylim()
    ax_rtt.set_ylim(y2_min - 1, y2_max + 1)

    # ensure every axis is labeled
    ax.set_xlabel('Time (s)', fontsize=22)
    ax.set_ylabel('Goodput (Mbps)', fontsize=22)
    ax_rtt.set_ylabel('RTT (ms)', fontsize=22)

    # (Legend removed)

    plt.tight_layout()
    outfile = f'goodput_rtt_{path_key}_{proto}.pdf'
    plt.savefig(outfile, dpi=300)
    plt.close(fig)
    print(f"Saved {outfile}")
