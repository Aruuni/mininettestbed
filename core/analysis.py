import json
from core.parsers import *
from core.utils import *
import pandas as pd
import matplotlib.pyplot as plt

def process_raw_outputs(path):
    with open(path + '/emulation_info.json', 'r') as fin:
        emulation_info = json.load(fin)

    flows = emulation_info['flows']
    flows = list(filter(lambda flow: flow[5] != 'netem' and flow[5] != 'tbf', flows))
    flows.sort(key=lambda x: x[-2])

    csv_path = path + "/csvs"
    mkdirp(csv_path)
    change_all_user_permissions(path)
    for flow in flows:
        sender = str(flow[0])
        receiver = str(flow[1])
        sender_ip = str(flow[2])
        receiver_ip = str(flow[3])
        start_time = int(flow[-4])
        
        if flow[-2] in ORCA:
            # Convert sender output into csv
            df = parse_orca_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            df = parse_ss_output(path+"/%s_ss.csv" % sender, start_time)
            df.to_csv("%s/%s_ss.csv" % (csv_path,sender), index=False)
            # Convert receiver output into csv
            df = parse_orca_output(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver),index=False)
        elif flow[-2] == 'aurora':
            # Convert sender output into csv
            df = parse_aurora_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            # Convert receiver output into csv
            df = parse_aurora_output(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver),index=False)
        # WILL ONLY WORK WITH SYSTEM CC
        elif flow[-2] in IPERF:
            # Convert sender output into csv
            df = parse_iperf_json(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" % (csv_path,sender), index=False)
            
            df = parse_ss_output(path+"/%s_ss.csv" % sender, start_time)
            df.to_csv("%s/%s_ss.csv" % (csv_path,sender), index=False)
            
            # Convert receiver output into csv
            df = parse_iperf_json(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver), index=False)


def plot_all(path: str, flows:dict) -> None:
    """
    This function plots goodput (server-side throughput), RTT, and CWND for each flow from the iperf3 output files.
    All flows are plotted on the same graph for each variable (goodput, RTT, and CWND),
    and their time series are adjusted based on their start times.
    TODO - remove the hardcoded values for the number of flows and the start times
    Args:
    path (str): The directory where the iperf3 output files are located.
    num_flows (int): The number of flows to plot.
    start_times (list): A list of start times for each flow, where start_times[i] corresponds to the start time for flow 'c(i+1)'.
    """
    fig, axs = plt.subplots(9, 1, figsize=(17, 30))  
    #fig.suptitle(, fontsize=16)
    for flow in flows:
        flow_client = flow['src']  # Client flow name like 'c1', 'c2', etc.
        flow_server = flow['dst']  # Server flow name like 'x1', 'x2', etc.
        
        df_client = pd.read_csv(os.path.join(path, f'csvs/{flow_client}.csv'))
        df_ss_client = pd.read_csv(os.path.join(path, f'csvs/{flow_client}_ss.csv'))
        df_server = pd.read_csv(os.path.join(path, f'csvs/{flow_server}.csv'))

        axs[0].plot(df_server['time'], df_server['bandwidth'], label=f'{flow_server} Goodput')
        axs[1].plot(df_client['time'], df_client['bandwidth'], label=f'{flow_client} CWND')
        if 'transferred' in df_client.columns:
            axs[2].plot(df_client['time'], df_client['transferred'], label=f'{flow_client} Bytes')
        else:
             axs[2].plot(df_client['time'], df_client['bytes'], label=f'{flow_client} Bytes')
        
        if 'cwnd' in df_client.columns:
            axs[3].plot(df_client['time'], df_client['cwnd'], label=f'{flow_client} CWND')
        else:
            axs[3].plot(df_ss_client['time'], df_ss_client['cwnd'], label=f'{flow_client} CWND')

        if 'retr' in df_client.columns:
            axs[4].plot(df_client['time'], df_client['retr'], label=f'{flow_client} Retransmits')
        else:
            axs[4].plot(df_ss_client['time'], df_ss_client['retr'], label=f'{flow_client} Retransmits')
        if 'srtt' in df_client.columns:
            axs[5].plot(df_client['time'], df_client['srtt'], label=f'{flow_client} RTT')
        else:
            axs[5].plot(df_ss_client['time'], df_ss_client['srtt'], label=f'{flow_client} RTT')
        if 'rttvar' in df_client.columns:
            axs[6].plot(df_client['time'], df_client['rttvar'], label=f'{flow_client} Rttvar')
        else:
            axs[6].plot(df_ss_client['time'], df_ss_client['rttvar'], label=f'{flow_client} Rttvar')
    
    # Now process and plot queue sizes (8th subplot)
    queue_dir = os.path.join(path, 'queues')  # Specify the folder containing the queue files
    queue_files = [f for f in os.listdir(queue_dir) if f.endswith('.txt')]
    
    for queue_file in queue_files:
        queue_path = os.path.join(queue_dir, queue_file)
        
        df_queue = pd.read_csv(queue_path)
        df_queue['time'] = pd.to_numeric(df_queue['time'], errors='coerce')
        df_queue['time'] = df_queue['time'] - df_queue['time'].min()

        # Convert 'b', 'K', and other units to numeric values if necessary
        df_queue['root_pkts'] = df_queue['root_pkts'].str.replace('b', '').str.replace('K', '000').str.replace('M', '000000').str.replace('G', '000000000').astype(float)
        df_queue['root_drp'] = df_queue['root_drp'].fillna(0).astype(float)  # Handle missing drop values

        # Convert root_pkts to packets from bytes assuming 1500 bytes per packet
        df_queue['root_pkts'] = df_queue['root_pkts'] / 1500

        # Calculate the interval drops (difference between consecutive drops)
        df_queue['interval_drops'] = df_queue['root_drp'].diff().fillna(0)

        axs[7].plot(df_queue['time'], df_queue['root_pkts'], label=f'{queue_file} - root_pkts')
        axs[8].plot(df_queue['time'], df_queue['interval_drops'], linestyle='--', label=f'{queue_file} - root_drp')


def plot_all(path: str, flows: dict) -> None:
    """
    This function plots goodput (server-side throughput), RTT, and CWND for each flow from the iperf3 output files.
    All flows are plotted on the same graph for each variable (goodput, RTT, and CWND),
    and their time series are adjusted based on their start times.
    Args:
    path (str): The directory where the iperf3 output files are located.
    flows (dict): A dictionary containing the flow information with source and destination mappings.
    """
    fig, axs = plt.subplots(9, 1, figsize=(16, 36))

    for flow in flows:
        flow_client = flow['src']  # Client flow name like 'c1', 'c2', etc.
        flow_server = flow['dst']  # Server flow name like 'x1', 'x2', etc.

        df_client = pd.read_csv(os.path.join(path, f'csvs/{flow_client}.csv'))
        df_ss_client = pd.read_csv(os.path.join(path, f'csvs/{flow_client}_ss.csv'))
        df_server = pd.read_csv(os.path.join(path, f'csvs/{flow_server}.csv'))

        axs[0].plot(df_server['time'], df_server['bandwidth'], label=f'{flow_server} Goodput')
        axs[1].plot(df_client['time'], df_client['bandwidth'], label=f'{flow_client} CWND')
        if 'transferred' in df_client.columns:
            axs[2].plot(df_client['time'], df_client['transferred'], label=f'{flow_client} Bytes')
        else:
            axs[2].plot(df_client['time'], df_client['bytes'], label=f'{flow_client} Bytes')

        if 'cwnd' in df_client.columns:
            axs[3].plot(df_client['time'], df_client['cwnd'], label=f'{flow_client} CWND')
        else:
            axs[3].plot(df_ss_client['time'], df_ss_client['cwnd'], label=f'{flow_client} CWND')

        if 'retr' in df_client.columns:
            axs[4].plot(df_client['time'], df_client['retr'], label=f'{flow_client} Retransmits')
        else:
            axs[4].plot(df_ss_client['time'], df_ss_client['retr'], label=f'{flow_client} Retransmits')

        if 'srtt' in df_client.columns:
            axs[5].plot(df_client['time'], df_client['srtt'], label=f'{flow_client} RTT')
        else:
            axs[5].plot(df_ss_client['time'], df_ss_client['srtt'], label=f'{flow_client} RTT')
            
        if 'rttvar' in df_client.columns:
            axs[6].plot(df_client['time'], df_client['rttvar'], label=f'{flow_client} Rttvar')
        else:
            axs[6].plot(df_ss_client['time'], df_ss_client['rttvar'], label=f'{flow_client} Rttvar')

    queue_dir = os.path.join(path, 'queues')  # Specify the folder containing the queue files
    queue_files = [f for f in os.listdir(queue_dir) if f.endswith('.txt')]

    for queue_file in queue_files:
        queue_path = os.path.join(queue_dir, queue_file)

        df_queue = pd.read_csv(queue_path)
        df_queue['time'] = pd.to_numeric(df_queue['time'], errors='coerce')
        df_queue['time'] = df_queue['time'] - df_queue['time'].min()

        # Convert units to numeric values
        df_queue['root_pkts'] = (
            df_queue['root_pkts']
            .str.replace('b', '')
            .str.replace('K', '000')
            .str.replace('M', '000000')
            .str.replace('G', '000000000')
            .astype(float)
        )
        df_queue['root_drp'] = df_queue['root_drp'].fillna(0).astype(float)

        df_queue['root_pkts'] = df_queue['root_pkts'] / 1500
        df_queue['interval_drops'] = df_queue['root_drp'].diff().fillna(0)

        axs[7].plot(df_queue['time'], df_queue['root_pkts'], label=f'{queue_file} - root_pkts')
        axs[8].plot(df_queue['time'], df_queue['interval_drops'], linestyle='--', label=f'{queue_file} - root_drp')

    # Set titles, labels, and enable grids
    titles = [
        'Goodput (Mbps)', 'Throughput (Mbps)', 'Bytes', 'CWND (MSS)',
        'Retransmits', 'RTT (ms)', 'RTT Variance (ms)', 'Queue Sizes (Packets)', 'Queue drops (Packets)'
    ]
    y_labels = [
        'Goodput (Mbps)', 'Throughput (Mbps)', 'Bytes', 'CWND (MSS)',
        'Retransmits (segments)', 'RTT (ms)', 'RTT Variance (ms)', 'Queue Size (pkts)', 'Queue drops (Packets)'
    ]

    for i, ax in enumerate(axs):
        ax.set_title(titles[i])
        ax.set_xlabel('Time (s)')
        ax.set_ylabel(y_labels[i])
        ax.legend(loc='upper left')
        ax.grid(True)

        # Dynamically set x limits based on data
        all_x_values = []
        for line in ax.get_lines():
            all_x_values.extend(line.get_xdata())
        if all_x_values:
            x_min = 0  # Start from 0
            x_max = max(all_x_values)  # Maximum value in the data
            ax.set_xlim(x_min, x_max)

        # Dynamically set y limits
        y_min, y_max = 0, ax.get_ylim()[1]  # Start from 0 to current max of y-axis
        ax.set_ylim(y_min, y_max)

        # Adjust time ticks dynamically
        time_max = x_max
        time_interval = max(1, int(time_max / 20))  # Adjust ticks to ~20 intervals
        ax.xaxis.set_major_locator(plt.MultipleLocator(time_interval))

    # Adjust layout and save the figure
    plt.tight_layout(rect=[0, 0, 1, 1], pad=1.0)
    output_file = os.path.join(path, (path.split('/fifo/')[1]).split('/run')[0] + '.pdf')

    plt.savefig(output_file)
    print(f"Plot saved to {output_file}")
    plt.close()



def plot_all_ns3(path: str) -> None:
    """
    This function plots Goodput, RTT, CWND, Throughput, and Queue Size for each flow from NS3 experiment output files.
    All flows are plotted on the same graph for each variable.

    Args:
    path (str): The directory where the NS3 output files are located.
    """
    fig, axs = plt.subplots(6, 1, figsize=(17, 30))

    # Identify files by prefix and metric
    file_prefixes = set(f.split('-')[0] for f in os.listdir(path) if f.endswith('.csv') and '-' in f)
    metrics = ['goodput', 'throughput', 'cwnd', 'rtt', 'bytes']

    for prefix in file_prefixes:
        for idx, metric in enumerate(metrics):
            metric_file = os.path.join(path, f'{prefix}-{metric}.csv')
            if os.path.exists(metric_file):
                df = pd.read_csv(metric_file)
                axs[idx].plot(df['time'], df[df.columns[1]], label=f'{prefix} {metric.capitalize()}')

    # Queue Size plot
    # queue_file = os.path.join(path, 'queueSize.csv')
    # if os.path.exists(queue_file):
    #     df_queue = pd.read_csv(queue_file)
    #     df_queue['time'] = pd.to_numeric(df_queue['time'], errors='coerce')
    #     df_queue['time'] = df_queue['time'] - df_queue['time'].min()
    #     df_queue['root_pkts'] = df_queue['root_pkts'].astype(float) 

    #     axs[5].plot(df_queue['time'], df_queue['root_pkts'], label='Queue Size')

    # Titles and labels
    titles = ['Goodput (Mbps)', 'Throughput (Mbps)', 'CWND (MSS)', 'RTT (ms)', 'Bytes In Flight', 'Queue Size (Packets)']
    y_labels = ['Goodput (Mbps)', 'Throughput (Mbps)', 'CWND (MSS)', 'RTT (ms)', 'Bytes In Flight', 'Queue Size (pkts)']

    for i, ax in enumerate(axs):
        ax.set_title(titles[i])
        ax.set_xlabel('Time (s)')
        ax.set_ylabel(y_labels[i])
        ax.legend(loc='upper left')

    # Adjust layout and save the figure
    plt.tight_layout(rect=[0, 0, 1, 1], pad=1.0)
    output_file = os.path.join(path, 'ns3_experiment_results.pdf')

    plt.savefig(output_file)
    print(f"NS3 experiment plots saved to {output_file}")

def plot_all_ns3_responsiveness(path: str) -> None:
    """
    This function plots Goodput, RTT, Throughput, CWND, Bytes In Flight, and Queue Size for each flow from NS3 experiment output files.
    It also includes TBF bandwidth on the goodput plot and Netem RTT on the RTT plot. Netem loss is plotted on a secondary y-axis of the Goodput plot.
    
    Args:
    path (str): The directory where the NS3 output files are located.
    """
    fig, axs = plt.subplots(5, 1, figsize=(17, 30))
    # Set global font sizes
    plt.rcParams.update({
        'font.size': 16,         # General font size
        'axes.titlesize': 20,    # Title font size
        'axes.labelsize': 16,    # Axis label font size
        'xtick.labelsize': 16,   # X-axis tick font size
        'ytick.labelsize': 16,   # Y-axis tick font size
        'legend.fontsize': 20,   # Legend font size
    })
    # Identify files by extracting flow name and metric
    csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
    metrics = ['goodput', 'rtt', 'throughput', 'cwnd', 'bytes']
    file_mapping = {}

    # Create a mapping of flow name to metric files
    for file in csv_files:
        if '-' in file and file.endswith('.csv'):
            parts = file.split('-')
            if len(parts) < 3:
                continue  # Skip files that do not match the expected format

            flow_name = f"{parts[0]}-{parts[1]}"  # e.g., TcpBbr-1
            metric = parts[2].split('.')[0]  # e.g., goodput

            if metric in metrics:
                if flow_name not in file_mapping:
                    file_mapping[flow_name] = {}
                file_mapping[flow_name][metric] = file

    # Load emulation info from JSON
    emulation_info_file = os.path.join(path, 'emulation_info.json')
    with open(emulation_info_file, 'r') as f:
        emulation_info = json.load(f)

    netem_bw = []
    netem_rtt = []
    netem_loss = []

    # Extract TBF and Netem changes
    for flow in emulation_info['flows']:
        if flow[6] == 'tbf':
            netem_bw.append([flow[4],flow[7][1]])
        if flow[6] == 'netem' and flow[7]:
            netem_rtt.append([flow[4], flow[7][2]])
            netem_loss.append([flow[4], (lambda x: x * 100 if x is not None else None)(flow[7][6])])

    # Plot each metric for each flow
    for flow_name, metrics_files in file_mapping.items():
        if 'goodput' in metrics_files:
            df = pd.read_csv(os.path.join(path, metrics_files['goodput']))
            axs[0].plot(df['time'], df['goodput'], label=f'{flow_name} Goodput')
            axs[0].set_xlim(df['time'].min(), df['time'].max())  # Adjust x-axis to data range

        if 'rtt' in metrics_files:
            df = pd.read_csv(os.path.join(path, metrics_files['rtt']))
            axs[1].plot(df['time'], df['rtt'], label=f'{flow_name} RTT')
            axs[1].set_xlim(df['time'].min(), df['time'].max())  # Adjust x-axis to data range

        if 'throughput' in metrics_files:
            df = pd.read_csv(os.path.join(path, metrics_files['throughput']))
            axs[2].plot(df['time'], df['throughput'], label=f'{flow_name} Throughput')
            axs[2].set_xlim(df['time'].min(), df['time'].max())  # Adjust x-axis to data range
    # Plot both CWND and Bytes In Flight on the same subplot
    if 'cwnd' in metrics_files or 'bytes' in metrics_files:
        cwnd_df = pd.read_csv(os.path.join(path, metrics_files['cwnd'])) if 'cwnd' in metrics_files else pd.DataFrame()
        bytes_df = pd.read_csv(os.path.join(path, metrics_files['bytes'])) if 'bytes' in metrics_files else pd.DataFrame()

        if not cwnd_df.empty and 'cwnd' in cwnd_df.columns:
            cwnd_df['cwnd_packets'] = cwnd_df['cwnd']
            axs[3].plot(cwnd_df['time'], cwnd_df['cwnd_packets'], label=f'{flow_name} CWND (packets)')
            axs[3].set_xlim(df['time'].min(), df['time'].max())  # Adjust x-axis to data range
        if not bytes_df.empty and 'bytes' in bytes_df.columns:
            bytes_df['bytes_packets'] = bytes_df['bytes']
            axs[3].plot(bytes_df['time'], bytes_df['bytes_packets'], label=f'{flow_name} Packets in flight', linestyle='--')

   
    bw_df = pd.DataFrame(netem_bw, columns=["time", "max_bw"])
    bw_df.sort_values(by="time", inplace=True)
    if not bw_df['max_bw'][0] == None:
        last_time = bw_df['time'].max() + 10
        last_bw = bw_df['max_bw'].iloc[-1]
        bw_df = pd.concat([bw_df, pd.DataFrame([{"time": last_time, "max_bw": last_bw}])], ignore_index=True)

        bw_df.set_index('time', inplace=True)
        axs[0].step(bw_df.index, bw_df['max_bw'], label='Available Bandwidth', color='black', linestyle='--', where='post')

    rtt_df = pd.DataFrame(netem_rtt, columns=["time", "rtt"])
    rtt_df.sort_values(by="time", inplace=True)
    if not rtt_df['rtt'][0] == None:
        last_time = rtt_df['time'].max() + 10
        last_rtt = rtt_df['rtt'].iloc[-1]
        rtt_df = pd.concat([rtt_df, pd.DataFrame([{"time": last_time, "rtt": last_rtt}])], ignore_index=True)
       
        rtt_df.set_index('time', inplace=True)
        axs[1].step(rtt_df.index, rtt_df['rtt'], label='Base RTT', color='black', linestyle='--', where='post')

    # Plot Netem loss on the right y-axis of the Goodput plot
    loss_df = pd.DataFrame(netem_loss, columns=["time", "loss"])
    loss_df.sort_values(by="time", inplace=True)
    if not loss_df['loss'][0] == None:
        last_time = loss_df['time'].max() + 10
        last_loss = loss_df['loss'].iloc[-1]
        loss_df = pd.concat([loss_df, pd.DataFrame([{"time": last_time, "loss": last_loss}])], ignore_index=True)

        ax_loss = axs[0].twinx()
        ax_loss.step(loss_df['time'], loss_df['loss'], label='Loss (%)', color='red', linestyle='--', where='post')
        ax_loss.set_ylabel('Loss (%)', color='red')
        ax_loss.legend(loc='upper right')
        ax_loss.set_ylim(bottom=0)
        axs[0].set_ylim(bottom=0)

    # Queue size plot
    queue_file = os.path.join(path, 'queueSize.csv')
    if os.path.exists(queue_file):
        df_queue = pd.read_csv(queue_file)
        df_queue['time'] = pd.to_numeric(df_queue['time'], errors='coerce')
        df_queue['time'] = df_queue['time'] - df_queue['time'].min()
        df_queue['root_pkts'] = df_queue['root_pkts'].astype(float)
        axs[4].plot(df_queue['time'], df_queue['root_pkts'], label='Queue Size')
        axs[4].set_xlim(df['time'].min(), df['time'].max())  # Adjust x-axis to data range
    # Titles and labels
    titles = ['Goodput (Mbps)', 'RTT (ms)', 'Throughput (Mbps)', 'CWND and in-flight (Packets)', 'Queue Size (Packets)']
    y_labels = ['Goodput (Mbps)', 'RTT (ms)', 'Throughput (Mbps)', 'Packets', 'Queue Size (packets)']

    for i, ax in enumerate(axs):
        ax.set_title(titles[i])
        ax.set_xlabel('Time (s)', fontsize=16)
        ax.set_ylabel(y_labels[i])
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc='upper left')
                # Set x-ticks to show every 25 seconds
        ax.set_xticks(range(0, 325, 25))
        ax.grid(True)

    # Adjust layout and save the figure
    plt.tight_layout(rect=[0, 0, 1, 1], pad=1.0)
    output_file = os.path.join(path, 'ns3_experiment_results.pdf')

    plt.savefig(output_file)
    printBlueBackground(f"NS3 experiment plots saved to {output_file}")
    plt.close()

def plot_all_mininet_responsiveness(path: str) -> None:
    """
    This function plots Goodput, RTT, Throughput, CWND, Retransmissions, and Queue Size for Mininet experiment output files.
    It also includes TBF bandwidth, Netem RTT, and Netem loss changes from emulation_info.json.
    
    Args:
    path (str): The directory where the Mininet output files are located.
    """
    fig, axs = plt.subplots(7, 1, figsize=(17, 35))

    # File paths
    ss_file = os.path.join(path, 'csvs', 'c1_ss.csv')
    goodput_file = os.path.join(path, 'csvs', 'x1.csv')
    throughput_file = os.path.join(path, 'csvs', 'c1.csv')
    emulation_info_file = os.path.join(path, 'emulation_info.json')
    queue_dir = os.path.join(path, 'queues')

    # Load data
    ss_df = pd.read_csv(ss_file)
    goodput_df = pd.read_csv(goodput_file)
    throughput_df = pd.read_csv(throughput_file)

    # Load emulation info from JSON
    with open(emulation_info_file, 'r') as f:
        emulation_info = json.load(f)

    netem_bw = []
    netem_rtt = []
    netem_loss = []

    # Extract TBF and Netem changes
    for flow in emulation_info['flows']:
        if flow[6] == 'tbf':
            netem_bw.append([flow[4], flow[7][1]])  # Time and bandwidth
        if flow[6] == 'netem' and flow[7]:
            netem_rtt.append([flow[4], flow[7][2]])  # Time and RTT
            netem_loss.append([flow[4], (flow[7][6])])  # Time and loss

    # Plot Goodput
    axs[0].plot(goodput_df['time'], goodput_df['bandwidth'], label='Goodput (Mbps)')
    axs[0].set_title('Goodput (Mbps)')
    axs[0].set_xlabel('Time (s)')
    axs[0].set_ylabel('Goodput (Mbps)')
    axs[0].grid(True)

    # Plot bandwidth changes (TBF) as a step function
    if netem_bw:
        bw_df = pd.DataFrame(netem_bw, columns=["time", "max_bw"])
        bw_df.sort_values(by="time", inplace=True)
        last_time = bw_df['time'].max() + 10
        last_bw = bw_df['max_bw'].iloc[-1]
        bw_df = pd.concat([bw_df, pd.DataFrame([{"time": last_time, "max_bw": last_bw}])], ignore_index=True)
        axs[0].step(bw_df['time'], bw_df['max_bw'], label='Available Bandwidth', color='purple', linestyle='--', where='post')
        axs[2].step(bw_df['time'], bw_df['max_bw'], label='Available Bandwidth', color='purple', linestyle='--', where='post')

    axs[0].legend(loc='upper left')

    # Plot RTT
    axs[1].plot(ss_df['time'], ss_df['srtt'], label='RTT (ms)')
    axs[1].set_title('RTT (ms)')
    axs[1].set_xlabel('Time (s)')
    axs[1].set_ylabel('RTT (ms)')
    axs[1].grid(True)

    # Plot RTT changes (Netem) as a step function
    if netem_rtt:
        rtt_df = pd.DataFrame(netem_rtt, columns=["time", "rtt"])
        rtt_df.sort_values(by="time", inplace=True)
        last_time = rtt_df['time'].max() + 10
        last_rtt = rtt_df['rtt'].iloc[-1]
        rtt_df = pd.concat([rtt_df, pd.DataFrame([{"time": last_time, "rtt": last_rtt}])], ignore_index=True)
        axs[1].step(rtt_df['time'], rtt_df['rtt'], label='Base RTT', color='purple', linestyle='--', where='post')

    axs[1].legend(loc='upper left')

    # Plot Throughput
    axs[2].plot(throughput_df['time'], throughput_df['bandwidth'], label='Throughput (Mbps)',)
    axs[2].set_title('Throughput (Mbps)')
    axs[2].set_xlabel('Time (s)')
    axs[2].set_ylabel('Throughput (Mbps)')
    axs[2].grid(True)
    axs[2].legend(loc='upper left')

    # Plot CWND
    axs[3].plot(ss_df['time'], ss_df['cwnd'], label='CWND (packets)')
    axs[3].set_title('CWND (packets)')
    axs[3].set_xlabel('Time (s)')
    axs[3].set_ylabel('CWND (packets)')
    axs[3].grid(True)
    axs[3].legend(loc='upper left')

    # Plot Retransmissions
    axs[4].plot(throughput_df['time'], throughput_df['retr'], label='Retransmissions')
    axs[4].set_title('Retransmissions')
    axs[4].set_xlabel('Time (s)')
    axs[4].set_ylabel('Retransmissions')
    axs[4].grid(True)
    axs[4].legend(loc='upper left')

    # Plot Netem loss on the right y-axis of the Goodput plot
    if netem_loss:
        loss_df = pd.DataFrame(netem_loss, columns=["time", "loss"])
        loss_df.sort_values(by="time", inplace=True)
        last_time = loss_df['time'].max() + 10
        last_loss = loss_df['loss'].iloc[-1]
        loss_df = pd.concat([loss_df, pd.DataFrame([{"time": last_time, "loss": last_loss}])], ignore_index=True)

        ax_loss = axs[0].twinx()
        ax_loss.step(loss_df['time'], loss_df['loss'], label='Loss (%)', color='green', linestyle='--', where='post')
        ax_loss.set_ylabel('Loss (%)', color='green')
        ax_loss.legend(loc='upper right')
    # Specify the file you want to plot
    target_queue_file = 's2-eth2.txt'
    queue_path = os.path.join(queue_dir, target_queue_file)

    # Check if the file exists before proceeding
    if os.path.exists(queue_path):
        df_queue = pd.read_csv(queue_path)

        # Clean and preprocess the data
        df_queue['time'] = pd.to_numeric(df_queue['time'], errors='coerce')
        df_queue['time'] = df_queue['time'] - df_queue['time'].min()
        df_queue['root_pkts'] = df_queue['root_pkts'].str.replace('b', '').str.replace('K', '000').str.replace('M', '000000').str.replace('G', '000000000').astype(float)
        df_queue['root_pkts'] = pd.to_numeric(df_queue['root_pkts'], errors='coerce').fillna(0) / 1500  # Convert to packets

        # Plot Queue Size
        axs[5].plot(df_queue['time'], df_queue['root_pkts'], label='Queue Size (packets) - s2-eth2.txt')
        axs[5].set_title('Queue Size (Packets)')
        axs[5].set_xlabel('Time (s)')
        axs[5].set_ylabel('Queue Size (Packets)')
        axs[5].grid(True)
        axs[5].legend(loc='upper left')

        # Clean and preprocess the data for drops
        df_queue['root_drp'] = df_queue['root_drp'].fillna(0).astype(float)  # Handle missing drop values
        df_queue['root_drp'] = pd.to_numeric(df_queue['root_drp'], errors='coerce').fillna(0)
        df_queue['interval_drops'] = df_queue['root_drp'].diff().fillna(0)

        # Plot Queue Drops
        axs[6].plot(df_queue['time'], df_queue['interval_drops'], label='Queue Drops - s2-eth2.txt')
        axs[6].set_title('Queue Drops (Packets)')
        axs[6].set_xlabel('Time (s)')
        axs[6].set_ylabel('Drops (Packets)')
        axs[6].grid(True)
        axs[6].legend(loc='upper left')
    else:
        print(f"File {target_queue_file} not found in the 'queues' directory.")


    # Set x-ticks and adjust layout
    for ax in axs:
        ax.set_xticks(range(0, int(max(ss_df['time'].max(), goodput_df['time'].max(), throughput_df['time'].max())) + 1, 25))
        ax.grid(True)

    plt.tight_layout(rect=[0, 0, 1, 1], pad=1.0)
    output_file = os.path.join(path, os.path.join(path, (path.split('/fifo/')[1]).split('/run')[0]+'.pdf'))
    plt.savefig(output_file)
    print(f"Mininet experiment plots saved to {output_file}")
    plt.close()        
    
    
def plot_all_ns3_responsiveness_extra(path: str) -> None:
    """
    Plot Goodput, RTT, Throughput, CWND, Bytes In Flight, and BBR State from NS3 experiment files.
    
    Args:
    path (str): The directory containing CSV files for the NS3 experiment.
    """
    # Identify and load all CSV files
    files = {
        "goodput": os.path.join(path, "TcpBbr-1-goodput.csv"),
        "rtt": os.path.join(path, "TcpBbr-1-rtt.csv"),
        "lastrtt": os.path.join(path, "TcpBbr-1-lastrtt.csv"),
        "throughput": os.path.join(path, "TcpBbr-1-throughput.csv"),
        "cwnd": os.path.join(path, "TcpBbr-1-cwnd.csv"),
        "bytes": os.path.join(path, "TcpBbr-1-bytes.csv"),
        "retransmits": os.path.join(path, "TcpBbr-1-retransmits.csv"),

        "root_pkts": os.path.join(path, "queueSize_0_0.csv"),
        "root_pkts1": os.path.join(path, "queueSize_1_0.csv"),
        "root_pkts2": os.path.join(path, "queueSize_2_0.csv"),
        "root_pkts3": os.path.join(path, "queueSize_2_1.csv"),
        "root_pkts4": os.path.join(path, "queueSize_3_0.csv"),
        "root_pkts5": os.path.join(path, "queueSize_3_1.csv"),


        # "nextRoundDelivered": os.path.join(path,"TcpBbr-1-nextRoundDelivered.csv"),
        # "priorRoundDelivered": os.path.join(path,"TcpBbr-1-priorRoundDelivered.csv"),
        # "bbr_state": os.path.join(path, "TcpBbr-1-bbr_state.csv"),
        "pacingGain": os.path.join(path, "TcpBbr-1-pacingGain.csv"),
        # "m_cycleIndex": os.path.join(path, "TcpBbr-1-m_cycleIndex.csv"),
    }
    # Load emulation info for Netem and TBF data
    emulation_info_file = os.path.join(path, 'emulation_info.json')
    with open(emulation_info_file, 'r') as f:
        emulation_info = json.load(f)

    netem_bw = []
    netem_rtt = []
    netem_loss = []

    for flow in emulation_info['flows']:
        if flow[6] == 'tbf':
            netem_bw.append([flow[4], flow[7][1]])
        if flow[6] == 'netem' and flow[7]:
            netem_rtt.append([flow[4], flow[7][2]])
            netem_loss.append([flow[4], (lambda x: x * 100 if x is not None else None)(flow[7][6])])
    # Load the data into DataFrames
    data = {}
    for metric, file_path in files.items():
        if os.path.exists(file_path):
            data[metric] = pd.read_csv(file_path)

    # Create 6 subplots for the metrics
    fig, axs = plt.subplots(7, 1, figsize=(17, 36))
# Plot Goodput
    if "goodput" in data and "time" in data["goodput"].columns and "goodput" in data["goodput"].columns:
        bw_df = pd.DataFrame(netem_bw, columns=["time", "max_bw"]).sort_values(by="time")
        axs[0].plot(data["goodput"]["time"], data["goodput"]["goodput"], label="Goodput (Mbps)")
        axs[0].step(bw_df['time'], bw_df['max_bw'], label='Available Bandwidth', color='purple', where='post', linestyle='--')
        axs[0].set_title("Goodput (Mbps)")
        axs[0].set_xlabel("Time (s)")
        axs[0].set_ylabel("Goodput (Mbps)")
        axs[0].legend(loc="upper left")
        axs[0].grid(True)
        loss_df = pd.DataFrame(netem_loss, columns=["time", "loss"]).sort_values(by="time")
        ax_loss = axs[0].twinx()
        ax_loss.step(loss_df['time'], loss_df['loss'], label='Loss (%)', color='green', where='post', linestyle='--')
        ax_loss.set_ylabel('Loss (%)', color='green')
        ax_loss.legend(loc='upper right')

    # Plot RTT
    if "rtt" in data and "time" in data["rtt"].columns and "rtt" in data["rtt"].columns:
        rtt_df = pd.DataFrame(netem_rtt, columns=["time", "rtt"]).sort_values(by="time")
        axs[1].step(rtt_df['time'], rtt_df['rtt'], label='Base RTT', color='purple', where='post', linestyle='--')
        #axs[1].plot(data["rtt"]["time"], data["rtt"]["rtt"], label="RTT (ms)")
        axs[1].plot(data["lastrtt"]["time"], data["lastrtt"]["lastrtt"], label="last RTT (ms)", )

        axs[1].set_title("RTT (ms)")
        axs[1].set_xlabel("Time (s)")
        axs[1].set_ylabel("RTT (ms)")
        axs[1].legend(loc="upper left")
        axs[1].grid(True)

    # Plot Throughput
    if "throughput" in data and "time" in data["throughput"].columns and "throughput" in data["throughput"].columns:
        axs[2].plot(data["throughput"]["time"], data["throughput"]["throughput"], label="Throughput (Mbps)")
        axs[2].set_title("Throughput (Mbps)")
        axs[2].set_xlabel("Time (s)")
        axs[2].set_ylabel("Throughput (Mbps)")
        axs[2].legend(loc="upper left")
        axs[2].grid(True)

    # Plot CWND and Bytes in Flight on the same plot
    if "cwnd" in data and "time" in data["cwnd"].columns and "cwnd" in data["cwnd"].columns:
        axs[3].plot(data["cwnd"]["time"], data["cwnd"]["cwnd"]/1500, label="CWND (Packets)")
    if "bytes" in data and "time" in data["bytes"].columns and "bytes" in data["bytes"].columns:
        axs[3].plot(data["bytes"]["time"], data["bytes"]["bytes"]/ 1500, label="Bytes in Flight", linestyle="--")
    axs[3].set_title("CWND and Bytes in Flight")
    axs[3].set_xlabel("Time (s)")
    axs[3].set_ylabel("Packets")
    axs[3].legend(loc="upper left")
    axs[3].grid(True)
    # Plot Queue Size on axs[4]
    if "root_pkts" in data and "time" in data["root_pkts"].columns:
        queue_data = data["root_pkts"]
        queue_data1 = data["root_pkts1"]
        queue_data2 = data["root_pkts2"]
        queue_data3 = data["root_pkts3"]
        queue_data4 = data["root_pkts4"]
        queue_data5 = data["root_pkts5"]

        queue_data["time"] = pd.to_numeric(queue_data["time"], errors="coerce")
        queue_data["time"] = queue_data["time"] - queue_data["time"].min()

        queue_data2["time"] = pd.to_numeric(queue_data2["time"], errors="coerce")
        queue_data2["time"] = queue_data2["time"] - queue_data2["time"].min()
        
        queue_data3["time"] = pd.to_numeric(queue_data3["time"], errors="coerce")
        queue_data3["time"] = queue_data3["time"] - queue_data3["time"].min()

        queue_data1["time"] = pd.to_numeric(queue_data1["time"], errors="coerce")
        queue_data1["time"] = queue_data1["time"] - queue_data1["time"].min()

        queue_data4["time"] = pd.to_numeric(queue_data4["time"], errors="coerce")
        queue_data4["time"] = queue_data4["time"] - queue_data4["time"].min()

        queue_data5["time"] = pd.to_numeric(queue_data5["time"], errors="coerce")
        queue_data5["time"] = queue_data5["time"] - queue_data5["time"].min()


        queue_data["root_pkts"] = queue_data["root_pkts"].astype(float)  # Ensure numeric values
        queue_data1["root_pkts"] = queue_data1["root_pkts"].astype(float)  # Ensure numeric values
        queue_data2["root_pkts"] = queue_data2["root_pkts"].astype(float)  # Ensure numeric values
        queue_data3["root_pkts"] = queue_data3["root_pkts"].astype(float)  # Ensure numeric values
        queue_data4["root_pkts"] = queue_data4["root_pkts"].astype(float)  # Ensure numeric values
        queue_data5["root_pkts"] = queue_data5["root_pkts"].astype(float)  # Ensure numeric values

        axs[4].plot(queue_data["time"], queue_data["root_pkts"], label="Queue Size n0 d0 (Packets)")
        axs[4].plot(queue_data1["time"], queue_data1["root_pkts"], label="Queue Size n1 d0(Packets)")
        axs[4].plot(queue_data2["time"], queue_data2["root_pkts"], label="Queue Size n2 d0(Packets)")
        axs[4].plot(queue_data3["time"], queue_data3["root_pkts"], label="Queue Size n2 d1 (Packets)")
        axs[4].plot(queue_data4["time"], queue_data4["root_pkts"], label="Queue Size n3 d0 (Packets)")
        axs[4].plot(queue_data5["time"], queue_data5["root_pkts"], label="Queue Size n3 d1 (Packets)")
        axs[4].set_title("Queue Size (Packets)")
        axs[4].set_xlabel("Time (s)")
        axs[4].set_ylabel("Queue Size (Packets)")
        axs[4].legend(loc="upper left")
        axs[4].grid(True)

    # Plot BBR State
    if "pacingGain" in data and "time" in data["pacingGain"].columns and "pacingGain" in data["pacingGain"].columns:
        #axs[5].step(data["bbr_state"]["time"], data["bbr_state"]["bbr_state"], label="BBR State")
        axs[5].step(data["pacingGain"]["time"], data["pacingGain"]["pacingGain"], where="post", label="pacingGain")

        axs[5].set_title("pacingGain")
        axs[5].set_xlabel("Time (s)")
        axs[5].set_ylabel("State")
        axs[5].legend(loc="upper left")
        axs[5].grid(True)
        # Plot Throughput

    if "retransmits" in data and "time" in data["retransmits"].columns and "retransmits" in data["retransmits"].columns:
        axs[6].step(data["retransmits"]["time"], data["retransmits"]["retransmits"], where="pre", label="retransmits")
        axs[6].set_title("retransmits")
        axs[6].set_xlabel("Time (s)")
        axs[6].set_ylabel("packets")
        axs[6].legend(loc="upper left")
        axs[6].grid(True)
    for i, ax in enumerate(axs):
        ax.set_xticks(range(0, 315, 15))
        ax.grid(True)


    # Adjust layout and save the figure
    plt.tight_layout()
    output_file = os.path.join(path, "ns3_experiment_results_with_bbr.pdf")
    plt.savefig(output_file)
    printBlue(f"NS3 experiment plots saved to '{output_file}'.")
    plt.close()


    
