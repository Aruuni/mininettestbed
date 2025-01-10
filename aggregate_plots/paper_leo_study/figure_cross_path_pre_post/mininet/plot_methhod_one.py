import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter
import numpy as np
plt.style.use('science')
import matplotlib as mpl

plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.utils import *

ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/cross_traffic_fairness_inter_rtt"
COLOR = {'cubic': '#0C5DA5', 'orca': '#00B945', 'bbr3': '#FF9500', 'bbr': '#FF2C01', 'sage': '#845B97', 'pcc': '#686868'}

BWS = [100]
DELAYS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
AQM = "fifo"
QMULTS = [0.2, 1, 4]

PROTOCOLS = ['cubic', 'orca', 'bbr', 'sage', 'pcc' , 'bbr3']


FLOWS = 2
RUNS = [1, 2, 3, 4, 5]

pd.set_option('display.max_rows', None)
plt.rcParams['text.usetex'] = False

def calculate_rfair(flow_data, window_size=5):
    n = len(flow_data)

    # Calculate the average throughput of the i-th flow over the last w seconds
    avg_thri = flow_data.rolling(window=window_size).mean().iloc[-1]


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
        ax2.set_ylim(0.5, 1)

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
        ax1.set_xlim(None, None)

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

if __name__ == "__main__":
    for mult in QMULTS:
        data = []     
 
        for bw in BWS:
            for delay in DELAYS:
                for protocol in PROTOCOLS:
                    BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                    BDP_IN_PKTS = BDP_IN_BYTES / 1500

                    fairness_values_cross = []
                    fairness_after = []

                    receivers = {i: [] for i in range(1, FLOWS*2+1)}
                    for run in RUNS:
                        receivers_goodput = {i: pd.DataFrame(columns=['time', 'bandwidth']) for i in range(1, FLOWS*2 + 1)}
                        PATH = f'{ROOT_PATH}/{AQM}/DoubleDumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_{FLOWS}flows_22tcpbuf_{protocol}/run{run}'
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
                        CHANGE1 = 100
                        CHANGE2 = 200

                        goodput_dumbbell1 = combined_goodput[combined_goodput.columns[:FLOWS]]
                        goodput_dumbbell1 = goodput_dumbbell1[(goodput_dumbbell1.index <= CHANGE1) | (goodput_dumbbell1.index > CHANGE2)]  
                        goodput_dumbbell2 = combined_goodput[combined_goodput.columns[-FLOWS:]]
                        goodput_dumbbell2 = goodput_dumbbell2[(goodput_dumbbell2.index <= CHANGE1) | (goodput_dumbbell2.index > CHANGE2)]
                        goodput_both = combined_goodput[(combined_goodput.index > CHANGE1) & (combined_goodput.index <= CHANGE2)]


                        fairness_dumbbell1 = goodput_dumbbell1.apply(lambda row: calculate_jains_index(row.dropna().tolist()), axis=1)
                        fairness_dumbbell2 = goodput_dumbbell2.apply(lambda row: calculate_jains_index(row.dropna().tolist()), axis=1)
                        fairness_both = goodput_both.apply(lambda row: calculate_jains_index(row.dropna().tolist()), axis=1)
                        
                        # Combine the two into a single DataFrame
                        fairness_combined = pd.DataFrame({
                            'fairness_dumbbell1': fairness_dumbbell1,
                            'fairness_dumbbell2': fairness_dumbbell2
                        })

                        # Calculate the average and add it as a new column
                        fairness_combined = fairness_combined.mean(axis=1)
                        #print(fairness_both.loc[(CHANGE1-1):(int)(CHANGE1 + delay)].dropna())
                        #print(fairness_total['fairness_dumbbell2'])
       
                        fairness_values_cross.append(
                            fairness_both.loc[fairness_both.index.intersection(range(CHANGE1 + 1, int(CHANGE1 + (100)) + 1))].dropna()
                        )

                        fairness_after.append(
                            fairness_combined.loc[fairness_combined.index.intersection(range(CHANGE2 + 1, int(CHANGE2 + (100)) + 1))].dropna()
                        )



                    fairness_values_cross = np.concatenate(fairness_values_cross, axis=0)
                    fairness_after = np.concatenate(fairness_after, axis=0)

                    if len(fairness_after) > 0 and len(fairness_values_cross) > 0:
                        data_entry = [protocol, bw, delay, mult, fairness_values_cross.mean(), fairness_values_cross.std(), fairness_after.mean(), fairness_after.std()]
                        data.append(data_entry)
        #print(data)
        summary_data = pd.DataFrame(data,
                              columns=['protocol', 'bandwidth', 'delay', 'qmult', 'fairness_values_cross_mean',
                                       'fairness_values_cross_std', 'fairness_after_mean', 'fairness_after_std'])


        cubic_data = summary_data[summary_data['protocol'] == 'cubic'].set_index('delay')
        orca_data = summary_data[summary_data['protocol'] == 'orca'].set_index('delay')
        bbr_data = summary_data[summary_data['protocol'] == 'bbr'].set_index('delay')
        sage_data = summary_data[summary_data['protocol'] == 'sage'].set_index('delay')
        pcc_data = summary_data[summary_data['protocol'] == 'pcc'].set_index('delay')
        bbr3_data = summary_data[summary_data['protocol'] == 'bbr3'].set_index('delay')

        LINEWIDTH = 1
        ELINEWIDTH = 0.75
        CAPTHICK = ELINEWIDTH
        CAPSIZE= 2

        # -----------------------
        # Plot for the "handover" (cross) scenario
        # -----------------------
        fig_cross, ax_cross = plt.subplots(nrows=1, ncols=1, figsize=(3.7,1.8))

        # Plot "cross" data
        markers, caps, bars = ax_cross.errorbar(cubic_data.index*2, cubic_data['fairness_values_cross_mean'], 
                                                yerr=cubic_data['fairness_values_cross_std'],
                                                marker='x', linewidth=LINEWIDTH, elinewidth=ELINEWIDTH,
                                                capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['cubic'], 
                                                label='cubic-handover')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_cross.errorbar(orca_data.index*2, orca_data['fairness_values_cross_mean'],
                                                yerr=orca_data['fairness_values_cross_std'],
                                                marker='+', linewidth=LINEWIDTH, elinewidth=ELINEWIDTH,
                                                capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['orca'], 
                                                label='orca-handover')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_cross.errorbar(bbr_data.index*2, bbr_data['fairness_values_cross_mean'], 
                                                yerr=bbr_data['fairness_values_cross_std'],
                                                marker='.', linewidth=LINEWIDTH, elinewidth=ELINEWIDTH,
                                                capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['bbr'], 
                                                label='bbrv1-handover')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_cross.errorbar(sage_data.index*2, sage_data['fairness_values_cross_mean'], 
                                                yerr=sage_data['fairness_values_cross_std'],
                                                marker='*', linewidth=LINEWIDTH, elinewidth=ELINEWIDTH,
                                                capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['sage'], 
                                                label='sage-handover')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_cross.errorbar(pcc_data.index*2, pcc_data['fairness_values_cross_mean'], 
                                                yerr=pcc_data['fairness_values_cross_std'],
                                                marker='_', linewidth=LINEWIDTH, elinewidth=ELINEWIDTH,
                                                capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['pcc'], 
                                                label='vivace-handover')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]
        
        markers, caps, bars = ax_cross.errorbar(bbr3_data.index*2, bbr3_data['fairness_values_cross_mean'], 
                                                yerr=bbr3_data['fairness_values_cross_std'],
                                                marker='^', linewidth=LINEWIDTH, elinewidth=ELINEWIDTH,
                                                capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['bbr3'], 
                                                label='bbrv3-handover')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        ax_cross.set(yscale='linear', xlabel='RTT (ms)', ylabel="Jain's Fairness Index", ylim=[0.4,1.05])
        for axis in [ax_cross.xaxis, ax_cross.yaxis]:
            axis.set_major_formatter(ScalarFormatter())

        handles, labels = ax_cross.get_legend_handles_labels()
        handles = [h[0] for h in handles]

        fig_cross.legend(handles, labels, ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.28), columnspacing=0.8, handletextpad=0.9)
        
        for format in ['pdf']:
            plt.savefig(f'jainsindex_cross_inter_rtt_{mult}_50ms_fixed.{format}', dpi=1080)
        plt.close(fig_cross)

        # -----------------------
        # Plot for the "return" scenario
        # -----------------------
        fig_return, ax_return = plt.subplots(nrows=1, ncols=1, figsize=(3.7,1.8))

        # Plot "after" data (return)
        markers, caps, bars = ax_return.errorbar(cubic_data.index*2, cubic_data['fairness_after_mean'], 
                                                 yerr=cubic_data['fairness_after_std'],
                                                 marker='x', linewidth=LINEWIDTH, linestyle="--", elinewidth=ELINEWIDTH,
                                                 capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['cubic'], 
                                                 label='cubic-return')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_return.errorbar(orca_data.index*2, orca_data['fairness_after_mean'],
                                                 yerr=orca_data['fairness_after_std'],
                                                 marker='+', linewidth=LINEWIDTH, linestyle="--", elinewidth=ELINEWIDTH,
                                                 capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['orca'], 
                                                 label='orca-return')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_return.errorbar(bbr_data.index*2, bbr_data['fairness_after_mean'], 
                                                 yerr=bbr_data['fairness_after_std'],
                                                 marker='.', linewidth=LINEWIDTH, linestyle="--", elinewidth=ELINEWIDTH,
                                                 capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['bbr'], 
                                                 label='bbrv1-return')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_return.errorbar(sage_data.index*2, sage_data['fairness_after_mean'], 
                                                 yerr=sage_data['fairness_after_std'],
                                                 marker='*', linewidth=LINEWIDTH, linestyle="--", elinewidth=ELINEWIDTH,
                                                 capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['sage'], 
                                                 label='sage-return')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_return.errorbar(pcc_data.index*2, pcc_data['fairness_after_mean'], 
                                                 yerr=pcc_data['fairness_after_std'],
                                                 marker='_', linewidth=LINEWIDTH, linestyle="--", elinewidth=ELINEWIDTH,
                                                 capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['pcc'], 
                                                 label='vivace-return')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

        markers, caps, bars = ax_return.errorbar(bbr3_data.index*2, bbr3_data['fairness_after_mean'], 
                                                yerr=bbr3_data['fairness_after_std'],
                                                marker='^', linewidth=LINEWIDTH, linestyle="--", elinewidth=ELINEWIDTH,
                                                capsize=CAPSIZE, capthick=CAPTHICK, color=COLOR['bbr3'], 
                                                label='bbrv3-return')
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]
        ax_return.set(yscale='linear', xlabel='RTT (ms)', ylabel="Jain's Fairness Index", ylim=[0.4,1.05])
        for axis in [ax_return.xaxis, ax_return.yaxis]:
            axis.set_major_formatter(ScalarFormatter())

        handles, labels = ax_return.get_legend_handles_labels()
        handles = [h[0] for h in handles]

        fig_return.legend(handles, labels, ncol=3, loc='upper center', bbox_to_anchor=(0.5, 1.28), columnspacing=0.8, handletextpad=0.9)
        
        for format in ['pdf']:
            plt.savefig(f'jainsindex_return_inter_rtt_{mult}_50ms_fixed.{format}', dpi=1080)
        plt.close(fig_return)

