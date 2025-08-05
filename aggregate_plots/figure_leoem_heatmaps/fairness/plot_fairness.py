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
mymodule_dir = os.path.join(script_dir, '../../../..')
sys.path.append(mymodule_dir)

from core.config import *
from core.plotting import *



bent_pipe_link_bandwidth = 100
num_flows = 2

HOME_DIR = os.environ.get("HOME", ".")
base_results_dir = os.path.join(HOME_DIR, "cctestbed", "LeoEM", "results_LeoEM")

path_keys = list(PATHS_INFO.keys())
row_labels = [PATHS_INFO[k]["label"] for k in path_keys]


def parse_sage_file(fpath):
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
                bws.append(bw_bps / 1e6)
    except Exception:
        return pd.DataFrame(columns=["time", "bandwidth_mbps"])
    if not times:
        return pd.DataFrame(columns=["time", "bandwidth_mbps"])
    return pd.DataFrame({"time": times, "bandwidth_mbps": bws})


def compute_mean_std(path_key, proto, m):
    base_q = PATHS_INFO[path_key]["queue"]
    switch_q = int(base_q * m)
    all_ratios = []

    for run in RUNS:
        run_dir = os.path.join(
            base_results_dir,
            f"{path_key}_{bent_pipe_link_bandwidth}mbit_{switch_q}pkts_{num_flows}flows_{proto}",
            f"run{run}"
        )
        print(f"Processing run directory: {run_dir}")
        if not os.path.isdir(run_dir):
            continue


        pattern = os.path.join(run_dir, "csvs", "x*.csv")
        files = sorted(glob.glob(pattern))
        if len(files) < num_flows:
            continue

        series = []
        for fp in files:

            try:
                df = pd.read_csv(fp)
            except Exception:
                continue
            if "time" not in df.columns or "bandwidth" not in df.columns:
                continue

            df['time'] = df['time'].astype(float).astype(int)
            max_t = df['time'].max()
            cutoff = max_t - 100
            window = df[df['time'] >= cutoff]
            if window.empty:
                continue

            window = window.drop_duplicates(subset='time').set_index('time')
            series.append(window['bandwidth'])

        if len(series) < num_flows:
            continue

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

df_mean, df_std = {}, {}
for m in [1]:
    dfm = pd.DataFrame(0.0, index=row_labels, columns=PROTOCOLS_LEOEM)
    dfs = pd.DataFrame(0.0, index=row_labels, columns=PROTOCOLS_LEOEM)
    for key, label in zip(path_keys, row_labels):
        for proto in PROTOCOLS_LEOEM:
            mu, sigma = compute_mean_std(key, proto, m)
            dfm.at[label, proto] = mu
            dfs.at[label, proto] = sigma
    df_mean[m] = dfm
    df_std[m] = dfs


cmap = LinearSegmentedColormap.from_list("r_y_g", ["red", "yellow", "green"], N=256)
norm = Normalize(vmin=0.5, vmax=1)

fig, ax = plt.subplots(figsize=(10, 7))

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

ax.set_xticks(np.arange(len(PROTOCOLS_LEOEM)))
ax.set_xticklabels([rf"\textbf{{{PROTOCOLS_FRIENDLY_NAME_LEO[p]}}}" for p in PROTOCOLS_LEOEM], rotation=0, ha="center", fontsize=18)

ax.set_yticks(np.arange(len(row_labels)))
ax.set_yticklabels("")
#ax.set_yticklabels([rf"\textbf{{{r}}}" for r in row_labels], fontsize=14)


# Overlay “mean ± std” text inside each cell
for i in range(dfm.shape[0]):
    for j in range(dfm.shape[1]):
        mu = dfm.iat[i, j]
        sigma = dfs.iat[i, j]
        text_color = "black"
        ax.text(j, i, f"{mu:.2f}±{sigma:.1f}", ha="center", va="center", color=text_color, fontsize=20)


cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label(r"\textbf{Mean Goodput Ratio}", labelpad=20, rotation=90, fontsize=24)
cbar.ax.tick_params(labelsize=20)

plt.tight_layout()
plt.savefig("heatmap_leo_goodput_ratio.pdf", dpi=1080)
