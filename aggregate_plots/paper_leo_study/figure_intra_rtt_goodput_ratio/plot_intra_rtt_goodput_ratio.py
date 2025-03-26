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
from core.plotting import * 

ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_intra_rtt_async/fifo" 
PROTOCOLS = ['cubic', 'astraea', 'bbr3', 'bbr1', 'sage']
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

   summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult', 'goodput_ratio_20_mean',
                                       'goodput_ratio_20_std', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])

   fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
   ax = axes

   plot_points_rtt(ax, summary_data[summary_data['protocol'] == 'cubic'].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std',   'x', 'cubic')
   plot_points_rtt(ax, summary_data[summary_data['protocol'] == 'bbr1'].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std',  '.', 'bbrv1')
   plot_points_rtt(ax, summary_data[summary_data['protocol'] == 'bbr3'].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std',   '^', 'bbrv3')
   plot_points_rtt(ax, summary_data[summary_data['protocol'] == 'sage'].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std',   '*', 'sage')
   plot_points_rtt(ax, summary_data[summary_data['protocol'] == 'astraea'].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std','2', 'astraea')



   ax.set(yscale='linear',xlabel='RTT (ms)', ylabel='Goodput Ratio', ylim=[-0.1,1.1])
   for axis in [ax.xaxis, ax.yaxis]:
       axis.set_major_formatter(ScalarFormatter())


   # Build a 2-row "pyramid" legend
   handles, labels = ax.get_legend_handles_labels()
   # Convert errorbar handles if needed
   line_handles = [h[0] if isinstance(h, tuple) else h for h in handles]
   legend_map   = dict(zip(labels, line_handles))

   # Decide which protocols go top vs. bottom row
   handles_top = [legend_map.get('cubic'), legend_map.get('bbrv1'), legend_map.get('bbrv3')]
   labels_top  = ['cubic', 'bbrv1', 'bbrv3']

   handles_bottom = [legend_map.get('sage'), legend_map.get('astraea')]
   labels_bottom  = ['sage', 'astraea']

   legend_top = plt.legend(
      handles_top, labels_top,
      ncol=3,
      loc='upper center',
      bbox_to_anchor=(0.5, 1.41),
      columnspacing=1.0,
      handletextpad=0.5,
      labelspacing=0.1,
      borderaxespad=0.0
   )
   plt.gca().add_artist(legend_top)

   legend_bottom = plt.legend(
      handles_bottom, labels_bottom,
      ncol=2,
      loc='upper center',
      bbox_to_anchor=(0.5, 1.23),
      columnspacing=1.0,
      handletextpad=0.5,
      labelspacing=0.1,
      borderaxespad=0.0
   )

   plt.savefig(f"goodput_ratio_intra_rtt_{mult}.pdf" , dpi=1080)

