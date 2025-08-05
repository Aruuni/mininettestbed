import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import os, sys
import matplotlib as mpl
mpl.rcParams['agg.path.chunksize'] = 10000
pd.set_option('display.max_rows', None)
import numpy as np
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms
from matplotlib.lines import Line2D

plt.rcParams['text.usetex'] = True

# Ensure module path
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)
from core.config import *
from core.plotting import *

# Config
NUM_FLOWS    = 5
METRIC_START = 105
METRIC_END   = 125


def confidence_ellipse(x, y, ax, n_std=1.0, facecolor='none', **kwargs):
    cov = np.cov(x, y)
    pearson = cov[0,1] / np.sqrt(cov[0,0] * cov[1,1])
    rx, ry = np.sqrt(1 + pearson), np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0), width=2*rx, height=2*ry, facecolor=facecolor, **kwargs)
    sx, sy = np.sqrt(cov[0,0])*n_std, np.sqrt(cov[1,1])*n_std
    mx, my = np.mean(x), np.mean(y)
    transf = transforms.Affine2D().rotate_deg(45).scale(sx, sy).translate(mx, my)
    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


def data_to_efficiency_df(folder, delays, bandwidths, qmults, aqms, protocols):
    """
    Returns raw per-run metrics:
      - raw_delay: mean RTT (same units as srtt)
      - raw_goodput: aggregate goodput (Mbps)
      - raw_ret: mean retransmission rate (Mbps) [kept for debugging]
    """
    rows = []
    for aqm in aqms:
        for q in qmults:
            for d in delays:
                for bw in bandwidths:
                    BDP = int(bw * (2**20) * 2 * d * 1e-3 / 8) / 1500
                    for proto in protocols:
                        runs_raw_delay, runs_raw_goodput, runs_raw_ret = [], [], []
                        for run in RUNS:
                            base = f"{folder}/{aqm}/Dumbell_{bw}mbit_{d}ms_{int(q*BDP)}pkts_0loss_{NUM_FLOWS}flows_22tcpbuf_{proto}/run{run}"
                            flows, delays_ts, rets = [], [], []

                            for n in range(NUM_FLOWS):
                                # throughput samples
                                rx = f"{base}/csvs/x{n+1}.csv"
                                if os.path.exists(rx):
                                    df_rx = pd.read_csv(rx)[['time','bandwidth']]
                                    df_rx['time'] = df_rx['time'].astype(int)
                                    df_rx = df_rx[(df_rx.time>=METRIC_START)&(df_rx.time<=METRIC_END)]\
                                                .drop_duplicates('time').set_index('time')
                                    flows.append(df_rx['bandwidth'])
                                # RTT samples
                                snd = f"{base}/csvs/c{n+1}{'_ss' if proto not in ['vivace-uspace','astraea'] else ''}.csv"
                                if os.path.exists(snd):
                                    df_s = pd.read_csv(snd)[['time','srtt']]
                                    df_s['time'] = df_s['time'].astype(int)
                                    df_s = df_s[(df_s.time>=METRIC_START)&(df_s.time<=METRIC_END)]
                                    df_s = df_s.groupby('time').mean()['srtt']
                                    delays_ts.append(df_s)
                                # retransmissions (still loaded but not used in plot)
                                log_r = f"{base}/sysstat/etcp_c{n+1}.log"
                                if os.path.exists(log_r) and proto!='vivace-uspace':
                                    try:
                                        df_r = pd.read_csv(log_r, sep=';')
                                    except (pd.errors.EmptyDataError, pd.errors.ParserError):
                                        continue
                                    df_r['time'] = (df_r['timestamp'] - df_r['timestamp'].iloc[0] + 1).astype(int)
                                    df_r = df_r[(df_r.time>=METRIC_START)&(df_r.time<=METRIC_END)]\
                                                .drop_duplicates('time').set_index('time')
                                    rets.append(df_r['retrans/s'] * 1500 * 8 / 1e6)
                                elif os.path.exists(snd) and proto=='vivace-uspace':
                                    try:
                                        df_r = pd.read_csv(snd).rename(columns={'retr':'retrans/s'})
                                    except (pd.errors.EmptyDataError, pd.errors.ParserError):
                                        continue
                                    df_r['time'] = df_r['time'].astype(int)
                                    df_r = df_r[(df_r.time>=METRIC_START)&(df_r.time<=METRIC_END)]\
                                                .drop_duplicates('time').set_index('time')
                                    rets.append(df_r['retrans/s'] * 1500 * 8 / 1e6)

                            if flows and delays_ts:
                                agg_goodput = pd.concat(flows, axis=1).sum(axis=1).mean()
                                mean_delay = pd.concat(delays_ts, axis=1).mean(axis=1).mean()
                                mean_ret = pd.concat(rets, axis=1).sum(axis=1).mean() if rets else 0
                                runs_raw_delay.append(mean_delay)
                                runs_raw_goodput.append(agg_goodput)
                                runs_raw_ret.append(mean_ret)
                        if runs_raw_delay:
                            rows.append({
                                'aqm':aqm, 'delay':d, 'qmult':q, 'bandwidth':bw, 'protocol':proto,
                                'runs_raw_delay': runs_raw_delay,
                                'runs_raw_goodput': runs_raw_goodput,
                                'runs_raw_ret':   runs_raw_ret
                            })
    return pd.DataFrame(rows)


if __name__=='__main__':
    EXP = f"{HOME_DIR}/cctestbed/mininet/results_efficiency_aqm"
    DELAYS = [25]
    BWS    = [100]
    AQMS   = ['fifo','fq_codel','fq_pie','cake']
    QMULTS = [1]
    PROTOCOLS = PROTOCOLS_LEO

    df = data_to_efficiency_df(EXP, DELAYS, BWS, QMULTS, AQMS, PROTOCOLS)
    if df.empty:
        print("No data found")
        sys.exit(1)
    print(df)

    # Plot: normalized scatter
    MARKER = {'fifo':'o','fq_codel':'^','fq_pie':'P','cake':'X'}
    fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(3, 1.2))
    ax = axes
    for proto in PROTOCOLS:
        for aqm in AQMS:
            sub = df[(df.protocol==proto)&(df.aqm==aqm)]
            if sub.empty: 
                continue

            d = sub.delay.values[0]
            run_d = np.array(sub.runs_raw_delay.iloc[0])
            run_g = np.array(sub.runs_raw_goodput.iloc[0])  # aggregate goodput only

            # normalize per-run
            x_runs = run_d / (2 * d)
            goodput_runs = run_g / 100.0  # normalized goodput

            # mean normalized
            x = x_runs.mean()
            goodput = goodput_runs.mean()

            # plot only goodput (no retransmission subtraction)
            ax.scatter(x, goodput, marker=MARKER[aqm], s=20,
                       edgecolors=COLORS_LEO[proto], facecolors='none', linewidth=0.6, zorder=2)

            # ellipse for goodput variation
            if len(x_runs) > 1:
                confidence_ellipse(x_runs, goodput_runs, ax,
                                   facecolor=COLORS_LEO[proto], alpha=0.2)

    ax.set(xlabel='Normalised Delay', ylabel='Norm. Agg. Goodput', ylim=(0.8,1.0), xlim=(1,2.05))
    # AQM legend
    handles = [Line2D([],[], marker=MARKER[a], linestyle='None', markerfacecolor='none',
                       markeredgecolor='black', label=AQM_FRIENDLY_NAME[a]) for a in AQMS]
    ax.legend(handles, [AQM_FRIENDLY_NAME[a] for a in AQMS],
              loc='best', ncol=4, fontsize=5, columnspacing=0.5, handletextpad=0.2, frameon=False, markerscale=0.9)
    ax.yaxis.label.set_size(8)  # or whatever size you like
    ax.invert_xaxis()
    plt.savefig('aqm_eff_scatter.pdf', dpi=1080)
