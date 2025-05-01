import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import os, sys
import matplotlib as mpl
mpl.rcParams['agg.path.chunksize'] = 10000
pd.set_option('display.max_rows', None)
from functools import reduce
import numpy as np
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms
from matplotlib.lines import Line2D
plt.rcParams['text.usetex'] = False

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 

def confidence_ellipse(x, y, ax, n_std=1.0, facecolor='none', **kwargs):
    if x.size != y.size:
        raise ValueError("x and y must be the same size")
    cov = np.cov(x, y)
    pearson = cov[0, 1]/np.sqrt(cov[0, 0] * cov[1, 1])
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,facecolor=facecolor, **kwargs)
    scale_x = np.sqrt(cov[0, 0]) * n_std
    mean_x = np.mean(x)
    scale_y = np.sqrt(cov[1, 1]) * n_std
    mean_y = np.mean(y)
    transf = transforms.Affine2D() \
        .rotate_deg(45) \
        .scale(scale_x, scale_y) \
        .translate(mean_x, mean_y)
    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)

def data_to_df(folder, delays, bandwidths, qmults, aqms, protocols):
    data=[]
    efficiency_fairness_data = []
    start_time = 0
    end_time = 100
    for aqm in aqms:
        for qmult in qmults:
            for delay in delays:
                for BW in bandwidths:
                    for protocol in protocols:
                        BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                        BDP_IN_PKTS = BDP_IN_BYTES / 1500
                        for run in RUNS:
                            PATH = folder + f"/{aqm}/Dumbell_{BW}mbit_{delay}ms_{int(qmult * BDP_IN_PKTS)}pkts_0loss_{4}flows_22tcpbuf_{protocol}/run{run}" 
                            flows = []
                            retr_flows = []
                            delay_flows = []
                            for n in range(4):
                                if os.path.exists(f"{PATH}/csvs/x{(n + 1)}.csv"):
                                    receiver_total = pd.read_csv(f"{PATH}/csvs/x{(n + 1)}.csv").reset_index(drop=True)
                                    receiver_total = receiver_total[['time', 'bandwidth']]
                                    receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))

                                    receiver_total = receiver_total[(receiver_total['time'] >= (start_time + n * 25)) & (
                                                receiver_total['time'] <= (end_time + n * 25))]
                                    receiver_total = receiver_total.drop_duplicates('time')
                                    receiver_total = receiver_total.set_index('time')
                                    flows.append(receiver_total)
                                    bandwidth_mean = receiver_total.mean().values[0]
                                    bandwidth_std = receiver_total.std().values[0]
                                else:
                                    print(f"Folder {PATH} not found")
                                    receiver_total = None
                                    bandwidth_mean = None
                                    bandwidth_std = None

                                if protocol == 'vivace-uspace' or protocol == 'astraea':
                                    sender = pd.read_csv(f"{PATH}/csvs/c{(n + 1)}.csv")
                                else:
                                    sender = pd.read_csv(f"{PATH}/csvs/c{(n + 1)}_ss.csv")
                                sender = sender[['time', 'srtt']]
                                sender = sender[(sender['time'] >= (start_time + n * 25)) & (sender['time'] <= (end_time + n * 25))]

                                # We need to resample this data to 1 Hz frequency: Truncate time value to seconds, groupby.mean()
                                sender['time'] = sender['time'].apply(lambda x: int(x))
                                sender = sender.groupby('time').mean()
                                if len(sender) > 0:
                                    delay_flows.append(sender)
                                delay_mean = sender.mean().values[0]
                                delay_std = sender.std().values[0]
                        

                                if os.path.exists(f"{PATH}/sysstat/etcp_c{(n + 1)}.log") and protocol != 'vivace-uspace':
                                    systat = pd.read_csv(f"{PATH}/sysstat/etcp_c{(n + 1)}.log", sep=';').rename(
                                        columns={"# hostname": "hostname"})
                                    retr = systat[['timestamp', 'retrans/s']]

                                    if n == 0:
                                        start_timestamp = retr['timestamp'].iloc[0]

                                    retr.loc[:, 'timestamp'] = retr['timestamp'] - start_timestamp + 1

                                    retr = retr.rename(columns={'timestamp': 'time'})
                                    retr['time'] = retr['time'].apply(lambda x: int(float(x)))
                                    retr = retr[(retr['time'] >= (start_time + n * 25)) & (
                                                retr['time'] <= (end_time + n * 25))]
                                    retr = retr.drop_duplicates('time')

                                    retr = retr.set_index('time')
                                    retr_flows.append(retr*1500*8/(1024*1024))
                                    retr_mean = retr.mean().values[0]
                                    retr_std = retr.std().values[0]
                                if os.path.exists(f"{PATH}/csvs/c{(n + 1)}.csv") and protocol == 'vivace-uspace':
                                    systat = pd.read_csv(f"{PATH}/csvs/c{(n + 1)}.csv").rename(
                                        columns={"retr": "retrans/s"})
                                    retr = systat[['time', 'retrans/s']]
                                    retr['time'] = retr['time'].apply(lambda x: int(float(x)))
                                    retr = retr[
                                        (retr['time'] >= (start_time + n * 25)) & (retr['time'] <= (end_time + n * 25))]
                                    retr = retr.drop_duplicates('time')
                                    retr = retr.set_index('time')
                                    retr_flows.append(retr*1500*8/(1024*1024))
                                    retr_mean = retr.mean().values[0]
                                    retr_std = retr.std().values[0]
                               
                                if os.path.exists(PATH + '/sysstat/dev_root.log'):
                                    systat = pd.read_csv(PATH + '/sysstat/dev_root.log', sep=';').rename(
                                        columns={"# hostname": "hostname"})
                                    util = systat[['timestamp', 'IFACE', 'txkB/s', '%ifutil']]

                                    start_timestamp = util['timestamp'].iloc[0]

                                    #util['timestamp'] = util['timestamp'] - start_timestamp + 1
                                    util.loc[:, 'timestamp'] = util['timestamp'] - start_timestamp + 1


                                    util = util.rename(columns={'timestamp': 'time'})
                                    util['time'] = util['time'].apply(lambda x: int(float(x)))
                                    util = util[(util['time'] >= (start_time)) & (util['time'] < (end_time))]
                                    util_if = util[util['IFACE'] == "s2-eth2"]
                                    util_if = util_if[['time', 'txkB/s']]
                                    util_if = util_if.set_index('time')
                                    util_mean = util_if.mean().values[0]*8/1024
                                    util_std = util_if.std().values[0]*8/1024
                                else:
                                    util_mean = None
                                    util_std = None


                                data_point = [aqm, qmult, delay, BW, protocol, run, n, bandwidth_mean, bandwidth_std, delay_mean, delay_std, retr_mean, retr_std, util_mean, util_std]
                                data.append(data_point)

                            if len(flows) > 0:
                                if os.path.exists(f"{PATH}/sysstat/dev_root.log"):
                                    systat = pd.read_csv(f"{PATH}/sysstat/dev_root.log", sep=';').rename(
                                        columns={"# hostname": "hostname"})
                                    util = systat[['timestamp', 'IFACE', 'txkB/s', '%ifutil']]

                                    start_timestamp = util['timestamp'].iloc[0]

                                    util.loc[:, 'timestamp'] = util['timestamp'] - start_timestamp + 1

                                    util = util.rename(columns={'timestamp': 'time'})
                                    util['time'] = util['time'].apply(lambda x: int(float(x)))
                                    util = util[(util['time'] >= (start_time)) & (util['time'] < (end_time))]
                                    util_if = util[util['IFACE'] == "s2-eth2"]
                                    util_if = util_if[['time', 'txkB/s']]
                                    util_if = util_if.set_index('time')
                                    util_mean = util_if.mean().values[0] * 8 / 1024
                                    util_std = util_if.std().values[0] * 8 / 1024
                                else:
                                    util_mean = None
                                    util_std = None

                                #df_merged = reduce(lambda left, right: pd.merge(left, right, on=['time'],how='inner'), flows)
                                df_merged = pd.concat(flows).reset_index(drop=True)     
                                df_merged_sum = df_merged.sum(axis=1)
                                df_merged_ratio = df_merged.min(axis=1) / df_merged.max(axis=1)

                                #df_retr_merged = reduce(lambda left, right: pd.merge(left, right, on=['time'],how='inner'), retr_flows)

                                df_retr_merged = pd.concat(retr_flows).reset_index(drop=True)
                                df_retr_merged_sum = df_retr_merged.sum(axis=1)
                                #df_delay_merged = reduce(lambda left, right: pd.merge(left, right, on=['time'],how='inner'), delay_flows)
                                df_delay_merged = pd.concat(delay_flows).reset_index(drop=True)  
                                df_delay_merged_mean = df_delay_merged.mean(axis=1)

                                efficiency_metric1 = (df_merged_sum/BW) / (
                                            df_delay_merged_mean / (2 * delay))
                                efficiency_metric2 = (df_merged_sum/BW - df_retr_merged_sum/BW)/(df_delay_merged_mean/(2*delay))

                                efficiency_fairness_data.append([aqm, qmult, delay, BW, protocol, run, df_delay_merged_mean.mean(), df_merged_sum.mean(),df_merged_sum.std(),df_merged_ratio.mean(),df_merged_ratio.std(),df_retr_merged_sum.mean(),df_retr_merged_sum.std(), efficiency_metric1.mean(), efficiency_metric1.std(), efficiency_metric2.mean(), efficiency_metric2.std(), util_mean, util_std])

    COLUMNS1 = ['aqm', 'qmult', 'min_delay', 'bandwidth', 'protocol', 'run', 'flow','goodput_mean', 'goodput_std', 'delay_mean', 'delay_std', 'retr_mean', 'retr_std', 'util_mean', 'util_std']
    COLUMNS2 = ['aqm', 'qmult', 'min_delay', 'bandwidth', 'protocol', 'run', 'delay_mean' ,'efficiency_mean','efficiency_std', 'fairness_mean', 'fairness_std', 'retr_mean', 'retr_std', 'efficiency1_mean', 'efficiency1_std', 'efficiency2_mean', 'efficiency2_std', 'util_mean', 'util_std']
    return pd.DataFrame(data,columns=COLUMNS1), pd.DataFrame(efficiency_fairness_data,columns=COLUMNS2),


def plot_data(data, filename, ylim=None):
    LINEWIDTH = 1
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(4, 3), sharex=True, sharey=True)

    for i, protocol in enumerate(PROTOCOLS_LEO):
        ax = axes[i]
        for n in range(4):
            ax.plot(data['fifo'][protocol][n + 1].index, data['fifo'][protocol][n + 1]['mean'],
                    linewidth=LINEWIDTH, label=protocol)
            try:
                ax.fill_between(data['fifo'][protocol][n + 1].index,
                                data['fifo'][protocol][n + 1]['mean'] - data['fifo'][protocol][n + 1]['std'],
                                data['fifo'][protocol][n + 1]['mean'] + data['fifo'][protocol][n + 1]['std'],
                                alpha=0.2)
            except:
                print(f"Protocol: {protocol}")
                print(data['fifo'][protocol][n + 1]['mean'])
                print(data['fifo'][protocol][n + 1]['std'])

        if ylim:
            ax.set(ylim=ylim)

        if i == 2:
            ax.set(xlabel='time (s)')

        ax.text(70, 1.8, '%s' % protocol, va='center', c=COLORS_LEO[protocol])
        ax.grid()

    plt.savefig(filename, dpi=720)



if __name__ == "__main__":
    EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_aqm"
    DELAYS = [10, 50]
    RUNS = [1, 2, 3, 4, 5]
    
    MARKER_MAP = {10: '^',
                 50: '*'}
    delay_handles = [
        Line2D(
            [], [], 
            marker=MARKER_MAP[d],
            color='black',
            linestyle='None',
            markersize=6,
            markeredgewidth=1,
            markerfacecolor='none'
        )
        for d in DELAYS
    ]
    delay_labels = [f"{d} ms" for d in DELAYS]  
    proto_handles = [
        Line2D([], [], color=COLORS_LEO[p], linewidth=1) for p in PROTOCOLS_LEO
    ]
    proto_labels = [PROTOCOLS_FRIENDLY_NAME_LEO[p] for p in PROTOCOLS_LEO]
    #AQM_LIST = ['fifo', 'codel', 'fq']
    AQM_LIST = ['fifo']
    df1,df2 = data_to_df(EXPERIMENT_PATH, DELAYS, [100], QMULTS, AQM_LIST, PROTOCOLS_LEO)
    df1.to_csv('aqm_data.csv', index=False)
    df2.to_csv('aqm_efficiency_fairness.csv', index=False)
    df = pd.read_csv('aqm_efficiency_fairness.csv', index_col=None).dropna()
    df = df[df['aqm'] == 'fifo']
    df['aqm'] = pd.to_numeric(df['aqm'], errors='coerce')
    data = df.groupby(['min_delay','qmult','protocol']).mean()


    for CONTROL_VAR in QMULTS:
        fig, axes = plt.subplots(figsize=(3,1.5))
        for protocol in PROTOCOLS_LEO:
            for delay in DELAYS:
                if not (delay == 100 and protocol == 'aurora' and CONTROL_VAR == 4):
                    axes.scatter(data.loc[delay,CONTROL_VAR, protocol]['delay_mean']/ (delay*2), data.loc[delay,CONTROL_VAR, protocol]['util_mean']/100 - data.loc[delay,CONTROL_VAR, protocol]['retr_mean']/100, edgecolors=COLORS_LEO[protocol], marker=MARKER_MAP[delay], facecolors='none', alpha=0.25)
                    axes.scatter(data.loc[delay,CONTROL_VAR, protocol]['delay_mean']/ (delay*2), data.loc[delay,CONTROL_VAR, protocol]['util_mean']/100, edgecolors=COLORS_LEO[protocol], marker=MARKER_MAP[delay], facecolors='none', label='%s-%s' % ((lambda p: 'bbrv1' if p == 'bbr' else 'bbrv3' if p == 'bbr3' else 'vivace' if p == 'pcc' else p)(protocol), delay*2))
                    subset = df[(df['protocol'] == protocol) & (df['qmult'] == CONTROL_VAR)  & (df['min_delay'] == delay)]
                    y = subset['util_mean'].values/100
                    x = subset['delay_mean'].values/(delay*2)

                    confidence_ellipse(x, y, axes, facecolor=COLORS_LEO[protocol], edgecolor='none', alpha=0.25)

        handles, labels = axes.get_legend_handles_labels()
        # 1) Top row with 3 entries
        leg1 = fig.legend(
            proto_handles[:3], proto_labels[:3],
            loc='upper center',
            bbox_to_anchor=(0.45, 1.15),  # same as before
            ncol=3, frameon=False,
            fontsize=7, columnspacing=1.0,
            handlelength=2.5, handletextpad=0.7
        )
        fig.add_artist(leg1)  # keep this legend so the next one can also be drawn

        # 2) Bottom row with the remaining 2 entries, perfectly centered in 2 columns
        leg2 = fig.legend(
            proto_handles[3:], proto_labels[3:],
            loc='upper center',
            bbox_to_anchor=(0.45, 1.05),  # tweak this for vertical spacing
            ncol=2, frameon=False,
            fontsize=7, columnspacing=1.0,
            handlelength=2.5, handletextpad=0.7
        )
        axes.set(ylabel="Norm. Throughput", xlabel="Norm. Delay", ylim=[0.5,1])
        axes.legend([ Line2D([], [], 
            marker=MARKER_MAP[d],
            color='black',
            linestyle='None',
            markersize=6,
            markeredgewidth=1,
            markerfacecolor='none'
        ) for d in DELAYS], 
            [f"{d*2} ms" for d in DELAYS],
            loc='lower right',
            frameon=False,
            fontsize=6,
            handlelength=0,
            handletextpad=0.8,
            labelspacing=0.2,
            title="RTT",
            title_fontsize=6
        )
        axes.invert_xaxis()
        plt.savefig(f"qmult{CONTROL_VAR}_scatter1.pdf" , dpi=1080)