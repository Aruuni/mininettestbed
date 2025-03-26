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

plt.rcParams['text.usetex'] = False

# -------------------------------------------------------------------
# Set up paths (assumes your config module defines HOME_DIR, BW, etc.)
# -------------------------------------------------------------------
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)
from core.config import *

# -------------------------------------------------------------------
# Function: confidence_ellipse
# Creates an ellipse based on the covariance of x and y.
# -------------------------------------------------------------------
def confidence_ellipse(x, y, ax, n_std=1.0, facecolor='none', **kwargs):
    if x.size != y.size:
        raise ValueError("x and y must be the same size")
    cov = np.cov(x, y)
    pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                      facecolor=facecolor, **kwargs)
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

# -------------------------------------------------------------------
# Function: data_to_df
# Processes logs to produce two DataFrames:
#  - one for per-run data and another for efficiency/fairness metrics.
# -------------------------------------------------------------------
def data_to_df(folder, delays, bandwidths, qmults, aqms, protocols):
    data = []
    efficiency_fairness_data = []

    num_edge_links = 4  # Number of edge links in the parking lot topology

    for aqm in aqms:
        for qmult in qmults:
            for delay in delays:
                start_time = delay * 2
                end_time = delay * 3.5
                for BW in bandwidths:
                    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * delay * 1e-3 / 8)
                    BDP_IN_PKTS = BDP_IN_BYTES / 1500
                    for protocol in protocols:
                        for run in RUNS:
                            PATH = (
                                folder
                                + f"/{aqm}/ParkingLot_{BW}mbit_{delay}ms_{int(qmult * BDP_IN_PKTS)}pkts_0loss_"
                                + f"{4}flows_22tcpbuf_{protocol}/run{run}"
                            )
                            flows = []
                            retr_flows = []
                            delay_flows = []
                            for n in range(4):
                                csv_file = f"{PATH}/csvs/x{n+1}.csv"
                                if os.path.exists(csv_file):
                                    receiver_total = pd.read_csv(csv_file).reset_index(drop=True)
                                    receiver_total = receiver_total[['time', 'bandwidth']]
                                    receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))
                                    receiver_total = receiver_total[
                                        (receiver_total['time'] >= (start_time))
                                        & (receiver_total['time'] <= (end_time))
                                    ]
                                    receiver_total = receiver_total.drop_duplicates('time')
                                    receiver_total = receiver_total.set_index('time')
                                    flows.append(receiver_total)
                                    bandwidth_mean = receiver_total.mean().values[0]
                                    bandwidth_std = receiver_total.std().values[0]
                                else:
                                    print("Folder %s not found" % PATH)
                                    bandwidth_mean = None
                                    bandwidth_std = None

                                # Process sender logs for delay
                                if protocol == 'astraea':
                                    sender = pd.read_csv(PATH + f"/csvs/c{n+1}.csv")
                                else:
                                    sender = pd.read_csv(PATH + f"/csvs/c{n+1}_ss.csv")
                                sender = sender[['time', 'srtt']]
                                sender = sender[
                                    (sender['time'] >= (start_time))
                                    & (sender['time'] <= (end_time))
                                ]
                                sender = sender.groupby('time').mean()
                                if len(sender) > 0:
                                    delay_flows.append(sender)
                                delay_mean = sender.mean().values[0]
                                delay_std = sender.std().values[0] if len(sender) > 1 else 0

                                # Retr logs
                                if os.path.exists(f"{PATH}/sysstat/etcp_c{n+1}.log"):
                                    systat = pd.read_csv(f"{PATH}/sysstat/etcp_c{n+1}.log", sep=';') \
                                        .rename(columns={"# hostname": "hostname"})
                                    retr = systat[['timestamp', 'retrans/s']]
                                    if n == 0:
                                        start_timestamp = retr['timestamp'].iloc[0]
                                    retr.loc[:, 'timestamp'] = retr['timestamp'] - start_timestamp + 1
                                    retr = retr.rename(columns={'timestamp': 'time'})
                                    retr['time'] = retr['time'].apply(lambda x: int(float(x)))
                                    retr = retr[
                                        (retr['time'] >= (start_time))
                                        & (retr['time'] <= (end_time))
                                    ]
                                    retr = retr.drop_duplicates('time')
                                    retr = retr.set_index('time')
                                    retr_flows.append(retr * 1500 * 8 / (1024 * 1024))
                                    retr_mean = retr.mean().values[0]
                                    retr_std = retr.std().values[0] if len(retr) > 1 else 0
                                else:
                                    print("Folder %s not found" % PATH)
                                    retr_mean = None
                                    retr_std = None

                                # Compute utilisation by summing edge-link logs
                                util_total = None
                                for i in range(1, num_edge_links + 1):
                                    edge_log = f"{PATH}/sysstat/dev_c{i}.log"
                                    if os.path.exists(edge_log):
                                        systat_edge = pd.read_csv(edge_log, sep=';') \
                                            .rename(columns={"# hostname": "hostname"})
                                        systat_edge = systat_edge[systat_edge['IFACE'] != 'lo']
                                        util_edge = systat_edge[['timestamp', 'txkB/s']]
                                        start_timestamp_edge = util_edge['timestamp'].iloc[0]
                                        util_edge.loc[:, 'timestamp'] = (
                                            util_edge['timestamp'] - start_timestamp_edge + 1
                                        )
                                        util_edge = util_edge.rename(columns={'timestamp': 'time'})
                                        util_edge['time'] = util_edge['time'].apply(lambda x: int(float(x)))
                                        util_edge = util_edge[
                                            (util_edge['time'] >= start_time)
                                            & (util_edge['time'] < end_time)
                                        ]
                                        util_edge = util_edge.set_index('time')
                                        # Convert to Mbps
                                        util_conv = util_edge['txkB/s'] * 8 / 1024
                                        if util_total is None:
                                            util_total = util_conv
                                        else:
                                            util_total = util_total.add(util_conv, fill_value=0)
                                if util_total is not None and len(util_total) > 0:
                                    util_mean = util_total.mean()
                                    util_std = util_total.std()
                                else:
                                    util_mean = None
                                    util_std = None

                                data_point = [
                                    aqm, qmult, delay, BW, protocol, run, n,
                                    bandwidth_mean, bandwidth_std,
                                    delay_mean, delay_std,
                                    retr_mean, retr_std,
                                    util_mean, util_std
                                ]
                                data.append(data_point)

                            # If we have flows, compute additional efficiency/fairness data
                            if len(flows) > 0:
                                util_total = None
                                for i in range(1, num_edge_links + 1):
                                    edge_log = f"{PATH}/sysstat/dev_c{i}.log"
                                    if os.path.exists(edge_log):
                                        systat_edge = pd.read_csv(edge_log, sep=';') \
                                            .rename(columns={"# hostname": "hostname"})
                                        systat_edge = systat_edge[systat_edge['IFACE'] != 'lo']
                                        util_edge = systat_edge[['timestamp', 'txkB/s']]
                                        start_timestamp_edge = util_edge['timestamp'].iloc[0]
                                        util_edge.loc[:, 'timestamp'] = (
                                            util_edge['timestamp'] - start_timestamp_edge + 1
                                        )
                                        util_edge = util_edge.rename(columns={'timestamp': 'time'})
                                        util_edge['time'] = util_edge['time'].apply(lambda x: int(float(x)))
                                        util_edge = util_edge[
                                            (util_edge['time'] >= start_time)
                                            & (util_edge['time'] < end_time)
                                        ]
                                        util_edge = util_edge.set_index('time')
                                        util_conv = util_edge['txkB/s'] * 8 / 1024
                                        if util_total is None:
                                            util_total = util_conv
                                        else:
                                            util_total = util_total.add(util_conv, fill_value=0)
                                if util_total is not None and len(util_total) > 0:
                                    util_mean = util_total.mean()
                                    util_std = util_total.std()
                                else:
                                    util_mean = None
                                    util_std = None

                                df_merged = pd.concat(flows).reset_index(drop=True)
                                df_merged_sum = df_merged.sum(axis=1)
                                df_merged_ratio = df_merged.min(axis=1) / df_merged.max(axis=1)
                                df_retr_merged = pd.concat(retr_flows).reset_index(drop=True)
                                df_retr_merged_sum = df_retr_merged.sum(axis=1)
                                df_delay_merged = pd.concat(delay_flows).reset_index(drop=True)
                                df_delay_merged_mean = df_delay_merged.mean(axis=1)

                                efficiency_metric1 = (
                                    (df_merged_sum / BW)
                                    / (df_delay_merged_mean / (2 * delay))
                                )
                                efficiency_metric2 = (
                                    ((df_merged_sum / BW) - (df_retr_merged_sum / BW))
                                    / (df_delay_merged_mean / (2 * delay))
                                )

                                efficiency_fairness_data.append([
                                    aqm, qmult, delay, BW, protocol, run,
                                    df_delay_merged_mean.mean(),
                                    df_merged_sum.mean(),
                                    df_merged_sum.std(),
                                    df_merged_ratio.mean(),
                                    df_merged_ratio.std(),
                                    df_retr_merged_sum.mean(),
                                    df_retr_merged_sum.std(),
                                    efficiency_metric1.mean(),
                                    efficiency_metric1.std(),
                                    efficiency_metric2.mean(),
                                    efficiency_metric2.std(),
                                    util_mean, util_std
                                ])

    COLUMNS1 = [
        'aqm', 'qmult', 'min_delay', 'bandwidth', 'protocol', 'run', 'flow',
        'goodput_mean', 'goodput_std', 'delay_mean', 'delay_std',
        'retr_mean', 'retr_std', 'util_mean', 'util_std'
    ]
    COLUMNS2 = [
        'aqm', 'qmult', 'min_delay', 'bandwidth', 'protocol', 'run',
        'delay_mean', 'efficiency_mean', 'efficiency_std',
        'fairness_mean', 'fairness_std',
        'retr_mean', 'retr_std',
        'efficiency1_mean', 'efficiency1_std',
        'efficiency2_mean', 'efficiency2_std',
        'util_mean', 'util_std'
    ]
    return pd.DataFrame(data, columns=COLUMNS1), pd.DataFrame(efficiency_fairness_data, columns=COLUMNS2)

def plot_data(data, filename, ylim=None):
    COLOR = {
        'cubic': '#0C5DA5',
        'bbr1': '#00B945',
        'bbr3': '#FF9500',
        'sage': '#FF2C01',
        'vivace': '#845B97',
        'astraea': '#686868'
    }
    LINEWIDTH = 1
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(4, 3), sharex=True, sharey=True)
    for i, protocol in enumerate(PROTOCOLS):
        ax = axes[i]
        for n in range(4):
            ax.plot(
                data['fifo'][protocol][n + 1].index,
                data['fifo'][protocol][n + 1]['mean'],
                linewidth=LINEWIDTH, label=protocol
            )
            try:
                ax.fill_between(
                    data['fifo'][protocol][n + 1].index,
                    data['fifo'][protocol][n + 1]['mean']
                    - data['fifo'][protocol][n + 1]['std'],
                    data['fifo'][protocol][n + 1]['mean']
                    + data['fifo'][protocol][n + 1]['std'],
                    alpha=0.2
                )
            except:
                print('Protocol: %s' % protocol)
        if ylim:
            ax.set(ylim=ylim)
        if i == 2:
            ax.set(xlabel='time (s)')
        ax.text(70, 1.8, '%s' % protocol, va='center', c=COLOR[protocol])
        ax.grid()
    plt.savefig(filename, dpi=720)

if __name__ == "__main__":
    # Update for parking lot topology:
    ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_parking_lot"
    PROTOCOLS = ['cubic', 'bbr3', 'bbr1', 'sage', 'astraea']
    DELAYS = [20, 50]  # Only look at delays 20 and 50
    RUNS = [1, 2, 3, 4, 5]
    QMULTS = [0.2, 1, 4]
    AQM_LIST = ['fifo']

    # 1) Generate data and save CSVs
    df1, df2 = data_to_df(ROOT_PATH, DELAYS, [100], QMULTS, AQM_LIST, PROTOCOLS)
    df1.to_csv('aqm_data.csv', index=False)
    df2.to_csv('aqm_efficiency_fairness.csv', index=False)

    # 2) Load efficiency & fairness data
    df = pd.read_csv('aqm_efficiency_fairness.csv').dropna()
    # Only keep the FIFO data
    df = df[df['aqm'] == 'fifo']

    # -------------------------------------------------------------
    # 3) Fix the aggregator so we take the AVERAGE of 'util_mean'
    #    across runs (rather than sum).
    # -------------------------------------------------------------
    # Rename 'util_mean' to something we can interpret more clearly:
    df['util_avg'] = df['util_mean']

    # Group by min_delay, qmult, protocol => average across runs
    df_agg = df.groupby(['min_delay', 'qmult', 'protocol'], as_index=False).agg({
        'util_avg': 'mean',      # <-- AVERAGE across runs
        'delay_mean': 'mean',    # average delay across runs
        'retr_mean': 'mean',     # average retrans across runs
        'run': 'nunique'         # how many runs were present
    })

    # Set a multi-index for easy .loc[...] usage
    df_agg.set_index(['min_delay', 'qmult', 'protocol'], inplace=True)
    data = df_agg

    # -------------------------------------------------------------------
    # 4) Generate scatter plots: normalizing throughput by /100 in the plot
    #    to get the final "normalized throughput" the way you requested.
    # -------------------------------------------------------------------
    COLOR_MAP = {
        'cubic': '#0C5DA5',
        'bbr1': '#00B945',
        'bbr3': '#FF9500',
        'sage': '#FF2C01',
        'vivace': '#845B97',
        'astraea': '#686868'
    }
    MARKER_MAP = {20: '^', 50: '*'}

    def confidence_ellipse(x, y, ax, n_std=1.0, facecolor='none', **kwargs):
        if x.size != y.size:
            raise ValueError("x and y must be the same size")
        cov = np.cov(x, y)
        pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
        ell_radius_x = np.sqrt(1 + pearson)
        ell_radius_y = np.sqrt(1 - pearson)
        ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                          facecolor=facecolor, **kwargs)
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

    for CONTROL_VAR in [0.2, 1, 4]:
        fig, axes = plt.subplots(figsize=(4, 2))
        for protocol in PROTOCOLS:
            for delay in DELAYS:
                pt = data.loc[delay, CONTROL_VAR, protocol]

                # We'll use (pt['util_avg'] / 100) to "normalize" by 100
                # as you requested. Similarly subtract (retr_mean / 100) if needed.
                # (If your logic is "throughput in Mbps / 100" => dimensionless ~ 'units of 100 Mbps')
                axes.scatter(
                    pt['delay_mean'] / (delay * 2),
                    pt['util_avg'] / 100 - (pt['retr_mean'] / 100),
                    edgecolors=COLOR_MAP[protocol],
                    marker=MARKER_MAP[delay],
                    facecolors='none',
                    alpha=0.25
                )
                axes.scatter(
                    pt['delay_mean'] / (delay * 2),
                    pt['util_avg'] / 100,
                    edgecolors=COLOR_MAP[protocol],
                    marker=MARKER_MAP[delay],
                    facecolors='none',
                    label='%s-%s' % (protocol, delay * 2)
                )

                # Confidence ellipse if multiple runs
                subset = df[
                    (df['protocol'] == protocol)
                    & (df['qmult'] == CONTROL_VAR)
                    & (df['min_delay'] == delay)
                ]
                if len(subset) > 1:
                    x = subset['delay_mean'].values / (delay * 2)
                    y = subset['util_avg'].values / 100
                    confidence_ellipse(
                        x, y, axes,
                        facecolor=COLOR_MAP[protocol],
                        edgecolor='none', alpha=0.25
                    )

        handles, labels = axes.get_legend_handles_labels()
        fig.legend(
            handles[:-2], labels[:-2],
            loc='upper center', bbox_to_anchor=(0.5, 1.25),
            ncol=4, columnspacing=0.7, handletextpad=0.7
        )
        fig.legend(
            handles[-2:], labels[-2:],
            loc='upper center', bbox_to_anchor=(0.5, 1.05),
            ncol=2, columnspacing=0.7, handletextpad=0.7
        )

        axes.set(
            ylabel="Norm. Throughput",
            xlabel="Norm. Delay",
            ylim=[0, None]
        )
        axes.invert_xaxis()

        for fmt in ['pdf']:
            plt.savefig(f'{CONTROL_VAR}qmult_scatter_corrected.{fmt}', dpi=1080)
        plt.close(fig)
