import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scienceplots

# Setup paths from core.config
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)
from core.config import *  # HOME_DIR should be defined here

plt.style.use("science")
plt.rcParams["text.usetex"] = False
plt.rcParams["font.size"] = 9

# Root path for data
ROOT_PATH = os.path.join(HOME_DIR, "cctestbed/mininet/results_parking_lot/fifo")

# Protocols and their colors (used for label text)
PROTOCOLS = ["cubic", "bbr1", "bbr3", "astraea", "sage"]
COLOR_MAP = {
    "cubic":   "#0C5DA5",
    "bbr1":    "#00B945",
    "bbr3":    "#FF9500",
    "astraea": "#686868",
    "sage":    "#FF2C01",
}
# List of flow identifiers (extendable as needed)
FLOWS = ["x1", "x2", "x3", "x4"]

def plot_one(qmult, run, num_flows=4):
    """Plot goodput (bandwidth) vs. time for each protocol in stacked subplots for a single run."""
    BW    = 100  # in Mbit
    DELAY = 40   # in ms
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * 1e-3 / 8)
    BDP_IN_PKTS  = BDP_IN_BYTES / 1500
    folder_pkts  = int(qmult * BDP_IN_PKTS)
    TIME_RANGE = (DELAY * 2, DELAY * 4)

    fig, axes = plt.subplots(nrows=len(PROTOCOLS), ncols=1, figsize=(4, 3), sharex=True)
    plt.subplots_adjust(hspace=0.05)

    for i, proto in enumerate(PROTOCOLS):
        ax = axes[i]
        path = os.path.join(
            ROOT_PATH,
            f"ParkingLot_{BW}mbit_{DELAY}ms_{folder_pkts}pkts_0loss_{num_flows}flows_22tcpbuf_{proto}",
            f"run{run}"
        )
        if not os.path.isdir(path):
            print(f"[WARNING] Directory not found: {path}")
            continue

        plotted = False
        for flow in FLOWS:
            csv_file = os.path.join(path, "csvs", f"{flow}.csv")
            if not os.path.isfile(csv_file):
                print(f"[WARNING] File not found: {csv_file}")
                continue

            df = pd.read_csv(csv_file)
            if "time" not in df.columns or "bandwidth" not in df.columns:
                print(f"[WARNING] Missing 'time' or 'bandwidth' in {csv_file}")
                continue

            df = df[(df["time"] >= TIME_RANGE[0]) & (df["time"] <= TIME_RANGE[1])]
            if df.empty:
                print(f"[INFO] No data in time range for {csv_file}")
                continue

            ax.plot(df["time"], df["bandwidth"], label=flow, linewidth=1.0)
            plotted = True

        ax.set_xlim(TIME_RANGE)
        ax.grid(True, linestyle=":")

        if plotted:
            ax.text(
                0.02, 0.8, proto,
                transform=ax.transAxes,
                color=COLOR_MAP.get(proto, "black"),
                fontsize=10,
                weight="bold",
                ha="left",
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none")
            )
        else:
            ax.set_title(proto, fontsize=10, color=COLOR_MAP.get(proto, "black"))

        if proto == "bbr3":
            ax.set_ylabel("Goodput (Mbps)")
        else:
            ax.set_ylabel("")

    axes[-1].set_xlabel("Time (s)")

    outfile = f"goodput_{TIME_RANGE[0]}_{TIME_RANGE[1]}_qmult_{qmult}_run{run}.pdf"
    plt.savefig(outfile, dpi=300)
    plt.close()
    print(f"[INFO] Saved figure to {outfile}")

def plot_average(qmult, num_runs=5, num_flows=4, share_y_lim=True, shade_alpha=0.4):
    """Plot average goodput vs. time across multiple runs with shaded error bands."""
    BW    = 100  # in Mbit
    DELAY = 40   # in ms
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * 1e-3 / 8)
    BDP_IN_PKTS  = BDP_IN_BYTES / 1500
    folder_pkts  = int(qmult * BDP_IN_PKTS)
    TIME_RANGE = (DELAY * 2, DELAY * 4)

    fig, axes = plt.subplots(nrows=len(PROTOCOLS), ncols=1, figsize=(4, 3), sharex=True)
    plt.subplots_adjust(hspace=0.05)
    
    max_global_y = 0

    for i, proto in enumerate(PROTOCOLS):
        ax = axes[i]
        for flow in FLOWS:
            runs_data = []
            for run in range(1, num_runs + 1):
                path = os.path.join(
                    ROOT_PATH,
                    f"ParkingLot_{BW}mbit_{DELAY}ms_{folder_pkts}pkts_0loss_{num_flows}flows_22tcpbuf_{proto}",
                    f"run{run}"
                )
                csv_file = os.path.join(path, "csvs", f"{flow}.csv")
                if not os.path.isfile(csv_file):
                    print(f"[WARNING] File not found: {csv_file}")
                    continue

                df = pd.read_csv(csv_file)
                if "time" not in df.columns or "bandwidth" not in df.columns:
                    print(f"[WARNING] Missing 'time' or 'bandwidth' in {csv_file}")
                    continue

                df = df[(df["time"] >= TIME_RANGE[0]) & (df["time"] <= TIME_RANGE[1])]
                if df.empty:
                    print(f"[INFO] No data in time range for {csv_file}")
                    continue

                df = df.sort_values("time")
                runs_data.append(df)

            if not runs_data:
                continue

            t_ref = runs_data[0]["time"].values
            bw_runs = []
            for df in runs_data:
                t = df["time"].values
                bw = df["bandwidth"].values
                if len(t) != len(t_ref) or not np.allclose(t, t_ref):
                    bw_interp = np.interp(t_ref, t, bw)
                    bw_runs.append(bw_interp)
                else:
                    bw_runs.append(bw)
            bw_runs = np.array(bw_runs)

            mean_bw = np.mean(bw_runs, axis=0)
            std_bw  = np.std(bw_runs, axis=0)

            ax.plot(t_ref, mean_bw, label=flow, linewidth=1.0)
            ax.fill_between(t_ref, mean_bw - std_bw, mean_bw + std_bw, alpha=shade_alpha)
            
            current_max = (mean_bw + std_bw).max()
            if current_max > max_global_y:
                max_global_y = current_max

        ax.set_xlim(TIME_RANGE)
        ax.grid(True, linestyle=":")
        ax.text(
            0.02, 0.8, proto,
            transform=ax.transAxes,
            color=COLOR_MAP.get(proto, "black"),
            fontsize=10,
            weight="bold",
            ha="left",
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none")
        )
        if proto == "bbr3":
            ax.set_ylabel("Goodput (Mbps)")
        else:
            ax.set_ylabel("")

    axes[-1].set_xlabel("Time (s)")

    if share_y_lim:
        global_max = max(100, max_global_y)
        margin = global_max * 0.05
        for ax in axes:
            ax.set_ylim(0, global_max + margin)

    outfile = f"goodput_average_{TIME_RANGE[0]}_{TIME_RANGE[1]}_qmult_{qmult}.pdf"
    plt.savefig(outfile, dpi=300)
    plt.close()
    print(f"[INFO] Saved average figure to {outfile}")

def plot_cwnd(qmult, run, num_flows=4):
    """
    Plot the congestion window (cwnd) vs. time for each protocol in stacked subplots for a single run.
    
    For every protocol, the cwnd data for each flow is assumed to be stored as follows:
      - For astraea:  csvs/c{flow_number}.csv  (e.g., c1.csv, c2.csv, ...)
      - For other protocols: csvs/c{flow_number}_ss.csv (e.g., c1_ss.csv, c2_ss.csv, ...)
    
    The flow lines are plotted using the default color cycle, while the protocol label text uses the
    protocol's designated color.
    """
    BW    = 100  # in Mbit
    DELAY = 40   # in ms
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * 1e-3 / 8)
    BDP_IN_PKTS  = BDP_IN_BYTES / 1500
    folder_pkts  = int(qmult * BDP_IN_PKTS)
    TIME_RANGE = (DELAY * 2, DELAY * 4)

    fig, axes = plt.subplots(nrows=len(PROTOCOLS), ncols=1, figsize=(4, 3), sharex=True)
    plt.subplots_adjust(hspace=0.05)

    for i, proto in enumerate(PROTOCOLS):
        ax = axes[i]
        path = os.path.join(
            ROOT_PATH,
            f"ParkingLot_{BW}mbit_{DELAY}ms_{folder_pkts}pkts_0loss_{num_flows}flows_22tcpbuf_{proto}",
            f"run{run}"
        )
        if not os.path.isdir(path):
            print(f"[WARNING] Directory not found: {path}")
            continue

        found_any = False
        for flow in FLOWS:
            flow_num = flow[1:]  # e.g., "x1" -> "1"
            if proto == "astraea":
                cwnd_file = os.path.join(path, "csvs", f"c{flow_num}.csv")
            else:
                cwnd_file = os.path.join(path, "csvs", f"c{flow_num}_ss.csv")
            if not os.path.isfile(cwnd_file):
                print(f"[WARNING] File not found: {cwnd_file}")
                continue

            df = pd.read_csv(cwnd_file)
            if "time" not in df.columns or "cwnd" not in df.columns:
                print(f"[WARNING] Missing 'time' or 'cwnd' in {cwnd_file}")
                continue

            df = df[(df["time"] >= TIME_RANGE[0]) & (df["time"] <= TIME_RANGE[1])]
            if df.empty:
                print(f"[INFO] No data in time range for {cwnd_file}")
                continue

            # Plot using default color (by omitting the "color" parameter)
            ax.step(df["time"], df["cwnd"], where="post",
                    label=flow, linewidth=1.0)
            found_any = True

        if not found_any:
            print(f"[WARNING] No cwnd data found in {path}")

        ax.set_xlim(TIME_RANGE)
        ax.grid(True, linestyle=":")

        ax.text(
            0.02, 0.8, proto,
            transform=ax.transAxes,
            color=COLOR_MAP.get(proto, "black"),
            fontsize=10,
            weight="bold",
            ha="left",
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none")
        )

        if proto == "bbr3":
            ax.set_ylabel("cwnd (packets)")
        else:
            ax.set_ylabel("")

    axes[-1].set_xlabel("Time (s)")

    outfile = f"cwnd_{TIME_RANGE[0]}_{TIME_RANGE[1]}_qmult_{qmult}_run{run}.pdf"
    plt.savefig(outfile, dpi=300)
    plt.close()
    print(f"[INFO] Saved cwnd figure to {outfile}")

if __name__ == "__main__":
    # Example: Plot the average goodput (across 5 runs) for each qmult.
    # for mult in [0.2, 1, 4]:
    #     plot_average(mult, num_runs=5, num_flows=4, share_y_lim=True, shade_alpha=0.2)
    
    # Plot the cwnd for a single run (e.g., run 1) for each qmult.
    for mult in [0.2, 1, 4]:
        plot_cwnd(mult, run=2, num_flows=4)
