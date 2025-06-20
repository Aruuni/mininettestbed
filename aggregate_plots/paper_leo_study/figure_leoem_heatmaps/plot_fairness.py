import os, sys, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib import font_manager

libertine_reg_path = "/usr/share/fonts/opentype/linux-libertine/LinLibertine_R.otf"
libertine_bold_path = "/usr/share/fonts/opentype/linux-libertine/LinLibertine_RB.otf"

font_manager.fontManager.addfont(libertine_reg_path)
font_manager.fontManager.addfont(libertine_bold_path)

plt.rcParams['font.family']    = 'serif'
plt.rcParams['font.serif']     = ['Linux Libertine O']
plt.rcParams['font.weight']    = 'bold'
plt.rcParams['font.size']      = 40
plt.rcParams['text.usetex'] = True

script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)

from core.config import *
from core.plotting import *

protocols = ["astraea", "bbr3", "sage", "vivace-uspace", "cubic", "satcp"]

bent_pipe_link_bandwidth = 100
num_flows = 2  # Experiment now has 2 concurrent flows

HOME_DIR = os.environ.get("HOME", ".")
base_results_dir = os.path.join(HOME_DIR, "cctestbed", "LeoEM", "resutls_single_flow")

# Combine “basename (no .log)” → {queue, label}
paths_info = {
    "Starlink_SD_SEA_15_ISL_path":     { "queue": 582, "label": "San Diego to Seattle (ISL)" },
    "Starlink_SD_SEA_15_BP_path":      { "queue": 219, "label": "San Diego to Seattle (BP)" },
    "Starlink_SEA_NY_15_ISL_path":     { "queue": 388, "label": "Seattle to New York (ISL)" },
    "Starlink_SEA_NY_15_BP_path":      { "queue": 326, "label": "Seattle to New York (BP)" },
    "Starlink_SD_NY_15_ISL_path":      { "queue": 522, "label": "San Diego to New York (ISL)" },
    "Starlink_SD_NY_15_BP_path":       { "queue": 408, "label": "San Diego to New York (BP)" },
    "Starlink_NY_LDN_15_ISL_path":     { "queue": 696, "label": "New York to London (ISL)" },
    "Starlink_SD_Shanghai_15_ISL_path":{ "queue": 740, "label": "San Diego to Shanghai (ISL)" }
}

path_keys = list(paths_info.keys())
row_labels = [paths_info[k]["label"] for k in path_keys]


def parse_sage_file(fpath):
    """
    Parses a Sage output file at fpath. Looks for the line '----START----',
    then reads subsequent lines of the form:
      time, bandwidth_bps, other_value
    Returns a pandas DataFrame with columns ['time', 'bandwidth_mbps'].
    """
    times, bws = [], []
    seen_start = False
    try:
        with open(fpath, "r") as f:
            for line in f:
                line = line.strip()
                if not seen_start:
                    if line == "----START----":
                        seen_start = True
                    continue
                parts = line.split(",")
                if len(parts) < 2:
                    continue
                try:
                    t = float(parts[0]); bw_bps = float(parts[1])
                except ValueError:
                    continue
                times.append(int(t))
                bws.append(bw_bps / 1e6)  # convert to Mbps
    except Exception:
        return pd.DataFrame(columns=["time", "bandwidth_mbps"])
    if not times:
        return pd.DataFrame(columns=["time", "bandwidth_mbps"])
    return pd.DataFrame({"time": times, "bandwidth_mbps": bws})


def compute_mean_std(path_key, proto, m):
    """
    Computes goodput ratios over the last 100 seconds on a per-sample basis:
      • For each run, load both flow CSVs (Sage or non-sage).
      • Convert 'time' to integer seconds, find max_t, set cutoff = max_t - 100.
      • Filter to time ≥ cutoff, drop duplicate times, set 'time' as index.
      • Align the two flows by joining on index, drop NaNs and zero-bandwidth points.
      • For each timestamp, compute ratio = min(b1, b2) / max(b1, b2).
      • Collect all per-timestamp ratios across runs and return their mean/std.
    """
    base_q = paths_info[path_key]["queue"]
    switch_q = int(base_q * m)
    all_ratios = []

    for run in RUNS:
        run_dir = os.path.join(
            base_results_dir,
            f"{path_key}_{bent_pipe_link_bandwidth}mbit_{switch_q}pkts_{num_flows}flows_{proto}",
            f"run{run}"
        )
        if not os.path.isdir(run_dir):
            continue

        if proto == "sage":
            pattern = os.path.join(run_dir, "c*.csv")
        else:
            pattern = os.path.join(run_dir, "csvs", "x*.csv")
        files = sorted(glob.glob(pattern))
        if len(files) < num_flows:
            continue

        series = []
        for fp in files:
            if proto == "sage":
                df = parse_sage_file(fp).rename(columns={"bandwidth_mbps": "bandwidth"})
            else:
                try:
                    df = pd.read_csv(fp)
                except Exception:
                    continue
                if "time" not in df.columns or "bandwidth" not in df.columns:
                    continue

            # Cast time to integer seconds and window to last 100s
            df['time'] = df['time'].astype(float).astype(int)
            max_t = df['time'].max()
            cutoff = max_t - 100
            window = df[df['time'] >= cutoff]
            if window.empty:
                continue

            # Deduplicate and index by time
            window = window.drop_duplicates(subset='time').set_index('time')
            series.append(window['bandwidth'])

        if len(series) < num_flows:
            continue

        # Align flows and compute per-sample ratios
        merged = pd.concat(series, axis=1, join='inner')
        merged.columns = ['b1', 'b2']
        merged = merged.dropna()
        merged = merged[(merged['b1'] > 0) | (merged['b2'] > 0)]
        if merged.empty:
            continue

        ratios = (merged.min(axis=1) / merged.max(axis=1)).values
        all_ratios.append(ratios)

    if all_ratios:
        flat = np.concatenate(all_ratios)
        return float(flat.mean()), float(flat.std())
    else:
        return 0.0, 0.0

# Generate heatmaps of mean ± std as before

df_mean, df_std = {}, {}
for m in QMULTS:
    dfm = pd.DataFrame(0.0, index=row_labels, columns=protocols)
    dfs = pd.DataFrame(0.0, index=row_labels, columns=protocols)
    for key, label in zip(path_keys, row_labels):
        for proto in protocols:
            mu, sigma = compute_mean_std(key, proto, m)
            dfm.at[label, proto] = mu
            dfs.at[label, proto] = sigma
    df_mean[m] = dfm
    df_std[m] = dfs

# Create a continuous “red → yellow → green” colormap, fixed to [0, 1]
cmap = LinearSegmentedColormap.from_list("r_y_g", ["red", "yellow", "green"], N=256)
norm = Normalize(vmin=0.5, vmax=1)

fig, axes = plt.subplots(1, len(QMULTS), figsize=(30, 8), sharey=False)

for idx, m in enumerate(QMULTS):
    ax = axes[idx]
    dfm = df_mean[m]
    dfs = df_std[m]

    im = ax.imshow(
        dfm.values,
        origin="upper",
        aspect="auto",
        interpolation="nearest",
        cmap=cmap,
        norm=norm
    )

    # X‐axis: friendly protocol names, horizontal
    ax.set_xticks(np.arange(len(protocols)))
    ax.set_xticklabels(
        [rf"\textbf{{{PROTOCOLS_FRIENDLY_NAME_LEO[p]}}}" for p in protocols],
        rotation=0,
        ha="center",
        fontsize=18
    )

    # Y‐axis: show path labels only on the first subplot
    if idx == 0:
        ax.set_yticks(np.arange(len(row_labels)))
        ax.set_yticklabels([rf"\textbf{{{r}}}" for r in row_labels], fontsize=14)
    else:
        ax.set_yticks([])
        ax.set_yticklabels([])

    # Overlay “mean ± std” text inside each cell
    for i in range(dfm.shape[0]):
        for j in range(dfm.shape[1]):
            mu = dfm.iat[i, j]
            sigma = dfs.iat[i, j]
            text_color = "black" # if 0.3 <= mu <= 0.7 else "white"
            ax.text(
                j, i,
                f"{mu:.2f}±{sigma:.1f}",
                ha="center", va="center",
                color=text_color,
                fontsize=18
            )
    letter = chr(97 + idx)
    m_str  = f"{m}"
    # Subcaption below each heatmap
    ax.text(
        0.5, -0.08,
        rf"\textbf{{({letter}) Buffer Size: }}{m_str}\(\times\)\textbf{{BDP}}",
        ha="center", va="top",
        transform=ax.transAxes,
        fontsize=34   
    )

# Single colorbar on the far right, normalized to [0,1]
cbar_ax = fig.add_axes([0.90, 0.15, 0.025, 0.83])
cb = fig.colorbar(im, cax=cbar_ax)
cb.set_label(rf"\textbf{{Mean Goodput Ratio}}", labelpad=+20, rotation=90, fontsize=30)
cb.ax.tick_params(labelsize=20)
cb.ax.yaxis.set_label_position('right')
cb.ax.yaxis.tick_right()

# Adjust margins
plt.subplots_adjust(left=0.10, right=0.88, top=0.98, bottom=0.15)

# Save to PDF
plt.savefig("heatmap_leo_goodput_ratio.pdf", dpi=1080)
