import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import os, sys
import matplotlib as mpl
mpl.rcParams['agg.path.chunksize'] = 10000
pd.set_option('display.max_rows', None)
plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *

PROTOCOLS = ['cubic', 'sage', 'orca', 'astraea', 'bbr3', 'vivace']


def get_aqm_data(BW,aqm, delay, qmult):

    # Fetch per flow goodput
    goodput_data = {
        protocol: {i: pd.DataFrame([], columns=['time', 'mean', 'std']) for i in range(1, 5)}
        for protocol in PROTOCOLS
    }

    start_time = 0
    end_time = 100
    for protocol in PROTOCOLS:
        BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
        BDP_IN_PKTS = BDP_IN_BYTES / 1500
        senders = {1: [], 2: [], 3: [], 4:[]}
        receivers = {1: [], 2: [], 3: [], 4:[]}
        for run in RUNS:
           PATH = ROOT_PATH + '/%s/Dumbell_%smbit_%sms_%spkts_0loss_%sflows_22tcpbuf_%s/run%s' % (aqm,BW,delay,int(qmult * BDP_IN_PKTS),4,protocol,run)
           for n in range(4):
              if os.path.exists(PATH + '/csvs/c%s.csv' % (n+1)):
                 sender = pd.read_csv(PATH +  '/csvs/c%s.csv' % (n+1))
                 senders[n+1].append(sender)
              else:
                 print("Folder not found")

              if os.path.exists(PATH + '/csvs/x%s.csv' % (n+1)):
                 receiver_total = pd.read_csv(PATH + '/csvs/x%s.csv' % (n+1)).reset_index(drop=True)
                 receiver_total = receiver_total[['time', 'bandwidth']]
                 receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))
                 # receiver_total['bandwidth'] = receiver_total['bandwidth']

                 receiver_total = receiver_total[(receiver_total['time'] >= (start_time+n*25)) & (receiver_total['time'] <= (end_time+n*25))]
                 receiver_total = receiver_total.drop_duplicates('time')
                 receiver_total = receiver_total.set_index('time')
                 receivers[n+1].append(receiver_total)
              else:
                 print("Folder %s not found" % PATH)

        # For each flow, receivers contains a list of dataframes with a time and bandwidth column. These dataframes SHOULD have
        # exactly the same index. Now I can concatenate and compute mean and std
        for n in range(4):
            df = pd.concat(receivers[n+1], axis=1)
            df = df.sort_index()  # Ensure ascending time
            goodput_data[protocol][n+1]['mean'] = df.mean(axis=1)
            goodput_data[protocol][n+1]['std']  = df.std(axis=1)
            goodput_data[protocol][n+1].index  = df.index

    # Fetch per flow delay
    delay_data = {
        protocol: {i: pd.DataFrame([], columns=['time', 'mean', 'std']) for i in range(1, 5)}
        for protocol in PROTOCOLS
    }


    # Fetch per flow retransmissions
    retr_data = {
        protocol: {i: pd.DataFrame([], columns=['time', 'mean', 'std']) for i in range(1, 5)}
        for protocol in PROTOCOLS
    }

    start_time = 0
    end_time = 100
    for protocol in PROTOCOLS:
        BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
        BDP_IN_PKTS = BDP_IN_BYTES / 1500
        senders = {1: [], 2: [], 3: [], 4: []}
        receivers = {1: [], 2: [], 3: [], 4: []}
        for run in RUNS:
            PATH = ROOT_PATH + '/%s/Dumbell_%smbit_%sms_%spkts_0loss_%sflows_22tcpbuf_%s/run%s' % (
                aqm, BW, delay, int(qmult * BDP_IN_PKTS), 4, protocol, run)
            start_timestamp = 0
            for n in range(4):
                if protocol != 'aurora':
                    if os.path.exists(PATH + '/sysstat/etcp_c%s.log' % (n+1)):
                        systat = pd.read_csv(PATH + '/sysstat/etcp_c%s.log' % (n+1), sep=';').rename(
                            columns={"# hostname": "hostname"})
                        retr = systat[['timestamp', 'retrans/s']]

                        if n == 0:
                            start_timestamp =  retr['timestamp'].iloc[0]
                    
                        retr.loc[:, 'timestamp'] = retr['timestamp'] - start_timestamp + 1


                        retr = retr.rename(columns={'timestamp': 'time'})
                        retr['time'] = retr['time'].apply(lambda x: int(float(x)))
                        retr = retr[(retr['time'] >= (start_time + n * 25)) & (retr['time'] <= (end_time + n * 25))]
                        retr = retr.drop_duplicates('time')
                        retr = retr.set_index('time')
                        senders[n + 1].append(retr)

                    else:
                        print("Folder %s not found" % (PATH))
                else:
                    if os.path.exists(PATH + '/csvs/c%s.csv' % (n+1)):
                        systat = pd.read_csv(PATH + '/csvs/c%s.csv' % (n+1)).rename(
                            columns={"retr": "retrans/s"})
                        retr = systat[['time', 'retrans/s']]
                        retr['time'] = retr['time'].apply(lambda x: int(float(x)))
                        retr = retr[(retr['time'] >= (start_time + n * 25)) & (retr['time'] <= (end_time + n * 25))]
                        retr = retr.drop_duplicates('time')
                        retr = retr.set_index('time')
                        senders[n + 1].append(retr)


        # For each flow, receivers contains a list of dataframes with a time and bandwidth column. These dataframes SHOULD have
        # exactly the same index. Now I can concatenate and compute mean and std
        for n in range(4):
            retr_data[protocol][n + 1]['mean'] = pd.concat(senders[n + 1], axis=1).mean(axis=1)
            retr_data[protocol][n + 1]['std'] = pd.concat(senders[n + 1], axis=1).std(axis=1)
            retr_data[protocol][n + 1].index = pd.concat(senders[n + 1], axis=1).index


    return goodput_data, delay_data, retr_data




def plot_data(data, filename, ylim=None, xlim=None):
    COLOR = {'cubic': '#0C5DA5',
             'orca': '#00B945',
             'bbr3': '#FF9500',
             'sage': '#FF2C01',
             'vivace': '#845B97',
             'astraea': '#686868',
             }
    LINEWIDTH = 1
    fig, axes = plt.subplots(nrows=len(PROTOCOLS), ncols=1, figsize=(8, 5), sharex=True, sharey=True)

    for i, protocol in enumerate(PROTOCOLS):
        ax = axes[i]
        for n in range(4):
            ax.plot(data['fifo'][protocol][n + 1].index, data['fifo'][protocol][n + 1]['mean'],
                    linewidth=LINEWIDTH, label=protocol, )
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
        if xlim:
            ax.set(xlim=xlim)
            ax.set_xticks(range(0, 176, 25))
        if i == len(PROTOCOLS)-1:
            ax.set(xlabel='time (s)')
        # ax.set(title='%s' % protocol)

        ax.text(70, 90, '%s' % (lambda p: 'bbrv1' if p == 'bbr' else 'bbrv3' if p == 'bbr3' else 'vivace' if p == 'pcc' else p)(protocol), va='center', c=COLOR[protocol])
        ax.grid()

    #fig.suptitle("%s Mbps, %s RTT, %sxBDP" % (BW, 2*DELAY, QMULT))
    fig.text(0.045, 0.6, 'Goodput (Mbps)', va='center', rotation='vertical')

    plt.subplots_adjust(top=0.95)
    plt.savefig(filename, dpi=720)



if __name__ == "__main__":
    ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_aqm"
    BW = 100
    DELAY = 100
    RUNS = [1, 2, 3, 4, 5]
    QMULTS = [0.2,1,4]
    AQM = 'fifo'
    AQM_LIST = ['fifo']

    for QMULT in QMULTS:
        goodput_data = {}
        delay_data = {}
        retr_data = {}
        for aqm in AQM_LIST:
            goodput, delay, retr = get_aqm_data(BW,aqm, DELAY, QMULT)
            goodput_data[aqm] = goodput
            delay_data[aqm] = delay
            retr_data[aqm] = retr

        for format in ['pdf']:
            plot_data(goodput_data, 'aqm_goodput_%smbps_%sms_%smult.%s' % (BW, DELAY, QMULT, format), ylim=[0, 100], xlim=[0,175])
            # plot_data(delay_data, 'aqm_delay_%smbps_%sms_%smult.png' % (BW, DELAY, QMULTS))
            # plot_data(retr_data, 'aqm_retr_%smbps_%sms_%smult.png' % (BW, DELAY, QMULTS))









