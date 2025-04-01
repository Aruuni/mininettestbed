import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter
import numpy as np
from mpl_toolkits.axes_grid1 import ImageGrid
import numpy as np

plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *

PROTOCOLS = ['sage']
def parse_aurora_output(file, offset):
   with open(file, 'r') as fin:
      auroraOutput = fin.read()

   start_index = auroraOutput.find("new connection")
   if start_index == -1:
      start_index = auroraOutput.find("No connection established within")
      if start_index == -1:
         # Client case
         start_index = auroraOutput.find("finished connect")
         if start_index == -1:
            case = "client"
            success = False
         else:
            case = "client"
            success = True

      else:
         case = "server"
         success = False
   else:
      case = "server"
      success = True

   if success:
      auroraOutput = auroraOutput[start_index:]
      auroraOutput = auroraOutput.replace("send/recv: Non-blocking call failure: no buffer available for sending.\n",
                                          "")
      end_index = auroraOutput.find("recv:Connection was broken.")
      if end_index != -1:
         auroraOutput = auroraOutput[:end_index]
      end_index = auroraOutput.find("recv:Non-blocking call failure: no data available for reading")
      if end_index != -1:
         auroraOutput = auroraOutput[:end_index]
      lines = auroraOutput.strip().split("\n")
      lines = [line for line in lines if line.strip() != '']
      lines = lines[1:]  # Remove the first line containing "new connection...."
      columns = lines[0].split(",")

      # Extract the relevant information
      data = [line.split(",") for line in lines[1:]]
      data = data[1:]  # Remove first data point containing uniitialised values

      data = [[float(val) for val in sublist] for sublist in data]
      # Create a pandas DataFrame
      df = pd.DataFrame(data, columns=columns)
      # Convert columns to appropriate types
      df["time"] = df["time"] / 1000000
      df["time"] = df["time"] + offset
   else:
      if case == 'client':
         df = pd.DataFrame([], columns=['time', 'bandwidth', 'rtt', 'sent', 'lost', 'retr'])
      elif case == 'server':
         df = pd.DataFrame([], columns=['time', 'bandwidth'])

   return df

def parse_orca_output(file, offset):
   with open(file, 'r') as fin:
      orcaOutput = fin.read()
   start_index = orcaOutput.find("----START----")
   end_index = orcaOutput.find("----END----")
   orcaOutput = orcaOutput[start_index:end_index]

   lines = orcaOutput.strip().split("\n")
   lines = [line for line in lines if line.strip() != '']

   # Extract the relevant information
   data = [line.split(",") for line in lines[1:]]
   columns = ["time", "bandwidth", "bytes"] if len(data[0]) == 3 else ["time", "bandwidth", "bytes", "totalgoodput"]

   # Create a pandas DataFrame
   df = pd.DataFrame(data, columns=columns)
   # Convert columns to appropriate types
   df["time"] = df["time"].astype(float)
   if len(columns) > 3:
      df["time"] = df["time"] + offset
   df["bandwidth"] = df["bandwidth"].astype(float) / 1000000
   df["bytes"] = df["bytes"].astype(float)
   if len(columns) > 3:
      df["totalgoodput"] = df["totalgoodput"].astype(float)

   return df

if __name__ == "__main__":
    for QMULT in [0.2,1,4]:
        for mode in ['normal', 'inverse']:
            fig, axes = plt.subplots(nrows=len(PROTOCOLS), ncols=1, figsize=(15,5), sharex=True)
            plt.subplots_adjust(hspace=0.5)
            COLORMAP = {'cubic': '#0C5DA5',
             'orca': '#00B945',
             'bbr3': '#FF9500',
             'bbr': '#FF2C01',
             'sage': '#845B97',
             'pcc': '#686868',
             }
            LEGENDMAP = {}
            BW = 100
            DELAY = 50
            
            RUNS = [1,2,3,4,5]

            LINEWIDTH = 1

            if mode == 'inverse':
                ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_friendly_intra_rtt_async_inverse_longer/fifo" 
            else:
                ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_friendly_intra_rtt_longer/fifo" 
            for FLOWS in [2]:
               data = {protocol: {i: pd.DataFrame([], columns=['time', 'mean', 'std']) for i in range(1, 5)} for protocol in PROTOCOLS}


               start_time = 0
               end_time = 600
               # Plot throughput over time
               for protocol in PROTOCOLS:
                  BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
                  BDP_IN_PKTS = BDP_IN_BYTES / 1500
                  senders = {1: [], 2: [], 3: [], 4:[]}
                  receivers = {1: [], 2: [], 3: [], 4:[]}
                  for run in RUNS:
                     PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_%sflows_22tcpbuf_%s/run%s' % (BW,DELAY,int(QMULT * BDP_IN_PKTS),FLOWS,protocol,run)
                     for n in range(FLOWS):
                        if not os.path.exists(PATH + '/csvs/c%s.csv' % (n+1)):
                            try:
                                if protocol == 'orca':
                                    df = parse_orca_output(PATH + '/x%s_output.txt' % (n+1), 0 if n == 0 else DELAY)
                                    df.to_csv(PATH + '/csvs/x%s.csv' % (n+1), index=False)
                                if protocol == 'aurora':
                                    df = parse_aurora_output(PATH + '/x%s_output.txt' % (n+1), 0 if n == 0 else DELAY)
                                    df.to_csv(PATH + '/csvs/x%s.csv' % (n+1), index=False)
                            except:
                                print("Error parsing")
                        if os.path.exists(PATH + '/csvs/c%s.csv' % (n+1)):
                           sender = pd.read_csv(PATH +  '/csvs/c%s.csv' % (n+1))
                           senders[n+1].append(sender)
                        else:
                           print("Folder not found")

                        if os.path.exists(PATH + '/csvs/x%s.csv' % (n+1)):
                           receiver_total = pd.read_csv(PATH + '/csvs/x%s.csv' % (n+1)).reset_index(drop=True)
                           receiver_total = receiver_total[['time', 'bandwidth']]
                           receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))
                           receiver_total['bandwidth'] = receiver_total['bandwidth'].ewm(alpha=0.5).mean()

                           receiver_total = receiver_total[(receiver_total['time'] >= (start_time)) & (receiver_total['time'] <= (end_time))]
                           receiver_total = receiver_total.drop_duplicates('time')
                           receiver_total = receiver_total.set_index('time')
                           receivers[n+1].append(receiver_total)
                        else:
                           print(f"Folder {PATH} not found")

                  # For each flow, receivers contains a list of dataframes with a time and bandwidth column. These dataframes SHOULD have
                  # exactly the same index. Now I can concatenate and compute mean and std
                  for n in range(FLOWS):
                      if len(receivers[n+1]) > 0:
                         data[protocol][n+1]['mean'] = pd.concat(receivers[n+1], axis=1).mean(axis=1)
                         data[protocol][n+1]['std'] = pd.concat(receivers[n+1], axis=1).std(axis=1)
                         data[protocol][n+1].index = pd.concat(receivers[n+1], axis=1).index
                         data[protocol][n+1] = data[protocol][n+1][data[protocol][n+1].index <= 600]
                         data[protocol][n+1] = data[protocol][n+1].sort_index()

            for i,protocol in enumerate(PROTOCOLS):
               #remove index for single plot
               ax = axes

               for n in range(FLOWS):
                  if mode == 'inverse':
                     LABEL = (lambda p: 'bbrv1' if p == 'bbr' else 'bbrv3' if p == 'bbr3' else 'vivace' if p == 'pcc' else p)(protocol) if n == 0 else 'cubic'
                     COLOR = '#0C5DA5' if n == 1 else COLORMAP[protocol]
                  else:
                     LABEL = (lambda p: 'bbrv1' if p == 'bbr' else 'bbrv3' if p == 'bbr3' else 'vivace' if p == 'pcc' else p)(protocol) if n == 1 else 'cubic'
                     COLOR = '#0C5DA5' if n == 0 else COLORMAP[protocol]
                  print(data[protocol][n+1].index)
                  ax.plot(data[protocol][n+1].index, data[protocol][n+1]['mean'].sort_index(), linewidth=LINEWIDTH, label=LABEL, color=COLOR)
                  try:
                     if mode == 'inverse':
                           FC = '#0C5DA5' if n == 1 else COLORMAP[protocol]
                     else:
                           FC = '#0C5DA5' if n == 0 else COLORMAP[protocol]
                     ax.fill_between(data[protocol][n+1].index, data[protocol][n+1]['mean'] - data[protocol][n+1]['std'], data[protocol][n+1]['mean'] + data[protocol][n+1]['std'], alpha=0.2,  fc=FC)
                  except:
                     print("Fill between error")


               ax.set(ylim=[0,100])
               ax.set(xlim=[0,600])

               ax.grid()

               handles, labels = ax.get_legend_handles_labels()
               for handle, label in zip(handles, labels):
                  if not LEGENDMAP.get(label,None):
                     LEGENDMAP[label] = handle

            fig.text(0.5, 0.01, 'time (s)', ha='center')
            fig.text(0.045, 0.6, 'Goodput (Mbps)', va='center', rotation='vertical')

            
            fig.legend(list(LEGENDMAP.values()), list(LEGENDMAP.keys()), loc='upper center',ncol=3, bbox_to_anchor=(0.5, 1.20))

            for format in ['pdf']:
                plt.subplots_adjust(top=1)
                plt.savefig('goodput_friendly_%sms_%s_%s.%s' % (DELAY, QMULT, mode, format), dpi=720, bbox_inches='tight')
