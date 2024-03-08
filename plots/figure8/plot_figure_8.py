import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os
from matplotlib.ticker import ScalarFormatter
import numpy as np

plt.rcParams['text.usetex'] = False


ROOT_PATH =  "/home/mihai/mininettestbed/nooffload/results_fairness_bw_async/fifo" 
PROTOCOLS = ['cubic', 'bbr', 'bbr1'] # aur is bbr1
BWS = [10,20,30,40,50,60,70,80,90,100]
DELAYS = [20]
QMULTS = [0.2,1,4]
RUNS = [1, 2, 3, 4, 5]
LOSSES=[0]

for mult in QMULTS:
   data = []
   for protocol in PROTOCOLS:
     for bw in BWS:
        for delay in DELAYS:

           BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
           BDP_IN_PKTS = BDP_IN_BYTES / 1500

           retr_total = []

           for run in RUNS:
              PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_2flows_22tcpbuf_%s/run%s' % (bw,delay,int(mult * BDP_IN_PKTS),protocol,run)

              if os.path.exists(PATH + '/csvs/c1.csv'):
                  systat1 = pd.read_csv(PATH + '/csvs/c1.csv').rename(
                     columns={"retr": "retrans/s"})
                  retr1 = systat1[['time', 'retrans/s']]
                  systat2 = pd.read_csv(PATH + '/csvs/c1.csv').rename(
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


                 total = retr1_total.join(retr2_total, how='inner', lsuffix='1', rsuffix='2')[
                    ['retrans/s1', 'retrans/s2']]

                 retr_total.append(total.sum(axis=1))

           if len(retr_total) > 0:
            retr_total = np.concatenate(retr_total, axis=0)


           if len(retr_total) > 0:
              data_entry = [protocol, bw, delay, delay/10, mult, retr_total.mean(), retr_total.std()]
              data.append(data_entry)

   summary_data = pd.DataFrame(data,
                              columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult', 'retr_total_mean', 'retr_total_std'])

   bbr_data = summary_data[summary_data['protocol'] == 'bbr'].set_index('bandwidth')
   cubic_data = summary_data[summary_data['protocol'] == 'cubic'].set_index('bandwidth')
   bbr1_data = summary_data[summary_data['protocol'] == 'bbr1'].set_index('bandwidth')

   LINEWIDTH = 0.15
   ELINEWIDTH = 0.75
   CAPTHICK = ELINEWIDTH
   CAPSIZE= 2
   SCALE = 'linear'
   LOC = 4 if SCALE == 'log' else 2

   fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(3,1.2))
   ax = axes


   markers, caps, bars = ax.errorbar(cubic_data.index,cubic_data['retr_total_mean']*1448.0*8.0/(1024.0*1024.0), yerr=(cubic_data[['retr_total_mean','retr_total_std']].min(axis=1)*1448*8/(1024*1024),cubic_data['retr_total_std']*1448*8/(1024*1024)),marker='x',elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,linewidth=LINEWIDTH, label='cubic')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(bbr_data.index,bbr_data['retr_total_mean']*1448*8/(1024*1024), yerr=(bbr_data[['retr_total_mean','retr_total_std']].min(axis=1)*1448*8/(1024*1024),bbr_data['retr_total_std']*1448*8/(1024*1024)),marker='^',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='bbr')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(bbr1_data.index,bbr1_data['retr_total_mean']*1448*8/(1024*1024), yerr=(bbr1_data[['retr_total_mean','retr_total_std']].min(axis=1)*1448*8/(1024*1024),bbr1_data['retr_total_std']*1448*8/(1024*1024)),marker='+',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='bbr1')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]

   ax.set(xlabel='Bandwidth (Mbps)', ylabel='Retr. Rate (Mbps)',yscale=SCALE)
   for axis in [ax.xaxis, ax.yaxis]:
       axis.set_major_formatter(ScalarFormatter())

   handles, labels = ax.get_legend_handles_labels()
   # remove the errorbars
   handles = [h[0] for h in handles]

   legend = fig.legend(handles, labels,ncol=3, loc='upper center',bbox_to_anchor=(0.5, 1.08),columnspacing=0.8,handletextpad=0.5)
   # ax.grid()

   for format in ['pdf']:
      plt.savefig('retr_async_bw_%s_%s.%s' % (SCALE,mult, format), dpi=720)
