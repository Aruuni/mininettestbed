import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import scienceplots

script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, "../../..")
sys.path.append(mymodule_dir)
from core.config import *
from core.plotting import * 
plt.style.use("science")
plt.rcParams["text.usetex"] = False
plt.rcParams["font.size"]   = 11

# Root path for ParkingLot data
FLOWS = ["x1", "x2", "x3", "x4"]

def get_goodput_data(bw, delay, qmult, runs, aqm, num_flows=4):

    goodput_data = {
        protocol: {
            flow: pd.DataFrame(columns=['time', 'mean', 'std'])
            for flow in FLOWS
        }
        for protocol in PROTOCOLS_LEO
    }
    start_time = 0
    end_time = 100
    for protocol in PROTOCOLS_LEO:
        BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
        BDP_IN_PKTS = BDP_IN_BYTES / 1500
        senders = {1: [], 2: [], 3: [], 4: []}
        receivers = {1: [], 2: [], 3: [], 4: []}
        for run in RUNS:
           PATH = f"{EXPERIMENT_PATH}/{aqm}/Dumbell_{bw}mbit_{delay}ms_{int(qmult * BDP_IN_PKTS)}pkts_0loss_{4}flows_22tcpbuf_{protocol}/run{run}"
           for n in range(4):
              csv_path = f"{PATH}/csvs/x{n+1}.csv"
              if os.path.exists(csv_path):
                 receiver_total = pd.read_csv(csv_path).reset_index(drop=True)
                 receiver_total = receiver_total[['time', 'bandwidth']]
                 receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))
                 # Filter time range per flow
                 receiver_total = receiver_total[(receiver_total['time'] >= (start_time + n*25)) & (receiver_total['time'] <= (end_time + n*25))]
                 receiver_total = receiver_total.drop_duplicates('time')
                 receiver_total = receiver_total.set_index('time')
                 receivers[n+1].append(receiver_total)
              else:
                 print("Folder %s not found" % PATH)

        # For each flow, receivers contains a list of DataFrames with a time and bandwidth column.
        # These DataFrames should have the same index. Now concatenate and compute mean and std.
        for n in range(4):
           flow_key = FLOWS[n]  # Use string key (e.g., "x1")
           concatenated = pd.concat(receivers[n+1], axis=1)
           goodput_data[protocol][flow_key]['mean'] = concatenated.mean(axis=1)
           goodput_data[protocol][flow_key]['std'] = concatenated.std(axis=1)
           goodput_data[protocol][flow_key].index = concatenated.index
    return goodput_data

def plot_data(data, filename, ylim=None, xlim=None):
    LINEWIDTH = 1
    fig, axes = plt.subplots(nrows=len(PROTOCOLS_LEO), ncols=1, figsize=(8, 5), sharex=True, sharey=True)
    for i, protocol in enumerate(PROTOCOLS_LEO):
        ax = axes[i]
        for n in range(4):
            flow = FLOWS[n]  # string key e.g., "x1"
            ax.plot(data['fifo'][protocol][flow].index, 
                    data['fifo'][protocol][flow]['mean'],
                    linewidth=LINEWIDTH, label=protocol)

            try:
                ax.fill_between(data['fifo'][protocol][flow].index,
                                data['fifo'][protocol][flow]['mean'] - data['fifo'][protocol][flow]['std'],
                                data['fifo'][protocol][flow]['mean'] + data['fifo'][protocol][flow]['std'],
                                alpha=0.2)
            except Exception as e:
                print('Protocol: %s' % protocol)
                print(data['fifo'][protocol][flow]['mean'])
                print(data['fifo'][protocol][flow]['std'])
                print("Error:", e)

        if ylim:
            ax.set(ylim=ylim)

        if xlim:
            ax.set(xlim=xlim)
            ax.set_xticks(range(0, 176, 25))

        if i == len(PROTOCOLS_LEO)-1:
            ax.set(xlabel='time (s)')

        ax.text(70, 85, PROTOCOLS_FRIENDLY_NAME_LEO[protocol], va='center', c=COLORS_LEO[protocol])
        ax.grid()

    fig.text(0.045, 0.5, 'Goodput (Mbps)', va='center', rotation='vertical')
    plt.subplots_adjust(top=0.95)
    plt.savefig(filename, dpi=1080)

if __name__ == "__main__":
    EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_aqm"
    BW = 100
    DELAY = 10
    AQM = 'fifo'
    AQM_LIST = ['fifo']

    for QMULT in QMULTS:
        goodput_data = {}
        for aqm in AQM_LIST:
            goodput = get_goodput_data(BW, DELAY, QMULT, RUNS, aqm)
            goodput_data[aqm] = goodput

        for format in ['pdf']:
            plot_data(goodput_data, 'aqm_goodput_%smbps_%sms_%smult.%s' % (BW, DELAY, QMULT, format), ylim=[0, 100], xlim=[0,175])
            # plot_data(delay_data, 'aqm_delay_%smbps_%sms_%smult.png' % (BW, DELAY, QMULTS))
            # plot_data(retr_data, 'aqm_retr_%smbps_%sms_%smult.png' % (BW, DELAY, QMULTS))
