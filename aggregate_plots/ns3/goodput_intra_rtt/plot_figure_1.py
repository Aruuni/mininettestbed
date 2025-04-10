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
from core.utils import *


ROOT_PATH = f"{HOME_DIR}/cctestbed/ns3/results_fairness_intra_rtt/fifo" 
PROTOCOLS = ['cubic', 'bbr', 'bbr3']
BWS = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
QMULTS = [0.2, 1 ,4]
RUNS = [1, 2, 3, 4, 5]
LOSSES=[0]

def export_legend(legend, bbox=None, filename="legend.png"):
   fig = legend.figure
   fig.canvas.draw()
   if not bbox:
      bbox = legend.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
   fig.savefig(filename, dpi=1080, bbox_inches=bbox)


for mult in QMULTS:
   data = []
   for protocol in PROTOCOLS:
     for bw in BWS:
        for delay in DELAYS:
           duration = 2*delay
           start_time = 3*delay
           end_time = 4*delay
           keep_last_seconds = int(0.25*delay)

           BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
           BDP_IN_PKTS = BDP_IN_BYTES / 1500

           goodput_ratios_total = []

           for run in RUNS:
              PATH = ROOT_PATH + f"/Dumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{run}" 
              file1 = f"/Tcp{protocol.capitalize()}-1-goodput.csv"
              file2 = f"/Tcp{protocol.capitalize()}-2-goodput.csv"
              if os.path.exists(PATH + file1) and os.path.exists(PATH + file2):
                 receiver1_total = pd.read_csv(PATH + file1).reset_index(drop=True)
                 receiver2_total = pd.read_csv(PATH + file2).reset_index(drop=True)

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
                 total = receiver1_total.join(receiver2_total, how='inner', lsuffix='1', rsuffix='2')

                 # total = total.dropna()
                 # partial = partial.dropna()
         
                 goodput_ratios_total.append(total.min(axis=1)/total.max(axis=1))
              else:
                 avg_goodput = None
                 std_goodput = None
                 jain_goodput_20 = None
                 jain_goodput_total = None
                 print("Folder %s not found." % PATH)

           if  len(goodput_ratios_total) > 0:
              goodput_ratios_total = np.concatenate(goodput_ratios_total, axis=0)

              if len(goodput_ratios_total) > 0:
                 data_entry = [protocol, bw, delay, delay/10, mult,  goodput_ratios_total.mean(), goodput_ratios_total.std()]
                 data.append(data_entry)

   summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])

   cubic_data = summary_data[summary_data['protocol'] == 'cubic'].set_index('delay')
   bbr3_data = summary_data[summary_data['protocol'] == 'bbr3'].set_index('delay')
   bbr_data = summary_data[summary_data['protocol'] == 'bbr'].set_index('delay')


   LINEWIDTH = 0.15
   ELINEWIDTH = 0.75
   CAPTHICK = ELINEWIDTH
   CAPSIZE= 2

   fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
   ax = axes



   markers, caps, bars = ax.errorbar(cubic_data.index*2, cubic_data['goodput_ratio_total_mean'], yerr=cubic_data['goodput_ratio_total_std'],marker='x',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK, label='cubic')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(bbr3_data.index*2, bbr3_data['goodput_ratio_total_mean'], yerr=bbr3_data['goodput_ratio_total_std'],marker='^',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK, label='bbrv3')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(bbr_data.index*2,bbr_data['goodput_ratio_total_mean'], yerr=bbr_data['goodput_ratio_total_std'],marker='.',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='bbrv1')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]

   ax.set(yscale='linear',xlabel='RTT (ms)', ylabel='Goodput Ratio', ylim=[-0.1,1.1])
   for axis in [ax.xaxis, ax.yaxis]:
       axis.set_major_formatter(ScalarFormatter())
   # ax.legend(loc=4,prop={'size': 6})
   # get handles
   handles, labels = ax.get_legend_handles_labels()
   # remove the errorbars
   handles = [h[0] for h in handles]

   legend = fig.legend(handles, labels,ncol=3, loc='upper center',bbox_to_anchor=(0.5, 1.28),columnspacing=0.8, handletextpad=0.9)
   # ax.grid()

   for format in ['pdf']:
      plt.savefig(f"goodput_ratio_async_intra_{mult}.{format}", dpi=1080)

