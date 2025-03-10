import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter
import numpy as np

plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *

ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_bw_async/fifo" 
PROTOCOLS = ['cubic', 'sage', 'orca', 'astraea', 'bbr3', 'vivace']
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
           start_time = 25
           end_time = 100
           keep_last_seconds = 25

           BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
           BDP_IN_PKTS = BDP_IN_BYTES / 1500

           goodput_ratios_20 = []
           goodput_ratios_total = []

           for run in RUNS:
              PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_2flows_22tcpbuf_%s/run%s' % (bw,delay,int(mult * BDP_IN_PKTS),protocol,run)
              if os.path.exists(PATH + '/csvs/x1.csv') and os.path.exists(PATH + '/csvs/x2.csv'):
                 receiver1_total = pd.read_csv(PATH + '/csvs/x1.csv').reset_index(drop=True)
                 receiver2_total = pd.read_csv(PATH + '/csvs/x2.csv').reset_index(drop=True)

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

                 receiver1 = receiver1.set_index('time')
                 receiver2 = receiver2.set_index('time')

                 total = receiver1_total.join(receiver2_total, how='inner', lsuffix='1', rsuffix='2')[['bandwidth1', 'bandwidth2']]
                 partial = receiver1.join(receiver2, how='inner', lsuffix='1', rsuffix='2')[['bandwidth1', 'bandwidth2']]

                 # total = total.dropna()
                 # partial = partial.dropna()

                 goodput_ratios_20.append(partial.min(axis=1)/partial.max(axis=1))
                 goodput_ratios_total.append(total.min(axis=1)/total.max(axis=1))
              else:
                 avg_goodput = None
                 std_goodput = None
                 jain_goodput_20 = None
                 jain_goodput_total = None
                 print("Folder %s not found." % PATH)

           if len(goodput_ratios_20) > 0 and len(goodput_ratios_total) > 0:
              goodput_ratios_20 = np.concatenate(goodput_ratios_20, axis=0)
              goodput_ratios_total = np.concatenate(goodput_ratios_total, axis=0)

              if len(goodput_ratios_20) > 0 and len(goodput_ratios_total) > 0:
                 data_entry = [protocol, bw, delay, delay/10, mult, goodput_ratios_20.mean(), goodput_ratios_20.std(), goodput_ratios_total.mean(), goodput_ratios_total.std()]
                 data.append(data_entry)

   summary_data = pd.DataFrame(data,
                              columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult', 'goodput_ratio_20_mean',
                                       'goodput_ratio_20_std', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])


   cubic_data = summary_data[summary_data['protocol'] == 'cubic'].set_index('bandwidth')
   orca_data = summary_data[summary_data['protocol'] == 'orca'].set_index('bandwidth')
   bbr3_data = summary_data[summary_data['protocol'] == 'bbr3'].set_index('bandwidth')
   bbr_data = summary_data[summary_data['protocol'] == 'bbr1'].set_index('bandwidth')
   sage_data = summary_data[summary_data['protocol'] == 'sage'].set_index('bandwidth')
   pcc_data = summary_data[summary_data['protocol'] == 'vivace'].set_index('bandwidth')
   astraea_data = summary_data[summary_data['protocol'] == 'astraea'].set_index('bandwidth')
   LINEWIDTH = 0.20
   ELINEWIDTH = 0.75
   CAPTHICK = ELINEWIDTH
   CAPSIZE= 2

   fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
   ax = axes

   if 'cubic' in PROTOCOLS:
      markers, caps, bars = ax.errorbar(cubic_data.index, cubic_data['goodput_ratio_20_mean'], yerr=cubic_data['goodput_ratio_20_std'],marker='x',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK, label='cubic')
      [bar.set_alpha(0.5) for bar in bars]
      [cap.set_alpha(0.5) for cap in caps]
   if 'orca' in PROTOCOLS:
      markers, caps, bars = ax.errorbar(orca_data.index,orca_data['goodput_ratio_20_mean'], yerr=orca_data['goodput_ratio_20_std'],marker='+',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='orca')
      [bar.set_alpha(0.5) for bar in bars]
      [cap.set_alpha(0.5) for cap in caps]
   if 'bbr3' in PROTOCOLS:
      markers, caps, bars = ax.errorbar(bbr3_data.index,bbr3_data['goodput_ratio_20_mean'], yerr=bbr3_data['goodput_ratio_20_std'],marker='^',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='bbrv3')
      [bar.set_alpha(0.5) for bar in bars]
      [cap.set_alpha(0.5) for cap in caps]
   if 'bbr1' in PROTOCOLS:
      markers, caps, bars = ax.errorbar(bbr_data.index,bbr_data['goodput_ratio_20_mean'], yerr=bbr_data['goodput_ratio_20_std'],marker='.',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='bbrv1')
      [bar.set_alpha(0.5) for bar in bars]
      [cap.set_alpha(0.5) for cap in caps]
   if 'sage' in PROTOCOLS:
      markers, caps, bars = ax.errorbar(sage_data.index,sage_data['goodput_ratio_20_mean'], yerr=sage_data['goodput_ratio_20_std'],marker='*',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='sage')
      [bar.set_alpha(0.5) for bar in bars]
      [cap.set_alpha(0.5) for cap in caps]
   if 'vivace' in PROTOCOLS:
      markers, caps, bars = ax.errorbar(pcc_data.index,pcc_data['goodput_ratio_20_mean'], yerr=pcc_data['goodput_ratio_20_std'],marker='_',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='vivace')
      [bar.set_alpha(0.5) for bar in bars]
      [cap.set_alpha(0.5) for cap in caps]
   if 'astraea' in PROTOCOLS:
      markers, caps, bars = ax.errorbar(astraea_data.index,astraea_data['goodput_ratio_20_mean'], yerr=astraea_data['goodput_ratio_20_std'],marker='2',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='astraea')
      [bar.set_alpha(0.5) for bar in bars]
      [cap.set_alpha(0.5) for cap in caps]




   ax.set(yscale='linear',xlabel='Bandwidth (Mbps)', ylabel='Goodput Ratio')
   for axis in [ax.xaxis, ax.yaxis]:
       axis.set_major_formatter(ScalarFormatter())
   handles, labels = ax.get_legend_handles_labels()
   # remove the errorbars
   handles = [h[0] for h in handles]

   legend = fig.legend(handles, labels,ncol=3, loc='upper center',bbox_to_anchor=(0.5, 1.28),columnspacing=0.8,handletextpad=0.5)# ax.grid()

   for format in ['pdf']:
      plt.savefig('goodput_ratio_bw_%s.%s' % (mult, format), dpi=720)








