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

ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_parking_lot_hop_count/fifo" 
PROTOCOLS = ['cubic', 'astraea', 'bbr3', 'bbr1', 'sage'] 
BWS = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
QMULTS = 1
RUNS = [1, 2, 3, 4, 5]
LOSSES=[0]
FLOWS=[3,5,6]

def export_legend(legend, bbox=None, filename="legend.png"):
   fig = legend.figure
   fig.canvas.draw()
   if not bbox:
      bbox = legend.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
   fig.savefig(filename, dpi=1080, bbox_inches=bbox)


for flow in FLOWS:
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
                    PATH =  f'{ROOT_PATH}/ParkingLot_{bw}mbit_{delay}ms_{int(QMULTS * BDP_IN_PKTS)}pkts_0loss_{flow}flows_22tcpbuf_{protocol}/run{run}'
                    receiver_file_spine = f'{PATH}/csvs/x1.csv'
                    receiver_files_ribs = [f'{PATH}/csvs/x{i}.csv' for i in range(2, flow + 1)]
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
                        data_entry = [protocol, bw, delay, delay/10, flow, goodput_ratios_total.mean(), goodput_ratios_total.std()]
                        data.append(data_entry)

    summary_data = pd.DataFrame(data,columns=['protocol', 'bandwidth', 'delay', 'delay_ratio','flows', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])
    
    fig, axes = plt.subplots(nrows=1, ncols=1,figsize=(3,1.2))
    ax = axes
    for protocol in PROTOCOLS_LEO:
        plot_points(ax, summary_data[summary_data['protocol'] == protocol].set_index('delay'), 'goodput_ratio_total_mean', 'goodput_ratio_total_std', PROTOCOLS_MARKERS_LEO[protocol], COLORS_LEO[protocol], PROTOCOLS_FRIENDLY_NAME_LEO[protocol], True)
    for y, label, offset, color in [(1, 'max-min', -0.11, "red"), (1/flow / ((flow-1)/flow), 'proportional', 0.02, "black")]:
        ax.axhline(y, color=color, linestyle='--', linewidth=0.75)
        ax.text(ax.get_xlim()[1], y + offset, f' {label}', color=color, fontsize=6, va='bottom', ha='right')

        ax.set(yscale='linear',xlabel='RTT (ms)', ylabel='Goodput Ratio', ylim=[-0.1,1.1])

    ax.set(yscale='linear',xlabel='RTT (ms)', ylabel='Goodput Ratio')
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_major_formatter(ScalarFormatter())
    handles, labels = ax.get_legend_handles_labels()
    handles = [h[0] for h in handles]
    leg1 = fig.legend(
        handles[:3], labels[:3],
        ncol=3,
        loc='upper center',
        bbox_to_anchor=(0.45, 1.15),
        frameon=False,
        fontsize=7,
        columnspacing=0.8,
        handlelength=2.5,
        handletextpad=0.5
    )
    fig.add_artist(leg1)

    leg2 = fig.legend(
        handles[3:], labels[3:],
        ncol=2,
        loc='upper center',
        bbox_to_anchor=(0.45, 1.05),
        frameon=False,
        fontsize=7,
        columnspacing=0.8,
        handlelength=2.5,
        handletextpad=0.5
    )


    
    plt.savefig(f"goodput_ratio_between_hops_goodput_flows{flow}.pdf", dpi=1080)

