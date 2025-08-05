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
mymodule_dir = os.path.join(script_dir, '../../../..')
sys.path.append(mymodule_dir)
from core.config import *
from core.plotting import *

PROTOCOLS_LEOEM = ["cubic", "satcp", "bbr3", "vivace-uspace", "sage", "astraea"]
bent_pipe_link_bandwidth = 100
num_flows = 1
HOME_DIR = os.environ.get("HOME", ".")
base_results_dir = os.path.join(HOME_DIR, "cctestbed", "LeoEM", "results_LeoEM_low_Burst")



row_labels = [info['label'] for info in PATHS_INFO.values()]

def compute_mean_std(path_key, proto, m):
    base_q = PATHS_INFO[path_key]["queue"]
    switch_q = int(base_q * m)
    runs = []
    for run in RUNS:
        csv_dir = os.path.join(
            base_results_dir,
            f"{path_key}_{bent_pipe_link_bandwidth}mbit_{switch_q}pkts_{num_flows}flows_{proto}",
            f"run{run}",
            "csvs"
        )
        if not os.path.isdir(csv_dir):
            continue
        pattern = "x*.csv"
        csv_files = glob.glob(os.path.join(csv_dir, pattern))
        file_means = []
        for fpath in csv_files:
            try:
                df = pd.read_csv(fpath)
                if "bandwidth" in df.columns:
                    file_means.append(df["bandwidth"].mean())
            except Exception:
                continue
        if file_means:
            runs.append(np.mean(file_means))
    if runs:
        return float(np.mean(runs)/ bent_pipe_link_bandwidth), float(np.std(runs)/ bent_pipe_link_bandwidth)
    return 0.0, 0.0

# Only plot for buffer = 1 x BDP
m = 1
df_mean = pd.DataFrame(index=row_labels, columns=PROTOCOLS_LEOEM, data=0.0)
df_std = pd.DataFrame(index=row_labels, columns=PROTOCOLS_LEOEM, data=0.0)
for key in PATHS_INFO:
    for proto in PROTOCOLS_LEOEM:
        mu, sigma = compute_mean_std(key, proto, m)
        df_mean.at[PATHS_INFO[key]['label'], proto] = mu
        df_std.at[PATHS_INFO[key]['label'], proto] = sigma

# Create colormap and normalization
cmap = LinearSegmentedColormap.from_list("r_y_g", ["red", "yellow", "green"], N=256)
norm = Normalize(vmin=0, vmax=1)

# Plot single heatmap
fig, ax = plt.subplots(figsize=(10, 7))
im = ax.imshow(df_mean.values, origin='upper', aspect='auto', interpolation='nearest', cmap=cmap, norm=norm)
# X-axis labels
ax.set_xticks(np.arange(len(PROTOCOLS_LEOEM)))
ax.set_xticklabels([rf"\textbf{{{PROTOCOLS_FRIENDLY_NAME_LEO[p]}}}" for p in PROTOCOLS_LEOEM], rotation=0, ha='center', fontsize=18)
# Y-axis labels
ax.set_yticks(np.arange(len(row_labels)))
ax.set_yticklabels("")
ax.set_yticklabels([rf"\textbf{{{r}}}" for r in row_labels], fontsize=14)

for i in range(df_mean.shape[0]):
    for j in range(df_mean.shape[1]):
        mu = df_mean.iat[i, j]
        sigma = df_std.iat[i, j]
        ax.text(j, i, f"{mu:.2f}±{sigma:.1f}", ha='center', va='center', color='black', fontsize=18)


cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label(r"\textbf{Mean Norm. Goodput}", labelpad=20, rotation=90, fontsize=24)
cbar.ax.tick_params(labelsize=20)

plt.tight_layout()
plt.savefig("heatmap_leoem_goodput.pdf", dpi=300)