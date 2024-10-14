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
        #ADD An ADDITIONAL SPECIAL CASE IF NEEDED 
        
        if flow[-2] == 'orca':
            # Convert sender output into csv
            df = parse_orca_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            # Convert receiver output into csv
            df = parse_orca_output(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver),index=False)
        elif flow[-2] == 'sage':
            # Convert sender output into csv
            df = parse_orca_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

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

            # Convert receiver output into csv
            df = parse_iperf_json(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" % (csv_path, receiver), index=False)


def plot_all(path: str, tarffic_config) -> None:
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
    # Initialize figure with 3 subplots: one for goodput, one for RTT, and one for CWND
    fig, axs = plt.subplots(7, 1, figsize=(10, 30))  
    printDebug("Flows: ", tarffic_config)
    # Iterate over the number of flows and plot the metrics on the same graph
    for flow in tarffic_config:
        flow_client = flow['source']  # Client flow name like 'c1', 'c2', etc.
        flow_server = flow['dest']  # Server flow name like 'x1', 'x2', etc.
        
        client_file_path = os.path.join(path, f'{flow_client}_output.txt')
        server_file_path = os.path.join(path, f'{flow_server}_output.txt')
        
        if not os.path.exists(server_file_path):
            print(f"File {server_file_path} not found!")
            continue
        
        # Parse iperf3 server output to get goodput
        if flow in IPERF:
            df_server = parse_iperf_json(server_file_path, 0)
            df_client = parse_iperf_json(client_file_path, 0) 

        if flow in ORCA:
            df_server = parse_orca_output(server_file_path, 0)
            df_server = parse_orca_output(client_file_path, 0)
        # Parse iperf3 client output to get RTT and CWND

        # Add the corresponding start time to the time column to adjust the time series for both client and server
        df_server['time'] = df_server['time'] + flow['start']
        if not df_client.empty:
            df_client['time'] = df_client['time'] + flow['start']
        



        # Plot goodput (throughput measured at the server)
        if 'bandwidth' in df_server.columns:    
            axs[0].plot(df_server['time'], df_server['bandwidth'], label=f'{flow_server} Goodput')

        axs[1].plot(df_client['time'], df_client['bandwidth'], label=f'{flow_client} CWND')
        
        axs[2].plot(df_client['time'], df_client['transferred'], label=f'{flow_client} Bytes')

        axs[3].plot(df_client['time'], df_client['cwnd'], label=f'{flow_client} CWND')
        
        axs[4].plot(df_client['time'], df_client['retr'], label=f'{flow_client} Retransmits')

        axs[5].plot(df_client['time'], df_client['rtt'], label=f'{flow_client} RTT')
        
        axs[6].plot(df_client['time'], df_client['rttvar'], label=f'{flow_client} Rttvar')
    
    # Set titles and labels for the subplots
    titles = ['Goodput (Mbps)', 'Throughput (Mbps)', 'Bytes', 'CWND (MSS)',
              'Retransmits', 'RTT (ms)', 'RTT Variance (ms)']
    y_labels = ['Goodput (Mbps)', 'Throughput (Mbps)', 'Bytes', 'CWND (MSS)',
                'Retransmits (segments)', 'RTT (ms)', 'RTT Variance (ms)']

    for i, ax in enumerate(axs):
        ax.set_title(titles[i])
        ax.set_xlabel('Time (s)')
        ax.set_ylabel(y_labels[i])
        ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)  # Move legend outside the plot

    # Adjust layout and save the figure
    plt.tight_layout(rect=[0, 0, 0.85, 1])  # Leave space for the legend on the right
    output_file = os.path.join(path, 'flow_metrics.pdf')
    plt.savefig(output_file)
    print(f"Plot saved to {output_file}")

    