import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
plt.style.use('science')
import json
import os, sys
import matplotlib as mpl
import numpy as np
from matplotlib.pyplot import figure


plt.rcParams['text.usetex'] = False
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../../..')
sys.path.append( mymodule_dir )
from core.config import *
from core.plotting import * 

BW = 50
DELAY = 50
QMULT = 1
RUN = 16
BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
BDP_IN_PKTS = BDP_IN_BYTES / 1500
start_time = 100
end_time = 200
LINEWIDTH = 0.7

fig, axes = plt.subplots(nrows=2, ncols=1,figsize=(3,2), sharex=True)
ax = axes[0]
ax2 = ax.twinx()

final_handles = []
final_labels = []

ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt/fifo"
for protocol in PROTOCOLS_EXTENSION:
    PATH = f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{RUN}"
    with open(f"{PATH}/emulation_info.json", 'r') as fin:
        emulation_info = json.load(fin)

    bw_capacities = list(filter(lambda elem: elem[4] >= start_time and elem[4] <= end_time, emulation_info['flows']))
    bw_capacities = list(filter(lambda elem: elem[6] == 'tbf', bw_capacities))
    bw_capacities = [x[-1][1] for x in bw_capacities]

    min_rtts = list(filter(lambda elem: elem[4] >= start_time and elem[4] <= end_time, emulation_info['flows']))
    min_rtts = list(filter(lambda elem: elem[6] == 'netem', min_rtts))
    min_rtts = [x[-1][2] for x in min_rtts]

    if os.path.exists(f"{PATH}/csvs/c1.csv"):
        sender = pd.read_csv(f"{PATH}/csvs/c1.csv").reset_index(drop=True)
        sender['time'] = sender['time'].apply(lambda x: int(float(x)))
        sender = sender[(sender['time'] > start_time) & (sender['time'] < end_time)]
        sender = sender.drop_duplicates('time')
        sender = sender.set_index('time')
        ax.plot(sender.index + 1, sender['bandwidth'], color=COLORS_EXTENSION[protocol], linewidth=LINEWIDTH, label=PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol])



ax.step(list(range(start_time,end_time+1,10)),bw_capacities,where='post', color='black',linewidth=0.5, label='bandwidth',  alpha=0.5)
ax2.step(list(range(start_time,end_time+1,10)),min_rtts,where='post', color='red',linewidth=0.5, label='min RTT', linestyle='dashed', alpha=0.5)
ax2.set_ylabel('min RTT\n(ms)')

handles, labels = ax.get_legend_handles_labels()
for handle, label in zip(handles,labels):
    if label not in final_labels:
        final_labels.append(label)
        final_handles.append(handle)

handles, labels = ax2.get_legend_handles_labels()
for handle, label in zip(handles,labels):
    if label not in final_labels:
        final_labels.append(label)
        final_handles.append(handle)

protocol_data = {}
ax = axes[1]
ax2 = ax.twinx()
ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_loss/fifo"
for protocol in PROTOCOLS_EXTENSION:
    PATH = f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{RUN}"
    with open(f"{PATH}/emulation_info.json", 'r') as fin:
        emulation_info = json.load(fin)

    bw_capacities = list(filter(lambda elem: elem[4] >= start_time and elem[4] <= end_time, emulation_info['flows']))
    bw_capacities = list(filter(lambda elem: elem[6] == 'tbf', bw_capacities))
    bw_capacities = [x[-1][1] for x in bw_capacities]

    losses = list(filter(lambda elem: elem[4] >= start_time and elem[4] <= end_time, emulation_info['flows']))
    losses = list(filter(lambda elem: elem[6] == 'netem', losses))
    losses = [x[-1][-2] for x in losses]

    if os.path.exists(f"{PATH}/csvs/c1.csv"):
        sender = pd.read_csv(f"{PATH}/csvs/c1.csv").reset_index(drop=True)
        sender['time'] = sender['time'].apply(lambda x: int(float(x)))
        sender = sender[(sender['time'] > start_time) & (sender['time'] < end_time)]
        sender = sender.drop_duplicates('time')
        sender = sender.set_index('time')
        ax.plot(sender.index + 1, sender['bandwidth'], color=COLORS_EXTENSION[protocol], linewidth=LINEWIDTH, label=PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol])

ax.step(list(range(start_time, end_time + 1, 10)), bw_capacities, where='post', color='black', linewidth=0.5, label='bandwidth', alpha=0.5)
ax2.step(list(range(start_time, end_time + 1, 10)), losses, where='post', color='red', linewidth=0.5,label='loss rate', linestyle='-.', alpha=0.5)
ax2.set_ylabel('Loss Rate\n(\%)')

handles, labels = ax.get_legend_handles_labels()
for handle, label in zip(handles, labels):
    if label not in final_labels:
        final_labels.append(label)
        final_handles.append(handle)

handles, labels = ax2.get_legend_handles_labels()
for handle, label in zip(handles, labels):
    if label not in final_labels:
        final_labels.append(label)
        final_handles.append(handle)

ax.set(xlabel="time (s)")
fig.text(-0.05,0.5,"Sending Rate (Mbps)", rotation='vertical', va='center', ha='center')
ax2.yaxis.set_label_coords(1.15, 0.5)
fig.legend(final_handles, final_labels,ncol=3, loc='upper center',bbox_to_anchor=(0.5, 1.23),columnspacing=0.5,handletextpad=0.5, handlelength=1)

fig.savefig("joined_sending_rate.pdf", dpi=720)