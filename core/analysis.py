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
        start_time = int(flow[-3])
        
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
        else:
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

