import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import os

plt.rcParams['text.usetex'] = False

ROOT_PATH = "/home/mihai/mininettestbed/nooffload/results_fairness_intra_rtt_async/fifo" 
PROTOCOLS = ['cubic', 'bbr', 'orca', 'sage', 'bbr3', 'pcc']  # All protocols included
BWS = [100]
DELAYS = [10, 40, 70, 100]  # Using fewer delays for clarity
QMULTS = [0.2, 1, 4]  # 3 queue size values for Y-axis
RUNS = [1, 2, 3, 4, 5]
LOSSES = [0]

# Define distinct colors for each protocol
protocol_colors = {
    'cubic': 'blue',
    'bbr': 'green',
    'orca': 'red',
    'sage': 'purple',
    'bbr3': 'orange',
    'pcc': 'brown'
}

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')  # Create 3D axis

# Loop over each protocol and qmult to plot its results, connecting RTT values
for protocol in PROTOCOLS:
    data = []
    for bw in BWS:
        for mult in QMULTS:  # Fix the queue size (`qmult`) axis and connect RTT values
            for delay in DELAYS:
                duration = 2 * delay
                start_time = 2 * delay
                end_time = 3 * delay
                keep_last_seconds = int(0.25 * delay)

                BDP_IN_BYTES = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
                BDP_IN_PKTS = BDP_IN_BYTES / 1500

                goodput_ratios_20 = []
                goodput_ratios_total = []

                for run in RUNS:
                    PATH = f"{ROOT_PATH}/Dumbell_{bw}mbit_{delay}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{run}"
                    if os.path.exists(PATH + '/csvs/x1.csv') and os.path.exists(PATH + '/csvs/x2.csv'):
                        receiver1_total = pd.read_csv(PATH + '/csvs/x1.csv').reset_index(drop=True)
                        receiver2_total = pd.read_csv(PATH + '/csvs/x2.csv').reset_index(drop=True)

                        receiver1_total['time'] = receiver1_total['time'].apply(lambda x: int(float(x)))
                        receiver2_total['time'] = receiver2_total['time'].apply(lambda x: int(float(x)))

                        receiver1_total = receiver1_total[(receiver1_total['time'] > start_time) & (receiver1_total['time'] < end_time)]
                        receiver2_total = receiver2_total[(receiver2_total['time'] > start_time) & (receiver2_total['time'] < end_time)]

                        receiver1_total = receiver1_total.drop_duplicates('time')
                        receiver2_total = receiver2_total.drop_duplicates('time')
                        receiver1 = receiver1_total[receiver1_total['time'] >= end_time - keep_last_seconds].reset_index(drop=True)
                        receiver2 = receiver2_total[receiver2_total['time'] >= end_time - keep_last_seconds].reset_index(drop=True)

                        receiver1_total = receiver1_total.set_index('time')
                        receiver2_total = receiver2_total.set_index('time')

                        receiver1 = receiver1.set_index('time')
                        receiver2 = receiver2.set_index('time')

                        total = receiver1_total.join(receiver2_total, how='inner', lsuffix='1', rsuffix='2')[['bandwidth1', 'bandwidth2']]
                        partial = receiver1.join(receiver2, how='inner', lsuffix='1', rsuffix='2')[['bandwidth1', 'bandwidth2']]

                        goodput_ratios_20.append(partial.min(axis=1) / partial.max(axis=1))
                        goodput_ratios_total.append(total.min(axis=1) / total.max(axis=1))
                    else:
                        print(f"Folder {PATH} not found.")

                if len(goodput_ratios_20) > 0 and len(goodput_ratios_total) > 0:
                    goodput_ratios_20 = np.concatenate(goodput_ratios_20, axis=0)
                    goodput_ratios_total = np.concatenate(goodput_ratios_total, axis=0)

                    if len(goodput_ratios_20) > 0 and len(goodput_ratios_total) > 0:
                        data_entry = [protocol, bw, delay, mult, goodput_ratios_20.mean(), goodput_ratios_20.std(), goodput_ratios_total.mean(), goodput_ratios_total.std()]
                        data.append(data_entry)

    # Convert to DataFrame for processing
    summary_data = pd.DataFrame(data, columns=['protocol', 'bandwidth', 'delay', 'qmult', 'goodput_ratio_20_mean', 'goodput_ratio_20_std', 'goodput_ratio_total_mean', 'goodput_ratio_total_std'])

    # Create a "wave" plot by connecting RTT values (delay) across the fixed qmults for each protocol
    for mult in QMULTS:
        protocol_data = summary_data[summary_data['qmult'] == mult]
        # Sort by delay (RTT) to ensure lines are connected in the right order
        protocol_data = protocol_data.sort_values(by='delay')
        
        # Plot RTT (delay) vs Queue Size (qmult) vs Goodput Ratio, connecting RTT values
        ax.plot(protocol_data['delay'], [mult] * len(protocol_data['delay']), protocol_data['goodput_ratio_20_mean'], 
                color=protocol_colors[protocol], linestyle='-', linewidth=2)  # Thicker lines for readability

# Set the Y-axis to a logarithmic scale to ensure equidistant appearance of `qmult`
ax.set_yscale('log')

# Set equidistant Y-axis ticks for the queue size (`qmult`) axis
ax.set_yticks([0.2, 1, 4])
ax.set_yticklabels(['0.2', '1', '4'])

# Set 3D plot labels and title
ax.set_xlabel('RTT (ms)')
ax.set_ylabel('Queue Size (qmult)')
ax.set_zlabel('Goodput Ratio')
ax.set_title('3D Plot of RTT vs Queue Size and Goodput Ratio (Connecting RTT)')

# Rotate the view to give the wave-like appearance
ax.view_init(elev=30, azim=45)  # Adjusted angle for better readability

# Show the 3D plot
plt.show()
