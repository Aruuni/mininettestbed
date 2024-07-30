import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import os
import matplotlib as mpl
mpl.rcParams['agg.path.chunksize'] = 10000
pd.set_option('display.max_rows', None)

plt.rcParams['text.usetex'] = False

def get_data(BW, aqm, delay, qmult, n_flows=2):
    goodput_data = {
        'bbr': {i + 1: pd.DataFrame([], columns=['time', 'mean', 'std']) for i in range(n_flows)}
    }

    start_time = 0
    end_time = 100
    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500

    for protocol in PROTOCOLS:
        senders = {i + 1: [] for i in range(n_flows)}
        receivers = {i + 1: [] for i in range(n_flows)}
        for run in RUNS:
            PATH = ROOT_PATH + '/%s/DoubleDumbell_%smbit_%sms_%spkts_0loss_%sflows_22tcpbuf_%s/run%s' % (
                aqm, BW, delay, int(qmult * BDP_IN_PKTS), n_flows, protocol, run)
            
            for n in range(n_flows):
                if n < n_flows // 2:
                    suffix = f'1{n + 1}'  # First dumbbell
                else:
                    suffix = f'2{n + 1 - n_flows // 2}'  # Second dumbbell
                
                sender_path = PATH + f'/csvs/c{suffix}.csv'
                receiver_path = PATH + f'/csvs/x{suffix}.csv'

                if os.path.exists(sender_path):
                    sender = pd.read_csv(sender_path)
                    senders[n + 1].append(sender)
                else:
                    print("Folder not found:", sender_path)

                if os.path.exists(receiver_path):
                    receiver_total = pd.read_csv(receiver_path).reset_index(drop=True)
                    receiver_total = receiver_total[['time', 'bandwidth']]
                    #receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))
                    #receiver_total = receiver_total[(receiver_total['time'] >= (start_time + n * 25)) & (receiver_total['time'] <= (end_time + n * 25))]
                    #receiver_total = receiver_total.drop_duplicates('time')
                    receiver_total = receiver_total.set_index('time')
                    print(receiver_total)
                    receivers[n + 1].append(receiver_total)
                else:
                    print("Folder not found:", receiver_path)

        for n in range(n_flows):
           goodput_data[protocol][n+1]['mean'] = pd.concat(receivers[n+1], axis=1).mean(axis=1)
           goodput_data[protocol][n+1]['std'] = pd.concat(receivers[n+1], axis=1).std(axis=1)
           goodput_data[protocol][n+1].index = pd.concat(receivers[n+1], axis=1).index

    return goodput_data

def plot_data(data, filename, ylim=None):
    COLOR = {
        'bbr': '#00B945'
    }

    LINEWIDTH = 1
    fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(6, 2), sharex=True, sharey=True)
    for i, protocol in enumerate(PROTOCOLS):
        ax = axes#[i]
        for n in range(2):
            ax.plot(data['fifo'][protocol][n + 1].index, data['fifo'][protocol][n + 1]['mean'],
                    linewidth=LINEWIDTH, label=protocol)
            try:
                ax.fill_between(data['fifo'][protocol][n + 1].index,
                                data['fifo'][protocol][n + 1]['mean'] - data['fifo'][protocol][n + 1]['std'],
                                data['fifo'][protocol][n + 1]['mean'] + data['fifo'][protocol][n + 1]['std'],
                                alpha=0.2)
            except:
                print('Protocol: %s' % protocol)
                print(data['fifo'][protocol][n + 1]['mean'])
                print(data['fifo'][protocol][n + 1]['std'])

        if ylim:
            ax.set(ylim=ylim)

        if i == len(PROTOCOLS):
            ax.set(xlabel='time (s)')
        ax.set(title='%s' % protocol)
        #ax.text(70, 90, '%s' % protocol, va='center', c=COLOR[protocol])
        ax.grid()

    plt.subplots_adjust(top=0.95)
    plt.legend()
    plt.savefig(filename, dpi=720)
if __name__ == "__main__":
    ROOT_PATH = "/home/mihai/mininettestbed/nooffload/fairness_cross_traffic"
    PROTOCOLS = ['bbr']
    BW = 100
    DELAY = 3
    RUNS = [1]
    QMULTS = [1]
    FLOWS = [2]
    AQM = 'fifo'
    AQM_LIST = ['fifo']
    for QMULT in QMULTS:
        sending_rate_data = {}
        for aqm in AQM_LIST:
            sending_rate = get_data(BW, aqm, DELAY, QMULT)
            sending_rate_data[aqm] = sending_rate

        for format in ['pdf']:
            plot_data(sending_rate_data, 'sending_rate_%smbps_%sms_%smult.%s' % (BW, DELAY, QMULT, format), ylim=None)
