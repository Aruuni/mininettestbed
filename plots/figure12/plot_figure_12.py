import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import os
import matplotlib as mpl
mpl.rcParams['agg.path.chunksize'] = 10000
pd.set_option('display.max_rows', None)

plt.rcParams['text.usetex'] = False

def get_aqm_data(BW,aqm, delay, qmult):

    # Fetch per flow goodput orcaOriginalData
    goodput_data = {
             'orcaHyper-V':
                {1: pd.DataFrame([], columns=['time','mean', 'std']),
                 2: pd.DataFrame([], columns=['time','mean', 'std']),
                 3: pd.DataFrame([], columns=['time','mean', 'std']),
                 4: pd.DataFrame([], columns=['time','mean', 'std'])},
             'orcaVMWare':
                {1: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 2: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 3: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 4: pd.DataFrame([], columns=['time', 'mean', 'std'])},
             'orcaOriginalData':
                {1: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 2: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 3: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 4: pd.DataFrame([], columns=['time', 'mean', 'std'])},
             'sageDataOrcaVMWare':
                {1: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 2: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 3: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 4: pd.DataFrame([], columns=['time', 'mean', 'std'])},
             'sageDataOrcaHyper-V':
                {1: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 2: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 3: pd.DataFrame([], columns=['time', 'mean', 'std']),
                 4: pd.DataFrame([], columns=['time', 'mean', 'std'])},
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
           goodput_data[protocol][n+1]['mean'] = pd.concat(receivers[n+1], axis=1).mean(axis=1)
           goodput_data[protocol][n+1]['std'] = pd.concat(receivers[n+1], axis=1).std(axis=1)
           goodput_data[protocol][n+1].index = pd.concat(receivers[n+1], axis=1).index


    return goodput_data


def plot_data(data, filename, ylim=None):
    COLOR = {
            'orcaVMWare': '#00B945',     
            'orcaHyper-V': '#0C5DA5',
            'orcaOriginalData': '#7E2F8E',
            'sageDataOrcaVMWare': '#FF9500',
            'sageDataOrcaHyper-V': '#8B0000'
            }

    LINEWIDTH = 1
    fig, axes = plt.subplots(nrows=5, ncols=1, figsize=(6, 4), sharex=True, sharey=True)

    for i, protocol in enumerate(PROTOCOLS):
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
                print('Protocol: %s' % protocol)
                print(data['fifo'][protocol][n + 1]['mean'])
                print(data['fifo'][protocol][n + 1]['std'])

        if ylim:
            ax.set(ylim=ylim)

        if i == 4:
            ax.set(xlabel='time (s)')
        # ax.set(title='%s' % protocol)
        ax.text(70, 90, '%s' % protocol, va='center', c=COLOR[protocol])
        ax.grid()

    # fig.suptitle("%s Mbps, %s RTT, %sxBDP" % (BW, 2*DELAY, QMULTS))
    plt.subplots_adjust(top=0.95)
    plt.savefig(filename, dpi=720)



if __name__ == "__main__":
    ROOT_PATH = "/home/sage/mininettestbed/nooffload/results_fairness_aqm"
    PROTOCOLS = ['orcaVMWare', 'sageDataOrcaVMWare' , 'orcaHyper-V', 'sageDataOrcaHyper-V',  'orcaOriginalData']
    BW = 100
    DELAY = 10
    RUNS = [1, 2, 3, 4, 5]
    QMULTS = [0.2,1,4]
    AQM = 'fifo'
    #AQM_LIST = ['fifo', 'fq', 'codel']
    AQM_LIST = ['fifo']
    for QMULT in QMULTS:
        goodput_data = {}
        delay_data = {}
        retr_data = {}
        for aqm in AQM_LIST:
            goodput = get_aqm_data(BW,aqm, DELAY, QMULT)
            goodput_data[aqm] = goodput

        for format in ['pdf']:
            plot_data(goodput_data, 'aqm_goodput_%smbps_%sms_%smult.%s' % (BW, DELAY, QMULT, format), ylim=[0, 100])
            # plot_data(delay_data, 'aqm_delay_%smbps_%sms_%smult.png' % (BW, DELAY, QMULTS))
            # plot_data(retr_data, 'aqm_retr_%smbps_%sms_%smult.png' % (BW, DELAY, QMULTS))














