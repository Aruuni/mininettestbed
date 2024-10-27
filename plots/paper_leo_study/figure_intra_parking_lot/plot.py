import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os
from matplotlib.ticker import ScalarFormatter
import numpy as np

plt.rcParams['text.usetex'] = False


ROOT_PATH = "/home/mihai/mininettestbed/nooffload/results_parking_lot/fifo" 
PROTOCOLS = ['cubic', 'bbr', 'sage', 'pcc', 'orca', 'bbr3']
BWS = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
QMULTS = [0.2, 1 ,4]
RUNS = [1, 2, 3, 4, 5]
LOSSES=[0]
FLOWS=4

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
           start_time = 2*delay
           BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
           BDP_IN_PKTS = BDP_IN_BYTES / 1500

           goodput_ratios_20 = []
           goodput_ratios_total = []

           for run in RUNS:
            PATH = ROOT_PATH + '/ParkingLot_%smbit_%sms_%spkts_0loss_%sflows_22tcpbuf_%s/run%s' % (bw, delay, int(mult * BDP_IN_PKTS), FLOWS, protocol, run)
            receiver_file_spine = f'{PATH}/csvs/x1.csv'
            receiver_files_ribs = [f'{PATH}/csvs/x{i}.csv' for i in range(2, FLOWS + 1)]
            if all(os.path.exists(f) for f in receiver_files_ribs) and os.path.exists(receiver_file_spine):
                receivers_ribs_unprocessed = [pd.read_csv(f).reset_index(drop=True) for f in receiver_files_ribs]
                receiver_spine = pd.read_csv(receiver_file_spine).reset_index(drop=True)
                
                receiver_spine['time'] = receiver_spine['time'].apply(lambda x: int(float(x)))
                receiver_spine = receiver_spine[(receiver_spine['time'] >= start_time)]
                receiver_spine = receiver_spine.drop_duplicates('time')
                receiver_spine = receiver_spine.set_index('time')

                
                
                
                receivers_ribs = []
                for rib in receivers_ribs_unprocessed:
                    rib['time'] = rib['time'].apply(lambda x: int(float(x)))
                    rib = rib[(rib['time'] >= start_time)]
                    rib = rib.drop_duplicates('time')
                    rib = rib.set_index('time')
                    receivers_ribs.append(rib)

                
                combined_ribs = pd.concat([rib['bandwidth'] for rib in receivers_ribs], axis=1, keys=[f'Rib{i+1}' for i in range(len(receivers_ribs))])
                max_bandwidth_between_ribs = combined_ribs.max(axis=1).reset_index()
                max_bandwidth_between_ribs.columns = ['time', 'bandwidth']
                max_bandwidth_between_ribs.set_index('time')

                # Print or return the new DataFrame with time and max_bandwidth
                total = receiver_spine[['bandwidth']].join(max_bandwidth_between_ribs.set_index('time'), how='inner', lsuffix='1', rsuffix='2')             
                # total = total.dropna()
                # partial = partial.dropna()

                goodput_ratios_total.append(total.min(axis=1)/total.max(axis=1))
            else:
                avg_goodput = None
                std_goodput = None
                jain_goodput_20 = None
                jain_goodput_total = None
                print("Folder %s not found." % PATH)

           if len(goodput_ratios_total) > 0:
              goodput_ratios_total = np.concatenate(goodput_ratios_total, axis=0)

              if len(goodput_ratios_total) > 0:
                 data_entry = [protocol, bw, delay, delay/10, mult, goodput_ratios_total.mean(), goodput_ratios_total.std()]
                 data.append(data_entry)

   summary_data = pd.DataFrame(data,
                              columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','qmult', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])

   cubic_data = summary_data[summary_data['protocol'] == 'cubic'].set_index('delay')
   orca_data = summary_data[summary_data['protocol'] == 'orca'].set_index('delay')
   bbr3_data = summary_data[summary_data['protocol'] == 'bbr3'].set_index('delay')
   bbr_data = summary_data[summary_data['protocol'] == 'bbr'].set_index('delay')
   sage_data = summary_data[summary_data['protocol'] == 'sage'].set_index('delay')
   pcc_data = summary_data[summary_data['protocol'] == 'pcc'].set_index('delay')

   LINEWIDTH = 0.15
   ELINEWIDTH = 0.75
   CAPTHICK = ELINEWIDTH
   CAPSIZE= 2

   fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
   ax = axes



   markers, caps, bars = ax.errorbar(cubic_data.index*2, cubic_data['goodput_ratio_total_mean'], yerr=cubic_data['goodput_ratio_total_std'],marker='x',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK, label='cubic')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(orca_data.index*2,orca_data['goodput_ratio_total_mean'], yerr=orca_data['goodput_ratio_total_std'],marker='+',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='orca')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(bbr3_data.index*2, bbr3_data['goodput_ratio_total_mean'], yerr=bbr3_data['goodput_ratio_total_std'],marker='^',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK, label='bbrv3')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(bbr_data.index*2,bbr_data['goodput_ratio_total_mean'], yerr=bbr_data['goodput_ratio_total_std'],marker='.',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='bbrv1')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(sage_data.index*2,sage_data['goodput_ratio_total_mean'], yerr=sage_data['goodput_ratio_total_std'],marker='*',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='sage')
   [bar.set_alpha(0.5) for bar in bars]
   [cap.set_alpha(0.5) for cap in caps]
   markers, caps, bars = ax.errorbar(pcc_data.index*2,pcc_data['goodput_ratio_total_mean'], yerr=pcc_data['goodput_ratio_total_std'],marker='_',linewidth=LINEWIDTH, elinewidth=ELINEWIDTH, capsize=CAPSIZE, capthick=CAPTHICK,label='vivace')
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
      plt.savefig('goodput_ratio_between_max_ribs_%s.%s' % (mult, format), dpi=1080)

