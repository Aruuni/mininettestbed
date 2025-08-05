#!/usr/bin/env python3
import os
import sys
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib import font_manager

# Font setup
libertine_reg_path = "/usr/share/fonts/opentype/linux-libertine/LinLibertine_R.otf"
libertine_bold_path = "/usr/share/fonts/opentype/linux-libertine/LinLibertine_RB.otf"
font_manager.fontManager.addfont(libertine_reg_path)
font_manager.fontManager.addfont(libertine_bold_path)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Linux Libertine O']
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['font.size'] = 40
plt.rcParams['text.usetex'] = True

# Configuration
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '../../../..'))
sys.path.append(project_root)
from core.config import *
from core.plotting import *

bent_pipe_link_bandwidth = 100
num_flows = 1
IGNORE_SEC = 10
HOME = os.environ.get('HOME', '.')
base_results_dir = os.path.join(HOME, 'cctestbed', 'LeoEM', 'results_LeoEM')

# Labels for rows
row_labels = [info['label'] for info in PATHS_INFO.values()]

# 1) Parse base ping delays
def parse_ping_base_delay(txt_path):
    times = []
    if not os.path.isfile(txt_path):
        print(f"WARNING: ping log missing: {txt_path}")
        return times
    with open(txt_path) as f:
        for line in f:
            m = re.search(r"icmp_seq=\d+.*time=([0-9]+\.?[0-9]*)\s*ms", line)
            if m:
                times.append(float(m.group(1)))
    return times

# Build base_delay dictionary
base_delay = {}
for key, info in PATHS_INFO.items():
    ping_path = os.path.join(
        base_results_dir,
        f"{key}_{bent_pipe_link_bandwidth}mbit_{info['queue']}pkts_{num_flows}flows_ping/run1/ping.txt"
    )
    base_delay[key] = parse_ping_base_delay(ping_path)

# 2) Parse Sage 'ss' output for SRTT with timestamps
def parse_sage_srtt(file_path):
    timestamps = []
    srtts = []
    if not os.path.isfile(file_path):
        print(f"WARNING: Sage srtt file missing: {file_path}")
        return np.array([]), np.array([])
    with open(file_path) as f:
        for line in f:
            # Expect lines like: <unix_time>, ... rtt:<srtt>/<mdev> ...
            m = re.search(r"^(?P<ts>[0-9]+\.[0-9]+),.*?rtt:(?P<sr>[0-9]+\.?[0-9]*)/", line)
            if m:
                timestamps.append(float(m.group('ts')))
                srtts.append(float(m.group('sr')))
    if not timestamps:
        return np.array([]), np.array([])
    # convert to relative seconds since start
    t0 = timestamps[0]
    rel_times = np.array(timestamps) - t0
    secs = rel_times.astype(int)
    return secs, np.array(srtts)

# 3) Compute delay inflation stats
def compute_inflation(path_key, proto):
    seq_rtts = base_delay.get(path_key, [])
    if not seq_rtts:
        return 0.0, 0.0
    ratios = []
    # CSV naming: vivace-uspace & astraea use 'c1.csv'; others use 'c1_ss.csv'
    ss_name = 'c1.csv' if proto in ('vivace-uspace', 'astraea') else 'c1_ss.csv'

    for run in RUNS:
        if proto == 'sage':
            file_path = os.path.join(
                base_results_dir,
                f"{path_key}_{bent_pipe_link_bandwidth}mbit_{PATHS_INFO[path_key]['queue']}pkts_{num_flows}flows_{proto}/run{run}/{ss_name}"
            )
            secs, srtts = parse_sage_srtt(file_path)
        else:
            file_path = os.path.join(
                base_results_dir,
                f"{path_key}_{bent_pipe_link_bandwidth}mbit_{PATHS_INFO[path_key]['queue']}pkts_{num_flows}flows_{proto}/run{run}/csvs/{ss_name}"
            )
            if not os.path.isfile(file_path):
                continue
            df = pd.read_csv(file_path, usecols=['time','srtt'])
            secs = df['time'].astype(int).values
            srtts = df['srtt'].values
        if len(srtts) == 0:
            continue
        for sec, sr in zip(secs, srtts):
            if sec < IGNORE_SEC or sec >= len(seq_rtts) - IGNORE_SEC:
                continue
            if seq_rtts[sec] > 0:
                ratios.append(sr / seq_rtts[sec])

    if not ratios:
        return 0.0, 0.0
    return float(np.mean(ratios)), float(np.std(ratios))

# 4) Aggregate results
df_mean = pd.DataFrame(0.0, index=row_labels, columns=PROTOCOLS_LEOEM)
df_std = pd.DataFrame(0.0, index=row_labels, columns=PROTOCOLS_LEOEM)
for key, info in PATHS_INFO.items():
    lbl = info['label']
    for proto in PROTOCOLS_LEOEM:
        mu, sigma = compute_inflation(key, proto)
        df_mean.at[lbl, proto] = mu
        df_std.at[lbl, proto] = sigma

print("Mean delay inflation table:\n", df_mean)
print("Std delay inflation table:\n", df_std)

# 5) Plot heatmap
cmap = LinearSegmentedColormap.from_list('g_y_r', ['green','yellow','red'], N=256)
vmax = np.nanmax(df_mean.values)
norm = Normalize(vmin=1, vmax=vmax)
fig, ax = plt.subplots(figsize=(10,7))
im = ax.imshow(df_mean.values, origin='upper', aspect='auto', interpolation='nearest', cmap=cmap, norm=norm)
ax.set_xticks(np.arange(len(PROTOCOLS_LEOEM)))
ax.set_xticklabels([rf"\textbf{{{PROTOCOLS_FRIENDLY_NAME_LEO[p]}}}" for p in PROTOCOLS_LEOEM], rotation=0, ha='center', fontsize=18)
ax.set_yticks(np.arange(len(row_labels)))
ax.set_yticklabels("")
for i, lbl in enumerate(row_labels):
    for j, proto in enumerate(PROTOCOLS_LEOEM):
        mu = df_mean.iat[i,j]
        sigma = df_std.iat[i,j]
        ax.text(j, i, f"{max(1, mu):.2f}±{sigma:.1f}", ha='center', va='center', fontsize=20)
cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label(r"\textbf{Mean Norm. Delay}", labelpad=20, rotation=90, fontsize=24)
plt.tight_layout()
plt.savefig("heatmap_delay_inflation.pdf", dpi=300)