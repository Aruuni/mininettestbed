import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import scienceplots
plt.style.use('science')
import matplotlib.transforms as transforms
from matplotlib.patches import Ellipse

plt.rcParams['text.usetex'] = False

# Assuming these come from your own modules:
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)
from core.config import *
from core.plotting import * 

# Experiment parameters
ROOT_PATH = "/home/mihai/mininettestbed/nooffload/results_parking_lot/fifo" 
PROTOCOLS = ['cubic', 'bbr1', 'bbr3', 'sage', 'astraea']  # note: no "orca"
BWS = [100]
DELAYS = [10]
QMULTS = [0.2, 1, 4]
RUNS = [1, 2, 3, 4, 5]
FLOWS = 4

# --- A helper to draw a confidence ellipse (taken from your second code snippet) ---
def confidence_ellipse(x, y, ax, n_std=1.0, facecolor='none', **kwargs):
    """
    Draw a confidence ellipse based on the covariance of x and y.
    """
    if x.size != y.size:
        raise ValueError("x and y must be the same size")
    cov = np.cov(x, y)
    pearson = cov[0, 1] / np.sqrt(cov[0,0] * cov[1,1])
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0),
                      width=ell_radius_x * 2,
                      height=ell_radius_y * 2,
                      facecolor=facecolor, **kwargs)
    scale_x = np.sqrt(cov[0,0]) * n_std
    mean_x = np.mean(x)
    scale_y = np.sqrt(cov[1,1]) * n_std
    mean_y = np.mean(y)
    transf = transforms.Affine2D().rotate_deg(45).scale(scale_x, scale_y).translate(mean_x, mean_y)
    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)

# --- Data collection ---
data = []  # will hold one row per combination of protocol, delay, qmult, etc.

for mult in QMULTS:
    for protocol in PROTOCOLS:
        for bw in BWS:
            for delay in DELAYS:
                # Use the same definitions as before:
                start_time = 2 * delay
                BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * 1e-3 / 8)
                BDP_IN_PKTS = BDP_IN_BYTES / 1500

                # We will collect three arrays per setting:
                # (a) goodput ratios (per run, many time samples),
                # (b) normalized throughput (averaged per run),
                # (c) normalized retransmissions (averaged per run)
                goodput_ratios_total = []
                norm_throughput_list = []
                norm_retrans_list_all = []
                
                for run in RUNS:
                    # Build path based on your folder structure:
                    PATH = ROOT_PATH + '/ParkingLot_%smbit_%sms_%spkts_0loss_%sflows_22tcpbuf_%s/run%s' % (
                        bw, delay, int(mult * BDP_IN_PKTS), FLOWS, protocol, run)
                    
                    # Process the receiver files as before:
                    receiver_file_spine = f'{PATH}/csvs/x1.csv'
                    receiver_files_ribs = [f'{PATH}/csvs/x{i}.csv' for i in range(2, FLOWS + 1)]
                    if all(os.path.exists(f) for f in receiver_files_ribs) and os.path.exists(receiver_file_spine):
                        # Load spine and rib CSVs:
                        receivers_ribs_unprocessed = [pd.read_csv(f).reset_index(drop=True) for f in receiver_files_ribs]
                        receiver_spine = pd.read_csv(receiver_file_spine).reset_index(drop=True)
                        
                        receiver_spine['time'] = receiver_spine['time'].apply(lambda x: int(float(x)))
                        receiver_spine = receiver_spine[receiver_spine['time'] >= start_time].drop_duplicates('time').set_index('time')
                        
                        receivers_ribs = []
                        for rib in receivers_ribs_unprocessed:
                            rib['time'] = rib['time'].apply(lambda x: int(float(x)))
                            rib = rib[rib['time'] >= start_time].drop_duplicates('time').set_index('time')
                            receivers_ribs.append(rib)
                        
                        # For each time sample, take the maximum among the ribs:
                        combined_ribs = pd.concat([rib['bandwidth'] for rib in receivers_ribs],
                                                  axis=1, keys=[f'Rib{i+1}' for i in range(len(receivers_ribs))])
                        max_bandwidth_between_ribs = combined_ribs.max(axis=1).reset_index()
                        max_bandwidth_between_ribs.columns = ['time', 'bandwidth']
                        max_bandwidth_between_ribs.set_index('time', inplace=True)
                        
                        # Join spine and max ribs
                        total = receiver_spine[['bandwidth']].join(max_bandwidth_between_ribs, how='inner',
                                                                    lsuffix='1', rsuffix='2')
                        # Compute goodput ratio (per time sample) and save all values
                        run_goodput_ratio = total.min(axis=1) / total.max(axis=1)
                        goodput_ratios_total.append(run_goodput_ratio.values)
                    else:
                        print("Folder %s not found." % PATH)
                    
                    # --- Normalized throughput from dev_root.log ---
                    dev_root_file = f"{PATH}/sysstat/dev_root.log"
                    if os.path.exists(dev_root_file):
                        systat = pd.read_csv(dev_root_file, sep=';').rename(columns={"# hostname": "hostname"})
                        util = systat[['timestamp', 'IFACE', 'txkB/s', '%ifutil']]
                        start_ts = util['timestamp'].iloc[0]
                        util['timestamp'] = util['timestamp'] - start_ts + 1
                        util = util.rename(columns={'timestamp': 'time'})
                        util['time'] = util['time'].apply(lambda x: int(float(x)))
                        # Use a fixed window (here: [start_time, start_time+100])
                        end_time = start_time + 100
                        util = util[(util['time'] >= start_time) & (util['time'] < end_time)]
                        util_if = util[util['IFACE'] == "s2-eth2"]
                        if not util_if.empty:
                            # Compute throughput in Mbps (txkB/s *8/1024) then normalize by bw
                            util_mean = util_if['txkB/s'].mean() * 8 / 1024
                            norm_throughput_list.append(util_mean / bw)
                    
                    # --- Normalized retransmissions ---
                    norm_retrans_run_list = []
                    for n in range(1, FLOWS+1):
                        retr_file = f"{PATH}/sysstat/etcp_c{n}.log"
                        if os.path.exists(retr_file):
                            systat = pd.read_csv(retr_file, sep=';').rename(columns={"# hostname": "hostname"})
                            retr = systat[['timestamp', 'retrans/s']]
                            start_ts = retr['timestamp'].iloc[0]
                            retr['timestamp'] = retr['timestamp'] - start_ts + 1
                            retr = retr.rename(columns={'timestamp': 'time'})
                            retr['time'] = retr['time'].apply(lambda x: int(float(x)))
                            end_time = start_time + 100
                            retr = retr[(retr['time'] >= start_time) & (retr['time'] < end_time)].drop_duplicates('time')
                            if not retr.empty:
                                # Convert to Mbps (using a packet size of 1500 bytes) and normalize
                                retr_mean = retr['retrans/s'].mean() * 1500 * 8 / (1024*1024)
                                norm_retrans_run_list.append(retr_mean / bw)
                    if norm_retrans_run_list:
                        norm_retrans_list_all.append(np.mean(norm_retrans_run_list))
                
                # Combine the per-run arrays:
                if goodput_ratios_total:
                    all_goodput = np.concatenate(goodput_ratios_total)
                    mean_goodput = np.mean(all_goodput)
                    std_goodput = np.std(all_goodput)
                else:
                    mean_goodput = np.nan
                    std_goodput = np.nan
                if norm_throughput_list:
                    mean_norm_throughput = np.mean(norm_throughput_list)
                    std_norm_throughput = np.std(norm_throughput_list)
                else:
                    mean_norm_throughput = np.nan
                    std_norm_throughput = np.nan
                if norm_retrans_list_all:
                    mean_norm_retrans = np.mean(norm_retrans_list_all)
                    std_norm_retrans = np.std(norm_retrans_list_all)
                else:
                    mean_norm_retrans = np.nan
                    std_norm_retrans = np.nan
                
                # Save one data row for this (protocol, bw, delay, qmult) combination.
                data_entry = [protocol, bw, delay, delay/10, mult,
                              mean_goodput, std_goodput,
                              mean_norm_throughput, std_norm_throughput,
                              mean_norm_retrans, std_norm_retrans]
                data.append(data_entry)

# Build the summary DataFrame (note the new columns for normalized throughput and retransmissions)
summary_data = pd.DataFrame(data, columns=[
    'protocol', 'bandwidth', 'delay', 'delay_ratio', 'qmult',
    'goodput_ratio_mean', 'goodput_ratio_std',
    'norm_throughput_mean', 'norm_throughput_std',
    'norm_retrans_mean', 'norm_retrans_std'
])

# Omit protocol "orca" (if any were present)
summary_data = summary_data[summary_data['protocol'] != 'orca']

# --- Plotting ---
# We now plot a scatter where:
#   • x-axis = goodput_ratio_mean (with its error)
#   • y-axis = normalized throughput
# Also, we show a second (lighter) marker at (goodput_ratio_mean, norm_throughput_mean - norm_retrans_mean)
# and connect the two with a vertical line.
CAPSIZE = 2
colors = {
    'cubic': '#0C5DA5',
    'bbr1': '#FF2C01',
    'bbr3': '#FF9500',
    'sage': '#FF2C01',
    'astraea': '#686868'
}
markers = {
    'cubic': 'x',
    'bbr1': 'o',
    'bbr3': '^',
    'sage': '*',
    'astraea': 's'
}

fig, ax = plt.subplots(figsize=(3, 1.5))

for protocol in summary_data['protocol'].unique():
    dfp = summary_data[summary_data['protocol'] == protocol]
    # Plot the main (normalized throughput) points with error bars.
    ax.errorbar(dfp['goodput_ratio_mean'], dfp['norm_throughput_mean'],
                xerr=dfp['goodput_ratio_std'], yerr=dfp['norm_throughput_std'],
                fmt=markers[protocol], color=colors[protocol],
                label=protocol, capsize=CAPSIZE, markersize=5)
    # Plot the "penalized" points (throughput minus retransmissions)
    ax.errorbar(dfp['goodput_ratio_mean'], dfp['norm_throughput_mean'] - dfp['norm_retrans_mean'],
                xerr=dfp['goodput_ratio_std'], yerr=dfp['norm_retrans_std'],
                fmt=markers[protocol], color=colors[protocol],
                mfc='none', alpha=0.5, capsize=CAPSIZE, markersize=5)
    # Connect the two with a vertical line for each row:
    for idx, row in dfp.iterrows():
        ax.plot([row['goodput_ratio_mean'], row['goodput_ratio_mean']],
                [row['norm_throughput_mean'], row['norm_throughput_mean'] - row['norm_retrans_mean']],
                color=colors[protocol], alpha=0.5)
    # If you have more than one point per protocol, add a confidence ellipse (using the lower values)
    x_vals = dfp['goodput_ratio_mean'].values
    y_vals = (dfp['norm_throughput_mean'] - dfp['norm_retrans_mean']).values
    if len(x_vals) > 1:
        confidence_ellipse(x_vals, y_vals, ax, n_std=1.0,
                           facecolor=colors[protocol], edgecolor='none', alpha=0.25)

ax.set_xlabel("Goodput Ratio")
ax.set_ylabel("Normalized Throughput")
ax.set_xlim([-0.1, 1.1])
ax.set_ylim([0, 1.1])
ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.28),
          columnspacing=0.8, handletextpad=0.9)

plt.savefig('final_plot.pdf', dpi=1080)
