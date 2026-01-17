#!/usr/bin/env python3
import os, sys, glob
import numpy as np
import pandas as pd

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

import scienceplots
plt.style.use('science')
plt.rcParams['text.usetex'] = True

# --------- Project imports ---------
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)

from core.config import *      # PROTOCOLS_EXTENSION, PROTOCOLS_MARKERS_EXTENSION, COLORS_EXTENSION, PROTOCOLS_FRIENDLY_NAMES, HOME_DIR, etc.
from core.plotting import *    # plot_points

# --------- Experiment configuration ---------
EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/gauntlet/results_fairness_intra_rtt/fifo"

BWS    = [100]
DELAYS = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200]   # ms
QMULTS = [0.2, 1, 4]
RUNS   = list(range(1, 6))

# optional: slightly bigger fonts
mpl.rcParams.update({
    "figure.figsize": (6.0, 1.6),
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7,
})

def load_goodput_and_rtt_ratios_for_run(csv_dir: str, protocol: str, delay_ms: int):
    """
    Mirror the logic from your new script:
      - pick latest x1/x2 + c1/c2 files
      - time in integer seconds
      - steady-state window: (3*delay, 4*delay-1]
      - goodput ratio = min(bw1,bw2)/max(bw1,bw2) (skip where both zero)
      - RTT ratio     = average( srtt1/delay, srtt2/delay )
    Returns (goodput_ratio_array, rtt_ratio_array) or (None, None) if invalid.
    """
    if not os.path.isdir(csv_dir):
        print(f"CSV dir not found: {csv_dir}")
        return None, None

    # --- pick files ---
    x1_files = glob.glob(os.path.join(csv_dir, "x1*.csv"))
    x2_files = glob.glob(os.path.join(csv_dir, "x2*.csv"))

    if protocol in ("vivace-uspace", "astraea"):
        c1_pattern = "c1*.csv"
        c2_pattern = "c2*.csv"
    else:
        c1_pattern = "c1*_ss.csv"
        c2_pattern = "c2*_ss.csv"

    c1_files = glob.glob(os.path.join(csv_dir, c1_pattern))
    c2_files = glob.glob(os.path.join(csv_dir, c2_pattern))

    if not (x1_files and x2_files and c1_files and c2_files):
        print(f"Missing x/c files in {csv_dir}")
        return None, None

    x1_path = x1_files[0]
    x2_path = x2_files[0]
    c1_path = c1_files[0]
    c2_path = c2_files[0]

    # --- load ---
    r1g = pd.read_csv(x1_path).reset_index(drop=True)
    r2g = pd.read_csv(x2_path).reset_index(drop=True)
    r1s = pd.read_csv(c1_path).reset_index(drop=True)
    r2s = pd.read_csv(c2_path).reset_index(drop=True)

    # integer-second time
    for df in (r1g, r2g, r1s, r2s):
        df['time'] = df['time'].apply(lambda x: int(float(x)))

    # steady-state window (matches your new script)
    start_time = 3 * delay_ms
    end_time   = 4 * delay_ms - 1

    def window(df):
        return (df[(df['time'] > start_time) & (df['time'] <= end_time)]
                .drop_duplicates('time')
                .set_index('time'))

    r1g = window(r1g)
    r2g = window(r2g)
    r1s = window(r1s)
    r2s = window(r2s)

    # align common times
    times = r1g.index.intersection(r2g.index).intersection(r1s.index).intersection(r2s.index)
    if len(times) == 0:
        return None, None

    r1g = r1g.loc[times]
    r2g = r2g.loc[times]
    r1s = r1s.loc[times]
    r2s = r2s.loc[times]

    # filter out timestamps where both throughputs are zero or missing
    bw1 = r1g['bandwidth']
    bw2 = r2g['bandwidth']
    both_zero = (bw1 <= 0) & (bw2 <= 0)
    mask = ~both_zero

    if not mask.any():
        return None, None

    # goodput ratio
    goodput_ratio = (np.minimum(bw1, bw2) / np.maximum(bw1, bw2))[mask]

    # RTT ratio: NOTE: srtt / delay (no 2×)
    delay = float(delay_ms)
    rtt_ratio = (((r1s['srtt'] / delay) + (r2s['srtt'] / delay)) / 2.0)[mask]

    if goodput_ratio.empty or rtt_ratio.empty:
        return None, None

    return goodput_ratio.values, rtt_ratio.values


def main():
    for mult in QMULTS:
        data_rows = []

        for protocol in PROTOCOLS_EXTENSION:
            for bw in BWS:
                for delay in DELAYS:
                    # BDP & queue sizing as before
                    BDP_IN_BYTES = int(bw * (2 ** 20) * delay * (10 ** -3) / 8)
                    BDP_IN_PKTS  = BDP_IN_BYTES / 1500.0

                    goodput_samples = []
                    rtt_ratio_samples = []

                    for run in RUNS:
                        csv_dir = (
                            f"{EXPERIMENT_PATH}/"
                            f"Dumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_{protocol}/"
                            f"run{run}/csvs"
                        )

                        g, rtt = load_goodput_and_rtt_ratios_for_run(csv_dir, protocol, delay)
                        if g is None or rtt is None:
                            continue

                        goodput_samples.append(g)
                        rtt_ratio_samples.append(rtt)

                    if len(goodput_samples) == 0:
                        continue

                    goodput_samples = np.concatenate(goodput_samples, axis=0)
                    rtt_ratio_samples = np.concatenate(rtt_ratio_samples, axis=0)

                    row = [
                        protocol,
                        bw,
                        delay,
                        delay / 10.0,                       # your old "delay_ratio" param; kept for compatibility
                        mult,
                        goodput_samples.mean(),
                        goodput_samples.std(),
                        rtt_ratio_samples.mean(),
                        rtt_ratio_samples.std(),
                    ]
                    data_rows.append(row)

        summary_data = pd.DataFrame(
            data_rows,
            columns=[
                'protocol', 'bandwidth', 'delay', 'delay_ratio', 'qmult',
                'goodput_ratio_total_mean', 'goodput_ratio_total_std',
                'rtt_ratio_mean', 'rtt_ratio_std'
            ]
        )
        print(f"\n=== qmult={mult} ===")
        print(summary_data)

        # --------- Plot: goodput ratio + RTT ratio side-by-side ---------
        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(6, 1.6))
        ax_g, ax_rtt = axes

        for protocol in PROTOCOLS_EXTENSION:
            df_p = summary_data[summary_data['protocol'] == protocol]
            if df_p.empty:
                continue
            df_p = df_p.set_index('delay')

            # Goodput ratio
            plot_points(
                ax_g,
                df_p,
                'goodput_ratio_total_mean',
                'goodput_ratio_total_std',
                PROTOCOLS_MARKERS_EXTENSION[protocol],
                COLORS_EXTENSION[protocol],
                PROTOCOLS_FRIENDLY_NAMES[protocol],
                delay=True
            )

            # RTT ratio (srtt / delay)
            plot_points(
                ax_rtt,
                df_p,
                'rtt_ratio_mean',
                'rtt_ratio_std',
                PROTOCOLS_MARKERS_EXTENSION[protocol],
                COLORS_EXTENSION[protocol],
                PROTOCOLS_FRIENDLY_NAMES[protocol],
                delay=True
            )

        # Axis formatting
        ax_g.set(
            yscale='linear',
            xlabel='RTT (ms)',
            ylabel='Goodput Ratio',
            ylim=[-0.1, 1.1],
            title='Goodput Ratio (min/max)'
        )
        ax_rtt.set(
            yscale='linear',
            xlabel='RTT (ms)',
            ylabel='RTT Ratio (srtt / delay)',
            title='RTT Ratio'
        )

        # keep x-axis labels nice
        ax_g.xaxis.set_major_formatter(ScalarFormatter())
        ax_rtt.xaxis.set_major_formatter(ScalarFormatter())

        # optional: shared legend above both plots
        handles, labels = ax_g.get_legend_handles_labels()
        handles = [h[0] for h in handles] if handles and hasattr(handles[0], '__getitem__') else handles
        if handles:
            fig.legend(
                handles, labels,
                ncol=min(3, len(handles)),
                loc='upper center',
                bbox_to_anchor=(0.5, 1.25),
                columnspacing=0.8,
                handletextpad=0.5
            )

        fig.tight_layout()
        plt.savefig(f"goodput_and_rtt_intra_rtt_qmult{mult}_neww.pdf", dpi=1080, bbox_inches='tight')
        plt.close(fig)


if __name__ == "__main__":
    main()
