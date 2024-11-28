import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scienceplots
from matplotlib.ticker import FormatStrFormatter

plt.style.use('science')
import matplotlib as mpl

ROOT_PATH = "/home/mihai/mininettestbed/nooffload/fairness_cross_traffic"

BW = 100
DELAY = 20
AQM = "fifo"
QMULT = 1

PROTOCOLS = ['cubic', 'orca', 'bbr', 'sage', 'pcc', 'bbr3']
COLOR = {'cubic': '#0C5DA5', 'orca': '#00B945', 'bbr3': '#FF9500', 'bbr': '#FF2C01', 'sage': '#845B97', 'pcc': '#686868'}

FLOWS = 3
RUNS = [1, 2, 3, 4, 5]


pd.set_option('display.max_rows', None)
plt.rcParams['text.usetex'] = False

def calculate_rfair(flow_data, window_size=5):
    n = len(flow_data)
    print(n)
    # Calculate the average throughput of the i-th flow over the last w seconds
    avg_thri = flow_data.rolling(window=window_size).mean().iloc[-1]

    print (flow_data.rolling(window=window_size).mean().iloc[-1])
    # Calculate numerator and denominator for R-FAIR
    numerator = np.sqrt(np.sum((flow_data - avg_thri) ** 2))
    denominator = len(flow_data) * np.sqrt(np.sum(flow_data ** 2))
    
    # Calculate R-FAIR
    rfair = numerator / denominator
    
    return 1 - rfair





import matplotlib.pyplot as plt

def plot_fairness_and_goodput(fairness_data, goodput_data):
    for protocol in PROTOCOLS:
        fig, (ax2, ax1) = plt.subplots(2, 1, figsize=(15, 8), gridspec_kw={'height_ratios': [1, 2]}, sharex=True)

        # Plot fairness for all flows in the first subplot (top)
        fairness_mean_dumbbell1 = fairness_data[protocol]['fairness_dumbbell1_mean']
        fairness_mean_dumbbell2 = fairness_data[protocol]['fairness_dumbbell2_mean']
        fairness_mean_all = fairness_data[protocol]['fairness_all_mean']
        time = fairness_data[protocol]['time']

        ax2.plot(time, fairness_mean_dumbbell1, label='Fairness Dumbbell 1', color='orange')
        ax2.plot(time, fairness_mean_dumbbell2, label='Fairness Dumbbell 2', color='green')
        ax2.plot(time, fairness_mean_all, label='Fairness All', color='red')

        # Configure the fairness plot without title
        ax2.set_ylabel('Fairness Index', fontsize=25)
        ax2.tick_params(axis='both', which='major', labelsize=20)
        ax2.legend(fontsize=14, loc='lower right')
        ax2.grid()
        ax2.set_xlim(0, 100)
        ax2.set_ylim(0, 1)

        for flow in range(1, len(goodput_data[protocol]) + 1):
            goodput_mean = goodput_data[protocol][flow]['mean']
            goodput_std = goodput_data[protocol][flow]['std']
            time_index = goodput_mean.index

            ax1.plot(time_index, goodput_mean, label=f'Goodput Flow {flow}')
            ax1.fill_between(time_index, 
                             goodput_mean - goodput_std, 
                             goodput_mean + goodput_std, 
                             alpha=0.2)  # Shade for std deviation

        # Configure the goodput plot without title
        ax1.set_xlabel('Time (s)', fontsize=25)
        ax1.set_ylabel('Goodput (Mbps)', fontsize=25)
        ax1.tick_params(axis='both', which='major', labelsize=20)
        ax1.legend(fontsize=14, loc='lower right')
        ax1.grid()
        ax1.set_xlim(0, 100)

        # Remove padding between the subplots to make them appear closer together
        plt.subplots_adjust(hspace=0.05)
        ax2.get_xaxis().set_visible(True)  # Hide x-axis labels of the top plot

        # Tight layout with no extra padding
        plt.tight_layout(pad=0.5)
        plt.savefig(f'fairness_goodput_{protocol}.pdf', bbox_inches='tight')
        plt.close()


def calculate_jains_index(bandwidths):
    """Calculate Jain's Fairness Index for a given set of bandwidth values."""
    n = len(bandwidths)
    sum_bw = sum(bandwidths)
    sum_bw_sq = sum(bw ** 2 for bw in bandwidths)
    return (sum_bw ** 2) / (n * sum_bw_sq) if sum_bw_sq != 0 else 0

def get_fairness_data():
    goodput_data = {
        protocol: {i: pd.DataFrame([], columns=['mean', 'std']) for i in range(1, FLOWS*2+1)}
        for protocol in PROTOCOLS
    }
    fairness_data = {protocol: pd.DataFrame(columns=['time', 'fairness_dumbbbell1_mean', 'fairness_dumbbbell2_mean', 'fairness_all_mean']) for protocol in PROTOCOLS}
    for protocol in PROTOCOLS:
        BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
        BDP_IN_PKTS = BDP_IN_BYTES / 1500
        fairness_per_run = {i: pd.DataFrame(columns=['time', 'fairness_dumbbbell1', 'fairness_dumbbbell2', 'fairness_all']) for i in RUNS}
        receivers = {i: [] for i in range(1, FLOWS*2+1)}
        for run in RUNS:
            receivers_goodput = {i: pd.DataFrame(columns=['time', 'bandwidth']) for i in range(1, FLOWS*2 + 1)}
            PATH = f'{ROOT_PATH}/{AQM}/DoubleDumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_{FLOWS}flows_22tcpbuf_{protocol}/run{run}'

            for dumbbell in range(1, 3):
                for flow in range(1, FLOWS + 1):
                    flow_path = f'{PATH}/csvs/x{dumbbell}_{flow}.csv'
                    if os.path.exists(flow_path):
                        receiver_total = pd.read_csv(flow_path)[['time', 'bandwidth']]
                        receiver_total['time'] = receiver_total['time'].astype(float).astype(int)
                        receiver_total = receiver_total.drop_duplicates('time').set_index('time')
                        receivers_goodput[flow + (FLOWS * (dumbbell - 1))] = receiver_total
                        receivers[flow + (FLOWS * (dumbbell - 1))].append(receiver_total)
                #print(receivers)
            combined_goodput = pd.concat([receivers_goodput[i] for i in range(1, FLOWS*2 + 1)], axis=1)
            combined_goodput.columns = [f'bandwidth_{i}' for i in range(1, FLOWS*2 + 1)]

            goodput_dumbbell1 = combined_goodput[combined_goodput.columns[:FLOWS]]
            goodput_dumbbell1 = goodput_dumbbell1[(goodput_dumbbell1.index <= DELAY) | (goodput_dumbbell1.index > DELAY * 3)]  
            goodput_dumbbell2 = combined_goodput[combined_goodput.columns[-FLOWS:]]
            goodput_dumbbell2 = goodput_dumbbell2[(goodput_dumbbell2.index <= DELAY) | (goodput_dumbbell2.index > DELAY * 3)]
            goodput_both = combined_goodput[(combined_goodput.index > DELAY) & (combined_goodput.index <= DELAY * 3)]


            fairness_dumbbell1 = goodput_dumbbell1.apply(lambda row: calculate_jains_index(row.dropna().tolist()), axis=1)
            fairness_dumbbell2 = goodput_dumbbell2.apply(lambda row: calculate_jains_index(row.dropna().tolist()), axis=1)
            fairness_both = goodput_both.apply(lambda row: calculate_jains_index(row.dropna().tolist()), axis=1)
            fairness_total = pd.concat([fairness_dumbbell1, fairness_dumbbell2, fairness_both],axis=1)
            fairness_total.columns =['fairness_dumbbell1', 'fairness_dumbbell2', 'fairness_all']
            fairness_per_run[run] = fairness_total

        for flow in range(1,FLOWS*2+1):
           goodput_data[protocol][flow]['mean'] = pd.concat(receivers[flow], axis=1).mean(axis=1)
           goodput_data[protocol][flow]['std'] = pd.concat(receivers[flow], axis=1).std(axis=1)
           goodput_data[protocol][flow].index = pd.concat(receivers[flow], axis=1).index
        
        all_runs_concat = pd.concat(fairness_per_run.values(), axis=1, keys=RUNS)
        fairness_data[protocol] = pd.DataFrame({
            'time': all_runs_concat.index,
            'fairness_dumbbell1_mean': all_runs_concat.xs('fairness_dumbbell1', axis=1, level=1).mean(axis=1),
            'fairness_dumbbell2_mean': all_runs_concat.xs('fairness_dumbbell2', axis=1, level=1).mean(axis=1),
            'fairness_all_mean': all_runs_concat.xs('fairness_all', axis=1, level=1).mean(axis=1)
        }).sort_index()
    return fairness_data, goodput_data


if __name__ == "__main__":
    fairness_data, goodput_data = get_fairness_data()
    plot_fairness_and_goodput(fairness_data, goodput_data)
    #print(goodput_data['cubic'])
    # Calculate Jain's Fairness Index for different time segments
