import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import scienceplots

# Setup paths from core.config
script_dir    = os.path.dirname(__file__)
mymodule_dir  = os.path.join(script_dir, "../../..")
sys.path.append(mymodule_dir)
from core.config import *  # HOME_DIR should be defined here

plt.style.use("science")
plt.rcParams["text.usetex"] = False
plt.rcParams["font.size"]   = 9

# Root path for ParkingLot data
ROOT_PATH = os.path.join(HOME_DIR, "cctestbed/mininet/results_parking_lot/fifo")

PROTOCOLS = ["cubic", "bbr1", "bbr3", "astraea", "sage"]
FLOWS     = ["x1", "x2", "x3", "x4"]

def get_goodput_data(BW, DELAY, qmult, runs, num_flows=4):
    """
    For each protocol & flow, read data from multiple runs, align them by time,
    and compute mean & std of the 'bandwidth' column. Return a nested dictionary:
      goodput_data[protocol][flow] -> DataFrame with index=time, columns=['mean','std'].
    """
    # Compute the BDP-based folder naming
    BDP_IN_BYTES = int(BW * (2**20) * 2 * DELAY * (10**-3) / 8)
    BDP_IN_PKTS  = BDP_IN_BYTES / 1500
    folder_pkts  = int(qmult * BDP_IN_PKTS)

    # Data structure to store results
    goodput_data = {
        proto: {flow: pd.DataFrame() for flow in FLOWS}
        for proto in PROTOCOLS
    }

    for proto in PROTOCOLS:
        for flow in FLOWS:
            df_list = []  # holds one DataFrame per run

            for run in runs:
                path = os.path.join(
                    ROOT_PATH,
                    f"ParkingLot_{BW}mbit_{DELAY}ms_{folder_pkts}pkts_0loss_{num_flows}flows_22tcpbuf_{proto}",
                    f"run{run}",
                    "csvs"
                )
                csv_file = os.path.join(path, f"{flow}.csv")
                if not os.path.isfile(csv_file):
                    print(f"[WARNING] Missing file: {csv_file}")
                    continue

                tmp = pd.read_csv(csv_file)
                if "time" not in tmp.columns or "bandwidth" not in tmp.columns:
                    print(f"[WARNING] Missing 'time'/'bandwidth' in {csv_file}")
                    continue

                # Use time as the index
                tmp = tmp[["time", "bandwidth"]].copy().set_index("time")
                # Keep a consistent name for the column from this run
                tmp.columns = [f"run{run}"]
                df_list.append(tmp)

            if not df_list:
                # No data for this flow/protocol across all runs
                continue

            # Merge all runs on the time index (outer join to keep all time points)
            df_merged = pd.concat(df_list, axis=1, join="outer").sort_index()
            # If time points differ slightly among runs, you can optionally:
            # df_merged.interpolate(method="linear", inplace=True)
            # df_merged.dropna(inplace=True)

            if df_merged.empty:
                continue

            # Compute mean and std across the run columns
            df_merged["mean"] = df_merged.mean(axis=1)
            df_merged["std"]  = df_merged.std(axis=1)

            # Store only [mean, std] in final data structure
            goodput_data[proto][flow] = df_merged[["mean", "std"]].copy()

    return goodput_data
