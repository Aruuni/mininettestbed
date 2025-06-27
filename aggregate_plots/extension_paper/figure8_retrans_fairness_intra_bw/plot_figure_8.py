import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter
import numpy as np
plt.rcParams['text.usetex'] = False
import matplotlib.ticker as mticker
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 
from matplotlib.ticker import LogLocator, NullFormatter, LogFormatterSciNotation, FormatStrFormatter, FuncFormatter

EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_bw_async/fifo" 
BWS = [10,20,30,40,50,60,70,80,90,100]
DELAYS = [20]


for mult in QMULTS:
   data = []
   for protocol in PROTOCOLS_EXTENSION:
     for bw in BWS:
        for delay in DELAYS:
           BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
           BDP_IN_PKTS = BDP_IN_BYTES / 1500

           retr_total = []
           for run in RUNS:
              PATH = f"{EXPERIMENT_PATH}/Dumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{run}" 
              if protocol != 'vivace-uspace':
                 if os.path.exists(f"{PATH}/sysstat/etcp_c1.log"):
                    systat1 = pd.read_csv(f"{PATH}/sysstat/etcp_c1.log", sep=';').rename(
                       columns={"# hostname": "hostname"})
                    retr1 = systat1[['timestamp', 'retrans/s']]
                    systat2 = pd.read_csv(f"{PATH}/sysstat/etcp_c2.log", sep=';').rename(
                       columns={"# hostname": "hostname"})
                    retr2 = systat2[['timestamp', 'retrans/s']]
                    if retr1['timestamp'].iloc[0] <= retr2['timestamp'].iloc[0]:
                       start_timestamp = retr1['timestamp'].iloc[0]
                    else:
                       start_timestamp = retr2['timestamp'].iloc[0]

                    retr1.loc[:, 'timestamp'] = retr1['timestamp'] - start_timestamp + 1
                    retr2.loc[:, 'timestamp'] = retr2['timestamp'] - start_timestamp + 1

                    retr1 = retr1.rename(columns={'timestamp': 'time'})
                    retr2 = retr2.rename(columns={'timestamp': 'time'})
                    valid = True

                 else:
                    valid=False
              else:
                 if os.path.exists(f"{PATH}/csvs/c1.csv"):
                    systat1 = pd.read_csv(f"{PATH}/csvs/c1.csv").rename(
                       columns={"retr": "retrans/s"}) 
                    retr1 = systat1[['time', 'retrans/s']]
                    systat2 = pd.read_csv(f"{PATH}/csvs/c1.csv").rename(
                       columns={"retr": "retrans/s"})
                    retr2 = systat2[['time', 'retrans/s']]
                    valid = True
                 else:
                    valid = False

              if valid:
                 retr1['time'] = retr1['time'].apply(lambda x: int(float(x)))
                 retr2['time'] = retr2['time'].apply(lambda x: int(float(x)))

                 retr1 = retr1.drop_duplicates('time')
                 retr2 = retr2.drop_duplicates('time')

                 retr1_total = retr1[(retr1['time'] > 0) & (retr1['time'] < 100)]
                 retr2_total = retr2[(retr2['time'] > 0) & (retr2['time'] < 100)]

                 retr1_total = retr1_total.set_index('time')
                 retr2_total = retr2_total.set_index('time')

                 total = retr1_total.join(retr2_total, how='inner', lsuffix='1', rsuffix='2')[['retrans/s1', 'retrans/s2']]
                 retr_total.append(total.sum(axis=1))
           if len(retr_total) > 0:
            retr_total = np.concatenate(retr_total, axis=0)


           if len(retr_total) > 0:
              data_entry = [protocol, bw, delay, delay/10, mult, retr_total.mean(), retr_total.std()]
              data.append(data_entry)

   summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult', 'retr_total_mean', 'retr_total_std'])
   print(summary_data)
   SCALE = 'linear'
   LOC = 4 if SCALE == 'log' else 2

   fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(3,1.2))
   ax = axes
   
   for axis in [ax.xaxis, ax.yaxis]:
       axis.set_major_formatter(ScalarFormatter())
   for protocol in PROTOCOLS_EXTENSION:
      plot_retrans_points(ax, summary_data[summary_data['protocol'] == protocol].set_index('bandwidth'), 'retr_total_mean', 'retr_total_mean', PROTOCOLS_MARKERS_EXTENSION[protocol], COLORS_EXTENSION[protocol], PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol])


   ax.set(xlabel='Bandwidth (Mbps)', ylabel='Retr. (Mbps)', yscale=SCALE)
   for axis in [ax.xaxis, ax.yaxis]:
       axis.set_major_formatter(ScalarFormatter())

   handles, labels = ax.get_legend_handles_labels()
   # remove the errorbars
   handles = [h[0] for h in handles]

   # legend = fig.legend(
   #    handles, labels,
   #    ncol=3, loc='upper center',
   #    bbox_to_anchor=(0.5, 1.30),
   #    columnspacing=0.8,
   #    handletextpad=0.5
   # )
   # ax.grid()

   plt.savefig(f"retr_async_bw_{SCALE}_{mult}.pdf", dpi=720)