import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scienceplots

# use the science style
plt.style.use('science')
plt.rcParams['text.usetex'] = True

# adjust these paths/modules as needed
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)
from core.config import *
from core.plotting import *

BW = 50
DELAY = 50
QMULT = 1
RUN = 2
BDP_IN_BYTES = int(BW * (2**20) * 2 * DELAY * 1e-3 / 8)
BDP_IN_PKTS = BDP_IN_BYTES / 1500

start_time = 105
end_time   = 225
LINEWIDTH  = 0.7

# prepare the figure: two rows stacked, each 8×4 inches
fig, (ax1, ax2) = plt.subplots(
    nrows=2, ncols=1,
    figsize=(12, 3),
    sharex=True
)

final_handles = []
final_labels  = []
times = list(range(start_time, end_time + 1, 15))

ax = ax1
ax_rtt_top = ax.twinx()
ROOT_RTT = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_leo/fifo"
for protocol in PROTOCOLS_LEO:
    p = PROTOCOLS_FRIENDLY_NAME_LEO[protocol]
    path = f"{ROOT_RTT}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT*BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{RUN}"
    with open(os.path.join(path, "emulation_info.json")) as f:
        emu = json.load(f)
    bw_top = [x[-1][1] for x in emu['flows'] if start_time<=x[4]<=end_time and x[6]=='tbf']
    rtt_top = [x[-1][2] for x in emu['flows'] if start_time<=x[4]<=end_time and x[6]=='netem']
    csv = os.path.join(path, 'csvs/c1.csv')
    if os.path.exists(csv):
        df = (pd.read_csv(csv)
              .assign(time=lambda d: d['time'].astype(float).astype(int))
              .query("@start_time<time<@end_time")
              .drop_duplicates('time').set_index('time'))
        ax.plot(df.index+1, df['bandwidth'], color=COLORS_LEO[protocol], lw=LINEWIDTH, label=p)
# plot steps
ax.step(times, bw_top, where='post', color='black', lw=0.7, alpha=0.5)
ax_rtt_top.step(times, rtt_top, where='post', color='red', lw=0.7, alpha=0.5, linestyle='--')
fig.supylabel('Sending Rate (Mbps)', x=0.075)  # adjust x so it sits nicely
ax_rtt_top.set_ylabel('RTT (ms)')

for h,l in zip(*ax.get_legend_handles_labels()):
    if l not in final_labels: final_handles.append(h); final_labels.append(l)
for h,l in zip(*ax_rtt_top.get_legend_handles_labels()):
    if l not in final_labels: final_handles.append(h); final_labels.append(l)
ax.set_xlabel('Time (s)')
ax = ax2
# two extra y-axes
ax_loss = ax.twinx()
ax_rtt = ax.twinx()
# shift third axis
ax_rtt.spines['right'].set_position(('outward', 50))
ROOT_LOSS = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_loss_leo/fifo"
for protocol in PROTOCOLS_LEO:
    p = PROTOCOLS_FRIENDLY_NAME_LEO[protocol]
    # load loss experiment
    path_loss = f"{ROOT_LOSS}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT*BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{RUN}"
    with open(os.path.join(path_loss, 'emulation_info.json')) as f:
        emu_loss = json.load(f)
    bw_loss = [x[-1][1] for x in emu_loss['flows'] if start_time<=x[4]<=end_time and x[6]=='tbf']
    loss = [x[-1][-2] for x in emu_loss['flows'] if start_time<=x[4]<=end_time and x[6]=='netem']
    # load RTT experiment for same protocol
    path_rtt = f"{ROOT_RTT}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT*BDP_IN_PKTS)}pkts_0loss_1flows_22tcpbuf_{protocol}/run{RUN}"
    with open(os.path.join(path_rtt, 'emulation_info.json')) as f:
        emu_rtt = json.load(f)
    rtt = [x[-1][2] for x in emu_rtt['flows'] if start_time<=x[4]<=end_time and x[6]=='netem']
    # senders
    csv = os.path.join(path_loss, 'csvs/c1.csv')
    if os.path.exists(csv):
        df = (pd.read_csv(csv)
              .assign(time=lambda d: d['time'].astype(float).astype(int))
              .query("@start_time<time<@end_time")
              .drop_duplicates('time').set_index('time'))
        ax.plot(df.index+1, df['bandwidth'], color=COLORS_LEO[protocol], lw=LINEWIDTH, label=p)
# overlay steps
ax.step(times, bw_loss, where='post', color='black', lw=0.7, alpha=0.5, label='link capacity')
ax_rtt.step(times, rtt, where='post', color='red', lw=0.7, alpha=0.5, linestyle='--', label='base RTT')
ax_loss.step(times, loss, where='post', color='blue', lw=0.7, alpha=0.5, linestyle='-.', label='loss rate')

# labels
ax_rtt.set_ylabel('RTT (ms)')
ax_loss.set_ylabel('Loss (\%)')
# collect legend handles
for h,l in zip(*ax.get_legend_handles_labels()):
    if l not in final_labels: final_handles.append(h); final_labels.append(l)
for h,l in zip(*ax_rtt.get_legend_handles_labels()):
    if l not in final_labels: final_handles.append(h); final_labels.append(l)
for h,l in zip(*ax_loss.get_legend_handles_labels()):
    if l not in final_labels: final_handles.append(h); final_labels.append(l)
ax1.set_xlim(104, 226)
ax2.set_xlim(104, 226)
# final adjust
ax2.set_xlabel('Time (s)')
fig.legend(final_handles, final_labels, ncol=8, loc='upper center', bbox_to_anchor=(0.5, 1.00))

fig.savefig('responsiveness_bw_rtt_loss_combined.pdf', dpi=300)
