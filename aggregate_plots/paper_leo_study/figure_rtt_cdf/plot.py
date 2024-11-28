import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import json
import os
import matplotlib as mpl
import numpy as np
from matplotlib.pyplot import figure

pd.set_option('display.max_rows', None)
plt.rcParams['text.usetex'] = False

# Color mapping for protocols
COLOR = {'cubic': '#0C5DA5',
         'orca': '#00B945',
         'bbr3': '#FF9500',
         'bbr': '#FF2C01',
         'sage': '#845B97',
         'pcc': '#686868'}

# Parameters
PROTOCOLS = ['cubic', 'orca', 'bbr3', 'bbr', 'sage', 'pcc']
BW = 50  # Bandwidth
DELAY = 50  # Delay
QMULT = 1  # Queue multiplier
RUNS = list(range(1, 51))  # Run numbers
BINS = 50  # Number of bins for CDF

# Function to get goodput data
def get_df(ROOT_PATH, PROTOCOLS, RUNS, BW, DELAY, QMULT):
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    start_time = 0
    end_time = 300
    data = []

    for protocol in PROTOCOLS:
        for run in RUNS:
            PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_1flows_22tcpbuf_%s/run%s' % (
                BW, DELAY, int(QMULT * BDP_IN_PKTS), protocol, run)
            with open(PATH + '/emulation_info.json', 'r') as fin:
                emulation_info = json.load(fin)

            bw_capacities = [x[-1][1] for x in filter(lambda elem: elem[5] == 'tbf', emulation_info['flows'])]
            optimal_mean = sum(bw_capacities) / len(bw_capacities)

            if os.path.exists(PATH + '/csvs/x1.csv'):
                receiver = pd.read_csv(PATH + '/csvs/x1.csv').reset_index(drop=True)
                receiver['time'] = receiver['time'].apply(lambda x: int(float(x)))
                receiver = receiver[(receiver['time'] > start_time) & (receiver['time'] < end_time)]
                receiver = receiver.drop_duplicates('time').set_index('time')
                protocol_mean = receiver.mean()['bandwidth']
                data.append([protocol, run, protocol_mean, optimal_mean])

    COLUMNS = ['protocol', 'run_number', 'average_goodput', 'optimal_goodput']
    return pd.DataFrame(data, columns=COLUMNS)

# Function to get RTT data
def get_rtt_df(ROOT_PATH, PROTOCOLS, RUNS, BW, DELAY, QMULT):
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    start_time = 0
    end_time = 300
    data = []

    for protocol in PROTOCOLS:
        for run in RUNS:
            PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_1flows_22tcpbuf_%s/run%s' % (
                BW, DELAY, int(QMULT * BDP_IN_PKTS), protocol, run)
            with open(PATH + '/emulation_info.json', 'r') as fin:
                emulation_info = json.load(fin)

            rtt_capacities = [x[-1][2] for x in filter(lambda elem: elem[5] == 'netem', emulation_info['flows'])]
            optimal_mean = sum(rtt_capacities) / len(rtt_capacities)
            print(rtt_capacities)
            if os.path.exists(PATH + '/csvs/c1_ss.csv'):
                rtt_data = pd.read_csv(PATH + '/csvs/c1_ss.csv').reset_index(drop=True)
                rtt_data['time'] = rtt_data['time'].apply(lambda x: int(float(x)))
                rtt_data = rtt_data[(rtt_data['time'] > start_time) & (rtt_data['time'] < end_time)]
                rtt_data = rtt_data.drop_duplicates('time').set_index('time')
                mean_rtt = rtt_data.mean()['srtt']  # Assuming 'rtt' is the column name
                data.append([protocol, run, mean_rtt, optimal_mean])

    COLUMNS = ['protocol', 'run_number', 'srtt', 'optimal_srtt']
    return pd.DataFrame(data, columns=COLUMNS)

# Load Goodput Data
bw_rtt_data = get_df("/home/mihai/mininettestbed/nooffload/results_responsiveness_bw_rtt_leo/fifo", PROTOCOLS, RUNS, BW, DELAY, QMULT)
#loss_data = get_df("/home/mihai/mininettestbed/nooffload/results_responsiveness_loss/fifo", PROTOCOLS, RUNS, BW, DELAY, QMULT)

# Load RTT Data
rtt_data_bw_rtt = get_rtt_df("/home/mihai/mininettestbed/nooffload/results_responsiveness_bw_rtt_leo/fifo", PROTOCOLS, RUNS, BW, DELAY, QMULT)
#rtt_data_loss = get_rtt_df("/home/mihai/mininettestbed/nooffload/results_responsiveness_loss/fifo", PROTOCOLS, RUNS, BW, DELAY, QMULT)

# Plotting Goodput CDF
fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(3, 1.5))
ax = axes

# Optimal Goodput
optimals = bw_rtt_data[bw_rtt_data['protocol'] == 'cubic']['optimal_goodput']
values, base = np.histogram(optimals, bins=BINS)
cumulative = np.cumsum(values)
ax.plot(base[:-1], cumulative/50*100, c='black', label="optimal")

# Average Goodput CDF for each protocol
for protocol in PROTOCOLS:
    avg_goodputs = bw_rtt_data[bw_rtt_data['protocol'] == protocol]['average_goodput']
    values, base = np.histogram(avg_goodputs, bins=BINS)
    cumulative = np.cumsum(values)
    ax.plot(base[:-1], cumulative/50*100, label=f"{protocol}-rtt", c=COLOR[protocol])

    # avg_goodputs = loss_data[loss_data['protocol'] == protocol]['average_goodput']
    # values, base = np.histogram(avg_goodputs, bins=BINS)
    # cumulative = np.cumsum(values)
    # ax.plot(base[:-1], cumulative / 50 * 100, label=f"{protocol}-loss", linestyle='dashed', c=COLOR[protocol])

ax.set(xlabel="Average Goodput (Mbps)", ylabel="Percentage of Trials (\%)")
ax.annotate('optimal', xy=(50, 50), xytext=(45, 20), arrowprops=dict(arrowstyle="->", linewidth=0.5))

# Legend
fig.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.50), columnspacing=0.5, handletextpad=0.5, handlelength=1)

# Save Goodput CDF
for format in ['pdf']:
    fig.savefig(f"joined_goodput_cdf.{format}", dpi=720)

# Plotting RTT CDF
fig, ax = plt.subplots(figsize=(3, 1.5))

optimals = rtt_data_bw_rtt[rtt_data_bw_rtt['protocol'] == 'orca']['optimal_srtt']
values, base = np.histogram(optimals, bins=BINS)
cumulative = np.cumsum(values)
ax.plot(base[:-1], cumulative/50*100, c='black', label="optimal")

for protocol in PROTOCOLS:
    rtts = rtt_data_bw_rtt[rtt_data_bw_rtt['protocol'] == protocol]['srtt']
    values, base = np.histogram(rtts, bins=BINS)
    cumulative = np.cumsum(values)
    ax.plot(base[:-1], cumulative / 50 * 100, label=f"{protocol}-rtt", c=COLOR[protocol])

    # rtts = rtt_data_loss[rtt_data_loss['protocol'] == protocol]['rtt']
    # values, base = np.histogram(rtts, bins=BINS)
    # cumulative = np.cumsum(values)
    # ax.plot(base[:-1], cumulative / 50 * 100, label=f"{protocol}-loss", linestyle='dashed', c=COLOR[protocol])

ax.set(xlabel="RTT (ms)", ylabel="Percentage of Trials (\%)")
ax.annotate('optimal', xy=(50, 50), xytext=(45, 20), arrowprops=dict(arrowstyle="->", linewidth=0.5))

# Legend
fig.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.50), columnspacing=0.5, handletextpad=0.5, handlelength=1)

# Save RTT CDF
for format in ['pdf']:
    fig.savefig(f"joined_rtt_cdf.{format}", dpi=720)
