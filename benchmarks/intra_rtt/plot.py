#!/usr/bin/env python3
import os, sys, glob
from typing import Optional, List, Tuple

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from matplotlib.colors import LinearSegmentedColormap

# Optional style (keep if you have it installed and like it)
import scienceplots
plt.style.use('science')
plt.rcParams['text.usetex'] = True

# ------------ Project paths / imports ------------
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)

from core.config import *
from core.plotting import *

EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/benchmarks/results_intra_rtt_threading"

# Heatmap grids
BWS    = [20, 60, 100, 140, 180]                     # Mbps
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]   # ms
AQMS   = ['fifo']    # adjust if needed
QMULT  = 1.0         # Buffer size = 1×BDP (in packets)
RUNS = [1, 2, 3]
LOSSES=[0]
PROTOCOLS = ['sage', 'sage_reanimated']
# Make the figures bigger and easier to read
mpl.rcParams.update({
    "figure.figsize": (7.5, 6.0),
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
})

DELAY_SEQ_CMAP = LinearSegmentedColormap.from_list(
    "delay_seq_gyr",
    ["#1a9850",  # green (best, ratio=1)
    "#fee08b",  # yellow (moderate)
    "#d7301f"], # red (worst, high)
    N=256
)

# ------------ Helpers ------------
def pick_latest(dirs: List[str], pattern: str) -> Optional[str]:
    matches: List[str] = []
    for d in dirs:
        matches.extend(glob.glob(os.path.join(d, pattern)))
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)

def load_pair_timeseries(PATH: str, protocol: str, delay_ms: int) -> Tuple[Optional[pd.Series], Optional[pd.Series]]:
    search_dirs = [os.path.join(PATH, "csvs"), PATH]

    x1_path = pick_latest(search_dirs, "x1*.csv")
    x2_path = pick_latest(search_dirs, "x2*.csv")

    # c-files depend on protocol naming
    if protocol in ("vivace-uspace", "astraea"):
        c1_pattern = "c1*.csv"
        c2_pattern = "c2*.csv"
    else:
        c1_pattern = "c1*_ss.csv"
        c2_pattern = "c2*_ss.csv"

    c1_path = pick_latest(search_dirs, c1_pattern)
    c2_path = pick_latest(search_dirs, c2_pattern)

    if not all([x1_path, x2_path, c1_path, c2_path]):
        return None, None

    # Load CSVs
    r1g = pd.read_csv(x1_path).reset_index(drop=True)
    r2g = pd.read_csv(x2_path).reset_index(drop=True)
    r1s = pd.read_csv(c1_path).reset_index(drop=True)
    r2s = pd.read_csv(c2_path).reset_index(drop=True)

    # Ensure integer-second time
    for df in (r1g, r2g, r1s, r2s):
        df['time'] = df['time'].apply(lambda x: int(float(x)))

    # Steady-state window
    start_time =  delay_ms
    end_time   = 2 * delay_ms - 1

    def w(df):
        return df[(df['time'] > start_time) & (df['time'] <= end_time)] \
                .drop_duplicates('time').set_index('time')

    r1g, r2g, r1s, r2s = w(r1g), w(r2g), w(r1s), w(r2s)

    # Align intersection of timestamps
    times = r1g.index.intersection(r2g.index).intersection(r1s.index).intersection(r2s.index)
    if len(times) == 0:
        return None, None

    r1g = r1g.loc[times]
    r2g = r2g.loc[times]
    r1s = r1s.loc[times]
    r2s = r2s.loc[times]

    # Filter out timestamps where both throughputs are zero or missing
    both_zero = (r1g['bandwidth'] <= 0) & (r2g['bandwidth'] <= 0)
    mask = ~both_zero

    if not mask.any():
        return None, None

    goodput_ratio = (np.minimum(r1g['bandwidth'], r2g['bandwidth']) /
                    np.maximum(r1g['bandwidth'], r2g['bandwidth']))[mask]

    # NOTE: per request, use srtt / delay (no *2)
    delay_ratio = (((r1s['rtt'] / (delay_ms)) + (r2s['rtt'] / (delay_ms))) / 2.0)[mask]

    if goodput_ratio.empty or delay_ratio.empty:
        return None, None

    return goodput_ratio, delay_ratio

def compute_cell_ratios(bw: int, delay_ms: int, protocol: str, aqm: str, runs: List[int]) -> Tuple[float, float]:
    # BDP in bytes, then packets (MSS=1500B). Buffer = 1×BDP.
    BDP_BYTES = int(bw * (2 ** 20) * delay_ms * 1e-3 / 8)
    BDP_PKTS  = BDP_BYTES / 1500.0
    q_pkts    = int(QMULT * BDP_PKTS)

    goodput_samples = []
    delay_samples   = []

    for run in runs:
        PATH = (
            f"{EXPERIMENT_PATH}/Dumbell_{bw}mbit_{delay_ms}ms_"
            f"{q_pkts}pkts_0loss_2flows_{protocol}_{aqm}aqm/run{run}"
        )
        #print(f"Processing {PATH}")
        gr, dr = load_pair_timeseries(PATH, protocol, delay_ms)
        if gr is None or dr is None:
            continue
        goodput_samples.append(gr.values)
        delay_samples.append(dr.values)

    if len(goodput_samples) == 0:
        return np.nan, np.nan

    goodput_samples = np.concatenate(goodput_samples, axis=0)
    delay_samples   = np.concatenate(delay_samples, axis=0)

    return float(np.mean(goodput_samples)), float(np.mean(delay_samples))

def plot_heatmap_ratio_sequential(matrix, bws, delays, title, cbar_label, outfile):

    fig, ax = plt.subplots()  # size set via rcParams above

    data = np.ma.masked_invalid(matrix)
    cmap = plt.get_cmap("RdYlGn").copy()     # red→yellow→green, high=green
    cmap.set_bad(color="0.5")                # grey for missing

    vmin = 0.0
    vmax = 1.0 if np.nanmax(matrix) <= 1.0 else float(np.nanmax(matrix))
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

    im = ax.imshow(
        data, origin="lower", aspect="auto", interpolation="nearest",
        cmap=cmap, norm=norm
    )

    ax.set_xticks(range(len(bws)));    ax.set_xticklabels(bws)
    ax.set_yticks(range(len(delays))); ax.set_yticklabels(delays)
    ax.set_xlabel('Bottleneck Bandwidth (Mbps)')
    ax.set_ylabel('RTT (ms)')
    ax.set_title(title)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    cbar.formatter = ScalarFormatter(); cbar.update_ticks()

    # Mark NaNs explicitly
    for (i, j), val in np.ndenumerate(matrix):
        if np.isnan(val):
            ax.text(j, i, '×', ha='center', va='center', fontsize=11,
                    color='white', fontweight='bold')
        else:
            rgba = im.cmap(im.norm(val))
            r, g, b = rgba[:3]
            L = 0.2126*r + 0.7152*g + 0.0722*b  # relative luminance
            txt_color = 'black' if L > 0.6 else 'white'
            ax.text(j, i, "{:.2f}".format(val), ha='center', va='center',
                    fontsize=9, color=txt_color)
    fig.tight_layout()
    plt.savefig(outfile, dpi=400, bbox_inches='tight')
    plt.close(fig)

def plot_delay_ratio_one_sided(matrix, bws, delays, title, cbar_label, outfile, vmin=1.0, vmax=None):
    data = np.array(matrix, dtype=float, copy=True)

    # Clip any accidental <1 values up to 1 for coloring, but keep NaNs as NaN
    with np.errstate(invalid='ignore'):
        data[data < 1.0] = 1.0

    # Auto vmax if not provided: robust 95th percentile
    if vmax is None:
        if np.all(np.isnan(data)):
            vmax = 1.2  # fallback if everything missing
        else:
            vmax = float(np.nanquantile(data, 0.95))
            if vmax <= vmin:
                vmax = vmin + 0.1

    fig, ax = plt.subplots()

    cmap = DELAY_SEQ_CMAP.copy()
    cmap.set_bad(color="0.5")  # grey for NaNs
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

    im = ax.imshow(
        np.ma.masked_invalid(data),
        origin="lower", aspect="auto", interpolation="nearest",
        cmap=cmap, norm=norm
    )

    ax.set_xticks(range(len(bws)));    ax.set_xticklabels(bws)
    ax.set_yticks(range(len(delays))); ax.set_yticklabels(delays)
    ax.set_xlabel('Bottleneck Bandwidth (Mbps)')
    ax.set_ylabel('RTT (ms)')
    ax.set_title(title)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)

    # Mark NaNs with ×
    for (i, j), val in np.ndenumerate(matrix):
        if np.isnan(val):
            ax.text(j, i, '×', ha='center', va='center', fontsize=11,
                    color='white', fontweight='bold')
        else:
            rgba = im.cmap(im.norm(val))
            r, g, b = rgba[:3]
            L = 0.2126*r + 0.7152*g + 0.0722*b  # relative luminance
            txt_color = 'black' if L > 0.6 else 'white'
            ax.text(j, i, "{:.2f}".format(val), ha='center', va='center',
                    fontsize=9, color=txt_color)
    fig.tight_layout()
    plt.savefig(outfile, dpi=400, bbox_inches='tight')
    plt.close(fig)

def main():
    bw_to_j    = {bw: j for j, bw in enumerate(BWS)}
    delay_to_i = {d: i for i, d in enumerate(DELAYS)}

    for aqm in AQMS:
        for protocol in PROTOCOLS:
            goodput_ratio_mat = np.full((len(DELAYS), len(BWS)), np.nan, dtype=float)
            delay_ratio_mat   = np.full((len(DELAYS), len(BWS)), np.nan, dtype=float)

            for bw in BWS:
                for d in DELAYS:
                    mean_goodput_ratio, mean_delay_ratio = compute_cell_ratios(bw, d, protocol, aqm, RUNS)
                    i = delay_to_i[d]; j = bw_to_j[bw]
                    goodput_ratio_mat[i, j] = mean_goodput_ratio
                    delay_ratio_mat[i, j]   = mean_delay_ratio

            friendly = PROTOCOLS_FRIENDLY_NAMES.get(protocol, protocol)
            base = f"{protocol}_{aqm}"

            # Goodput ratio: higher is better (use red→green sequential)
            plot_heatmap_ratio_sequential(
                goodput_ratio_mat,
                BWS, DELAYS,
                title=f"Goodput Ratio min/max at each time step avereaged over time series (higher = better)\n{friendly} / {aqm.upper()}",
                cbar_label="Goodput Ratio",
                outfile=f"heatmap_goodput_ratio_{base}.pdf"
            )

            # Delay ratio: green at 1, then yellow→red as it increases
            plot_delay_ratio_one_sided(
                delay_ratio_mat,
                BWS, DELAYS,
                title=f"Delay Ratio (green at 1 → red as it grows)\n{friendly} / {aqm.upper()}",
                cbar_label="avg srtt / (delay)",
                outfile=f"heatmap_delay_ratio_{base}.pdf",
                vmin=1.0,
                vmax=None
            )

if __name__ == "__main__":
    main()
