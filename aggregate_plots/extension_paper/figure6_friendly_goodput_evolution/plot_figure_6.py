import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
import numpy as np

plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 


PROTOCOLS = ['cubic','bbr3',  'sage', 'orca',   'vivace-uspace', 'astraea',]
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
    for mult in QMULTS:
        for mode in ['normal', 'inverse']:
            fig, axes = plt.subplots(nrows=len(PROTOCOLS), ncols=1, figsize=(5,3), sharex=True)
            plt.subplots_adjust(hspace=0.5)
            LEGENDMAP = {}
            BW = 100
            DELAY = 50
            LINEWIDTH = 1
            if mode == 'inverse':
                ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_friendly_intra_rtt_async_inverse/fifo" 
            else:
                ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_friendly_intra_rtt_async/fifo" 
            for FLOWS in [2]:
               data = {protocol: {i: pd.DataFrame([], columns=['time', 'mean', 'std']) for i in range(1, 5)} for protocol in PROTOCOLS}


               start_time = 0
               end_time = 4*DELAY-2
               # Plot throughput over time
               for protocol in PROTOCOLS:
                  BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
                  BDP_IN_PKTS = BDP_IN_BYTES / 1500
                  senders = {1: [], 2: [], 3: [], 4:[]}
                  receivers = {1: [], 2: [], 3: [], 4:[]}
                  for run in RUNS:
                     PATH = f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_{FLOWS}flows_22tcpbuf_{protocol}/run{run}" 
                     for n in range(FLOWS):
                        if os.path.exists(f"{PATH}/csvs/c{(n+1)}.csv"):
                           sender = pd.read_csv(f"{PATH}/csvs/c{(n+1)}.csv")
                           senders[n+1].append(sender)
                        else:
                           prin = f"{PATH}/csvs/c{(n+1)}.csv"
                           print(f"Folder not {prin} found")

                        if os.path.exists(f"{PATH}/csvs/x{(n+1)}.csv"):
                           receiver_total = pd.read_csv(f"{PATH}/csvs/x{(n+1)}.csv").reset_index(drop=True)
                           receiver_total = receiver_total[['time', 'bandwidth']]
                           receiver_total['time'] = receiver_total['time'].apply(lambda x: int(float(x)))
                           receiver_total['bandwidth'] = receiver_total['bandwidth'].ewm(alpha=0.5).mean()

                           receiver_total = receiver_total[(receiver_total['time'] >= (start_time)) & (receiver_total['time'] <= (end_time))]
                           receiver_total = receiver_total.drop_duplicates('time')
                           receiver_total = receiver_total.set_index('time')
                           receivers[n+1].append(receiver_total)
                        else:
                           print("Folder not found")

                  # For each flow, receivers contains a list of dataframes with a time and bandwidth column. These dataframes SHOULD have
                  # exactly the same index. Now I can concatenate and compute mean and std
                  for n in range(FLOWS):
                      if len(receivers[n+1]) > 0:
                         data[protocol][n+1]['mean'] = pd.concat(receivers[n+1], axis=1).mean(axis=1).sort_index()
                         data[protocol][n+1]['std'] = pd.concat(receivers[n+1], axis=1).std(axis=1).sort_index()
                         data[protocol][n+1].index = pd.concat(receivers[n+1], axis=1).sort_index().index

            for i,protocol in enumerate(PROTOCOLS):
               #remove index for single plot
               ax = axes[i]

               for n in range(FLOWS):
                   if mode == 'inverse':
                       LABEL = PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol] if n == 0 else 'Cubic'
                       COLOR = '#0C5DA5' if n == 1 else COLORS_EXTENSION[protocol]
                   else:
                       LABEL = PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol] if n == 1 else 'Cubic'
                       COLOR = '#0C5DA5' if n == 0 else COLORS_EXTENSION[protocol]

                   ax.plot(data[protocol][n+1].index, data[protocol][n+1]['mean'], linewidth=LINEWIDTH, label=LABEL, color=COLOR)
                   try:
                     if mode == 'inverse':
                         FC = '#0C5DA5' if n == 1 else COLORS_EXTENSION[protocol]
                     else:
                         FC = '#0C5DA5' if n == 0 else COLORS_EXTENSION[protocol]
                     ax.fill_between(data[protocol][n+1].index, data[protocol][n+1]['mean'] - data[protocol][n+1]['std'], data[protocol][n+1]['mean'] + data[protocol][n+1]['std'], alpha=0.2,  fc=FC)
                   except:
                     print("Fill between error")


               ax.set(ylim=[0,100])
               ax.set(xlim=[0,200])

               ax.grid()

               handles, labels = ax.get_legend_handles_labels()
               for handle, label in zip(handles, labels):
                  if not LEGENDMAP.get(label,None):
                     LEGENDMAP[label] = handle

            fig.text(0.5, 0.01, 'time (s)', ha='center')
            fig.text(0.030, 0.6, 'Goodput (Mbps)', va='center', rotation='vertical')

            # fig.legend(list(LEGENDMAP.values()), list(LEGENDMAP.keys()), loc='upper center',ncol=3, bbox_to_anchor=(0.5, 1.17))
            plt.subplots_adjust(top=1)
            plt.savefig(f"goodput_friendly_{DELAY}ms_{mult}_{mode}.pdf", dpi=720, bbox_inches='tight')
