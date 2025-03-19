import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

protocols = ["astraea", "bbr1", "bbr", "cubic", "sage",  "satcp"]
paths = [
    "Starlink_NY_LDN_15_ISL_path.log",
    "Starlink_SD_NY_15_BP_path.log",
    "Starlink_SD_NY_15_ISL_path.log",
    "Starlink_SEA_NY_15_BP_path.log",
    "Starlink_SD_Shanghai_15_ISL_path",
    "Starlink_SD_SEA_15_BP_path"
]
runs = [1, 2, 3, 4, 5]

bent_pipe_link_bandwidth = 100
switch_queue_size = 10000
num_flows = 1

HOME_DIR = os.environ.get('HOME', '.')
base_results_dir = os.path.join(HOME_DIR, "cctestbed", "LeoEM", "resutls_single_flow")


label_mapping = {
    "Starlink_NY_LDN_15_ISL_path": "New York to London (ISL)",
    "Starlink_SD_NY_15_BP_path": "Sydney to New York (BP)",
    "Starlink_SD_NY_15_ISL_path": "Sydney to New York (ISL)",
    "Starlink_SEA_NY_15_BP_path": "Seattle to New York (BP)",
    "Starlink_SD_Shanghai_15_ISL_path": "Sydney to Shanghai (ISL)",
    "Starlink_SD_SEA_15_BP_path": "Sydney to Seattle (BP)"
}

COLOR = {
    'cubic': '#0C5DA5',
    'bbr1': '#00B945',
    'bbr3': '#FF9500',
    'sage': '#FF2C01',
    'orca': '#845B97',
    'astraea': '#845B97',
}


results = {}

for path in paths:
    path_basename = path.split('.')[0]
    if path_basename not in results:
        results[path_basename] = {}
    for protocol in protocols:
        run_avgs = []
        for run in runs:
            run_dir = os.path.join(
                base_results_dir,
                f"{path_basename}_{bent_pipe_link_bandwidth}mbit_{switch_queue_size}pkts_{num_flows}flows_{protocol}",
                f"run{run}"
            )
            csvs_dir = os.path.join(run_dir, "csvs")
            if not os.path.isdir(csvs_dir):
                print(f"Directory {csvs_dir} does not exist")
                continue

            server_files = glob.glob(os.path.join(csvs_dir, "x*.csv"))
            if not server_files:
                print(f"No server CSV files found in {csvs_dir}")
                continue

            file_avgs = []
            for file in server_files:
                try:
                    df = pd.read_csv(file)
                    if 'bandwidth' in df.columns:
                        file_avg = df['bandwidth'].mean()
                        file_avgs.append(file_avg)
                    else:
                        print(f"'bandwidth' column not found in {file}")
                except Exception as e:
                    print(f"Error reading {file}: {e}")

            if file_avgs:
                run_avg = np.mean(file_avgs)
                run_avgs.append(run_avg)

        overall_avg = np.mean(run_avgs) if run_avgs else np.nan
        results[path_basename][protocol] = overall_avg



# for path_basename, protocols_dict in results.items():
#     print(f"{path_basename}:")
#     for protocol, avg in protocols_dict.items():
#         print(f"  {protocol}: {avg}")


paths_keys = list(results.keys())
display_labels = [label_mapping.get(key, key) for key in paths_keys]

x = np.arange(len(display_labels))
width = 0.1

fig, ax = plt.subplots(figsize=(12, 6))

for i, protocol in enumerate(protocols):
    protocol_avgs = []
    for key in paths_keys:
        avg = results[key].get(protocol, np.nan)
        protocol_avgs.append(avg)

    offsets = x - (len(protocols) / 2) * width + i * width + width / 2

    if protocol == 'bbr':
        plot_label = 'bbr3'
        color = COLOR.get('bbr3', '#333333')
    else:
        plot_label = protocol
        color = COLOR.get(protocol, '#333333')

    ax.bar(offsets, protocol_avgs, width, label=plot_label, color=color)

ax.set_ylabel('Average Goodput (Mbps)')
ax.set_title('Average Goodput per Path')
ax.set_xticks(x)
ax.set_xticklabels(display_labels, rotation=45, ha='right')

handles, labels = ax.get_legend_handles_labels()
ax.legend(
    handles, 
    labels,
    loc='upper center',        
    bbox_to_anchor=(0.5, 1.15),
    ncol=len(protocols),        
    frameon=False               
)

plt.tight_layout()
plt.savefig("figure.pdf")
plt.show()
