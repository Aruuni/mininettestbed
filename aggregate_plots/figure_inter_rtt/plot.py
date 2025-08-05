import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter, LogLocator, LogFormatter, FuncFormatter
import numpy as np
plt.rcParams['text.usetex'] = True
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 

EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_inter_rtt/sfq" 

BWS = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

for mult in [0.2, 1, 4 ]:
    data = []
    for protocol in PROTOCOLS_LEO:
      for bw in BWS:
          for delay in DELAYS:
              start_time = 3*delay
              end_time = 4*delay-1
              keep_last_seconds = int(0.25*delay)

              BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
              BDP_IN_PKTS = BDP_IN_BYTES / 1500

              goodput_ratios_total = []
              for run in RUNS:
                  PATH = f"{EXPERIMENT_PATH}/Dumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{run}" 
                  if os.path.exists(f"{PATH}/csvs/x1.csv") and os.path.exists(f"{PATH}/csvs/x2.csv"):
                      receiver1_total = pd.read_csv(f"{PATH}/csvs/x1.csv").reset_index(drop=True)
                      receiver2_total = pd.read_csv(f"{PATH}/csvs/x2.csv").reset_index(drop=True)

                      receiver1_total['time'] = receiver1_total['time'].apply(lambda x: int(float(x)))
                      receiver2_total['time'] = receiver2_total['time'].apply(lambda x: int(float(x)))


                      receiver1_total = receiver1_total[(receiver1_total['time'] > start_time) & (receiver1_total['time'] < end_time)]
                      receiver2_total = receiver2_total[(receiver2_total['time'] > start_time) & (receiver2_total['time'] < end_time)]

                      receiver1_total = receiver1_total.drop_duplicates('time')
                      receiver2_total = receiver2_total.drop_duplicates('time')
                      receiver1 = receiver1_total[receiver1_total['time'] >= end_time - keep_last_seconds].reset_index(drop=True)
                      receiver2 = receiver2_total[receiver2_total['time'] >= end_time - keep_last_seconds].reset_index(drop=True)

                      receiver1_total = receiver1_total.set_index('time')
                      receiver2_total = receiver2_total.set_index('time')

                      total = receiver1_total.join(receiver2_total, how='inner', lsuffix='1', rsuffix='2')[['bandwidth1', 'bandwidth2']]
                      total = total[(total['bandwidth1'] > 0) | (total['bandwidth2'] > 0)] # if one datapoint contains a nan from the divide by 0, the enire datapoint will not be plotted.
                      
                      goodput_ratios_total.append(total.min(axis=1)/total.max(axis=1))
                      #goodput_ratios_total.append(total['bandwidth1']/total['bandwidth2'])
                  else:
                      print(f"Folder {PATH} not found.")

              if  len(goodput_ratios_total) > 0:
                  goodput_ratios_total = np.concatenate(goodput_ratios_total, axis=0)

                  if len(goodput_ratios_total) > 0:
                      data_entry = [protocol, bw, delay, delay/10, mult, goodput_ratios_total.mean(), goodput_ratios_total.std()]
                      data.append(data_entry)

    summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult','goodput_ratio_total_mean', 'goodput_ratio_total_std'])
    fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.1))
    ax = axes
    for protocol in PROTOCOLS_LEO:
        plot_points(ax, summary_data[summary_data['protocol'] == protocol].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std', PROTOCOLS_MARKERS_LEO[protocol], COLORS_LEO[protocol], PROTOCOLS_FRIENDLY_NAME_LEO[protocol], delay=True)

    ax.set(yscale='linear',xlabel='RTT (ms)', ylabel='Goodput Ratio', ylim=[-0.1, 1.1])
    # x-axis remains linear; use ScalarFormatter to keep “100”, “200”, … style
    ax.xaxis.set_major_formatter(ScalarFormatter())


    handles, labels = ax.get_legend_handles_labels()
    handles = [h[0] for h in handles]
    # leg1 = fig.legend(
    #     handles[:3], labels[:3],
    #     ncol=3,
    #     loc='upper center',
    #     bbox_to_anchor=(0.5, 1.15),
    #     frameon=False,
    #     fontsize=7,
    #     columnspacing=0.8,
    #     handlelength=2.5,
    #     handletextpad=0.5
    # )
    # fig.add_artist(leg1)

    # leg2 = fig.legend(
    #     handles[3:], labels[3:],
    #     ncol=2,
    #     loc='upper center',
    #     bbox_to_anchor=(0.5, 1.05),
    #     frameon=False,
    #     fontsize=7,
    #     columnspacing=0.8,
    #     handlelength=2.5,
    #     handletextpad=0.5
    # )
    plt.savefig(f"goodput_inter_rtt_qmult{mult}.pdf", dpi=1080)