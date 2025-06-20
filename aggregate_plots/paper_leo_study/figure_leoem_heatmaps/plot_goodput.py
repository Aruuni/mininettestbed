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

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Linux Libertine O']
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['font.size'] = 40
plt.rcParams['text.usetex'] = True

script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)

from core.config import *
from core.plotting import *

protocols = ["astraea", "bbr3", "sage", "vivace-uspace", "cubic", "satcp"]

bent_pipe_link_bandwidth = 100
num_flows               = 1

HOME_DIR         = os.environ.get("HOME", ".")
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

path_keys  = list(paths_info.keys())
row_labels = [paths_info[k]["label"] for k in path_keys]

def compute_mean_std(path_key, proto, m):
    base_q    = paths_info[path_key]["queue"]
    switch_q  = int(base_q * m)
    run_values = []
    for run in RUNS:
        csv_dir = os.path.join(
            base_results_dir,
            f"{path_key}_{bent_pipe_link_bandwidth}mbit_{switch_q}pkts_{num_flows}flows_{proto}",
            f"run{run}",
            "csvs"
        )
        if not os.path.isdir(csv_dir):
            continue

        if proto == "sage":
            # For “sage”, read client-side CSVs (c*.csv) and convert bps → Mbps
            csv_files = glob.glob(os.path.join(csv_dir, "c*.csv"))
        else:
            # For other protocols, read server-side CSVs (x*.csv) which are already in Mbps
            csv_files = glob.glob(os.path.join(csv_dir, "x*.csv"))

        if not csv_files:
            continue

        file_means = []
        for fpath in csv_files:
            try:
                df = pd.read_csv(fpath)
                if "bandwidth" in df.columns:
                    file_means.append(df["bandwidth"].mean())
            except Exception:
                pass

        if file_means:
            run_values.append(np.mean(file_means))

    if run_values:
        return float(np.mean(run_values)), float(np.std(run_values))
    else:
        return 0.0, 0.0

df_mean = {}
df_std  = {}

for m in QMULTS:
    dfm = pd.DataFrame(0.0, index=row_labels, columns=protocols)
    dfs = pd.DataFrame(0.0, index=row_labels, columns=protocols)
    for key, label in zip(path_keys, row_labels):
        for proto in protocols:
            mu, sigma = compute_mean_std(key, proto, m)
            dfm.at[label, proto] = mu
            dfs.at[label, proto] = sigma
    df_mean[m] = dfm
    df_std[m]  = dfs

# Create a continuous “red → yellow → green” colormap, fixed to [0, 100]
cmap = LinearSegmentedColormap.from_list("r_y_g", ["red", "yellow", "green"], N=256)
norm = Normalize(vmin=0, vmax=100)

fig, axes = plt.subplots(1, 3, figsize=(30, 8), sharey=False)

for idx, m in enumerate(QMULTS):
    ax  = axes[idx]
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

    # X‐axis: use friendly names, but keep them horizontal
    ax.set_xticks(np.arange(len(protocols)))

    ax.set_xticklabels(
        [rf"\textbf{{{PROTOCOLS_FRIENDLY_NAME_LEO[p]}}}" for p in protocols],
        rotation=0,
        ha="center",
        fontsize=18
    )

    # Y‐axis: show path labels only on the leftmost subplot
    if idx == 0:
        ax.set_yticks(np.arange(len(row_labels)))
        ax.set_yticklabels([rf"\textbf{{{r}}}" for r in row_labels], fontsize=14)
    else:
        ax.set_yticks([])
        ax.set_yticklabels([])

    # Overlay “mean ± std” text inside each cell
    for i in range(dfm.shape[0]):
        for j in range(dfm.shape[1]):
            mu    = dfm.iat[i, j]
            sigma = dfs.iat[i, j]
            # Conditional text color: black if mean ∈ [40,70], otherwise white
            text_color = "black" # if 40 <= mu <= 70 else "white"
            ax.text(j, i,
                f"{mu:.1f}±{sigma:.1f}",
                ha="center", va="center",
                color=text_color,
                fontsize=18
            )
    # Subcaption below each heatmap


    letter = chr(97 + idx) 
    m_str  = f"{m}" 

    ax.text(
        0.5, -0.10,
        rf"\textbf{{({letter}) Buffer Size: }}{m_str}\(\times\)\textbf{{BDP}}",
        ha="center", va="top",
        transform=ax.transAxes,
        fontsize=34,
    )

# Place single colorbar on the far right; shift it leftward for more space
cbar_ax = fig.add_axes([0.90, 0.15, 0.025, 0.83])
cb = fig.colorbar(im, cax=cbar_ax)
cb.set_label(rf"\textbf{{Mean Goodput Ratio}}", labelpad=+20, rotation=90, fontsize=30)
cb.ax.tick_params(labelsize=20)
cb.ax.yaxis.set_label_position('right')
cb.ax.yaxis.tick_right()

plt.subplots_adjust(left=0.10, right=0.88, top=0.98, bottom=0.15)

# Save to PDF
plt.savefig("heatmap_leo.pdf", dpi=1080)
