import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os
from matplotlib.ticker import ScalarFormatter
import numpy as np
from mpl_toolkits.axes_grid1 import ImageGrid
import numpy as np



plt.rcParams['text.usetex'] = False


if __name__ == "__main__":
    for QMULT in [0.2,1,4]:
        for mode in ['normal']:
            fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(5,2.5), sharex=True)

            COLORMAP = {'cubic':  '#00B945',
                        'cubic': '#FF9500'}
            LEGENDMAP = {}
            BW = 100
            DELAY = 50
            PROTOCOLS = ['cubic', 'cubic']
            RUNS = [1,2,3,4,5]

            LINEWIDTH = 1

            if mode == 'inverse':
                ROOT_PATH = "/home/mihai/mininettestbed/nooffload/results_friendly_intra_rtt_async_inverse/fifo"
            else:
                ROOT_PATH = "/home/mihai/mininettestbed/nooffload/results_fairness_inter_rtt_async/fifo"
            for FLOWS in [2]:
               data = {'cubic':
                          {1: pd.DataFrame([], columns=['time','mean', 'std']),
                           2: pd.DataFrame([], columns=['time','mean', 'std']),
                           3: pd.DataFrame([], columns=['time','mean', 'std']),
                           4: pd.DataFrame([], columns=['time','mean', 'std'])},
                       'bbr':
                          {1: pd.DataFrame([], columns=['time', 'mean', 'std']),
                           2: pd.DataFrame([], columns=['time', 'mean', 'std']),
                           3: pd.DataFrame([], columns=['time', 'mean', 'std']),
                           4: pd.DataFrame([], columns=['time', 'mean', 'std'])},
                       'bbr1':
                          {1: pd.DataFrame([], columns=['time', 'mean', 'std']),
                           2: pd.DataFrame([], columns=['time', 'mean', 'std']),
                           3: pd.DataFrame([], columns=['time', 'mean', 'std']),
                           4: pd.DataFrame([], columns=['time', 'mean', 'std'])}
                       }

               start_time = 0
               end_time = 4*DELAY-2
               # Plot throughput over time
               for protocol in PROTOCOLS:
                  BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
                  BDP_IN_PKTS = BDP_IN_BYTES / 1500
                  senders = {1: [], 2: [], 3: [], 4:[]}
                  receivers = {1: [], 2: [], 3: [], 4:[]}
                  for run in RUNS:
                     PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_%sflows_22tcpbuf_%s/run%s' % (BW,DELAY,int(QMULT * BDP_IN_PKTS),FLOWS,protocol,run)
                     for n in range(FLOWS):

                        if os.path.exists(PATH + '/csvs/c%s.csv' % (n+1)):
                           sender = pd.read_csv(PATH +  '/csvs/c%s.csv' % (n+1))
                           senders[n+1].append(sender)
                        else:
                           print("Folder not found")

                        if os.path.exists(PATH + '/csvs/x%s.csv' % (n+1)):
                           receiver_total = pd.read_csv(PATH + '/csvs/x%s.csv' % (n+1)).reset_index(drop=True)
                           receiver_total = receiver_total[['time', 'bandwidth']]
                           receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))
                           receiver_total['bandwidth'] = receiver_total['bandwidth'].ewm(alpha=0.5).mean()

                           receiver_total = receiver_total[(receiver_total['time'] >= (start_time)) & (receiver_total['time'] <= (end_time))]
                           receiver_total = receiver_total.drop_duplicates('time')
                           receiver_total = receiver_total.set_index('time')
                           receivers[n+1].append(receiver_total)
                        else:
                           print("Folder not found:" + PATH)

                  # For each flow, receivers contains a list of dataframes with a time and bandwidth column. These dataframes SHOULD have
                  # exactly the same index. Now I can concatenate and compute mean and std
                  for n in range(FLOWS):
                      if len(receivers[n+1]) > 0:
                         data[protocol][n+1]['mean'] = pd.concat(receivers[n+1], axis=1).mean(axis=1)
                         data[protocol][n+1]['std'] = pd.concat(receivers[n+1], axis=1).std(axis=1)
                         data[protocol][n+1].index = pd.concat(receivers[n+1], axis=1).index

            for i,protocol in enumerate(PROTOCOLS):
               ax = axes[i]

               for n in range(FLOWS):
                   if mode == 'inverse':
                       LABEL = protocol if n == 0 else 'cubic'
                       COLOR = '#0C5DA5' if n == 1 else COLORMAP[protocol]
                   else:
                       LABEL = protocol 
                       COLOR = '#0C5DA5' if n == 0 else COLORMAP[protocol]

                   ax.plot(data[protocol][n+1].index, data[protocol][n+1]['mean'], linewidth=LINEWIDTH, label=LABEL, color=COLOR)
                   try:
                     if mode == 'inverse':
                         FC = '#0C5DA5' if n == 1 else COLORMAP[protocol]
                     else:
                         FC = '#0C5DA5' if n == 0 else COLORMAP[protocol]
                     ax.fill_between(data[protocol][n+1].index, data[protocol][n+1]['mean'] - data[protocol][n+1]['std'], data[protocol][n+1]['mean'] + data[protocol][n+1]['std'], alpha=0.2,  fc=FC)
                   except:
                     print("Fill between error")


               ax.set(ylim=[0,100])

               ax.grid()

               handles, labels = ax.get_legend_handles_labels()
               for handle, label in zip(handles, labels):
                  if not LEGENDMAP.get(label,None):
                     LEGENDMAP[label] = handle

            fig.text(0.5, 0.01, 'time (s)', ha='center')
            fig.text(0.045, 0.5, 'Goodput (Mbps)', va='center', rotation='vertical')


            fig.legend(list(LEGENDMAP.values()), list(LEGENDMAP.keys()), loc='upper center',ncol=3)

            for format in ['pdf']:
                plt.savefig('goodput_friendly_%sms_%s_%s.%s' % (DELAY, QMULT, mode, format), dpi=720)
