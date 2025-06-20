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
        if 'orca' in flow[-2]:
            # Convert sender output into csv
            df = parse_orca_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            df = parse_ss_output(path+"/%s_ss.csv" % sender, start_time)
            df.to_csv("%s/%s_ss.csv" % (csv_path,sender), index=False)
            # Convert receiver output into csv
            df = parse_orca_output(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver),index=False)
        if flow[-2] == 'sage':
            # Convert sender output into csv
            df = parse_orca_output(path+"/%s_output.txt" % sender, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, sender), index=False)

            df = parse_ss_sage_output(path+"/%s_ss.csv" % sender, start_time)
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
        elif flow[-2] == 'astraea':
            # Convert sender output into csv
            df = parse_astraea_output(f"{path}/{sender}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)

            # Convert receiver output into csv
            df = parse_astraea_output(f"{path}/{receiver}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
        elif flow[-2] == 'vivace-uspace':
            # Convert sender output into csv
            df = parse_vivace_uspace_output(f"{path}/{sender}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)

            # Convert receiver output into csv
            df = parse_vivace_uspace_output(f"{path}/{receiver}_output.txt" , start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
        elif flow[-2] in IPERF:
            # Convert sender output into csv
            df = parse_iperf_json(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)
            
            df = parse_ss_output(path+"/%s_ss.csv" % sender, start_time)
            df.to_csv("%s/%s_ss.csv" % (csv_path,sender), index=False)
            
            # Convert receiver output into csv
            df = parse_iperf_json(path+"/%s_output.txt" % receiver, start_time)
            df.to_csv("%s/%s.csv" %  (csv_path, receiver), index=False)



def plot_all_mn(path: str) -> None:
    def remove_outliers(df, column, threshold):
        """Remove outliers from a DataFrame column based on a threshold."""
        return df[df[column] < threshold]
    fig, axs = plt.subplots(7, 1, figsize=(16, 36))
    with open(os.path.join(path, 'emulation_info.json'), 'r') as f:
        emulation_info = json.load(f)
    flows = []
    for flow in emulation_info['flows']:
        try:
            if flow[7] == None:
                flows.append([flow[0], flow[1]])  
        except IndexError:
            if flow[6] == None:
                flows.append([flow[0], flow[1]])  
    try:
        for flow in flows:
            flow_client = flow[0]  # Client flow name like 'c1', 'c2', etc.
            flow_server = flow[1]  # Server flow name like 'x1', 'x2', etc.

            df_client = pd.read_csv(os.path.join(path, f'csvs/{flow_client}.csv'))
            try:
                df_ss_client = pd.read_csv(os.path.join(path, f'csvs/{flow_client}_ss.csv'))
            except FileNotFoundError:
                df_ss_client = pd.DataFrame()
            df_server = pd.read_csv(os.path.join(path, f'csvs/{flow_server}.csv'))

            netem_bw = []
            netem_rtt = []
            netem_loss = []

            for flow in emulation_info['flows']:
                if flow[6] == 'tbf':
                    netem_bw.append([flow[4], flow[7][1]])  
                if flow[6] == 'netem' and flow[7]:
                    netem_rtt.append([flow[4], flow[7][2]])  
                    netem_loss.append([flow[4], (flow[7][6])])  

            if netem_bw:
                bw_df = pd.DataFrame(netem_bw, columns=["time", "max_bw"])
                bw_df.sort_values(by="time", inplace=True)
                last_time = bw_df['time'].max() + 10
                last_bw = bw_df['max_bw'].iloc[-1]
                bw_df = pd.concat([bw_df, pd.DataFrame([{"time": last_time, "max_bw": last_bw}])], ignore_index=True)
                axs[0].step(bw_df['time'], bw_df['max_bw'], label='Available Bandwidth', color='black', linestyle='--', where='post')
                axs[2].step(bw_df['time'], bw_df['max_bw'], label='Available Bandwidth', color='black', linestyle='--', where='post')

            if netem_rtt:
                rtt_df = pd.DataFrame(netem_rtt, columns=["time", "rtt"])
                rtt_df.sort_values(by="time", inplace=True)
                last_time = rtt_df['time'].max() + 10
                last_rtt = rtt_df['rtt'].iloc[-1]
                rtt_df = pd.concat([rtt_df, pd.DataFrame([{"time": last_time, "rtt": last_rtt}])], ignore_index=True)
                axs[1].step(rtt_df['time'], rtt_df['rtt'], label='Base RTT', color='black', linestyle='--', where='post')

            if netem_loss and not netem_loss[0][1] == None: 
                loss_df = pd.DataFrame(netem_loss, columns=["time", "loss"])
                loss_df.sort_values(by="time", inplace=True)
                last_time = loss_df['time'].max() + 10
                last_loss = loss_df['loss'].iloc[-1]
                loss_df = pd.concat([loss_df, pd.DataFrame([{"time": last_time, "loss": last_loss}])], ignore_index=True)

                ax_loss = axs[0].twinx()
                ax_loss.step(loss_df['time'], loss_df['loss'], label='Loss (%)', color='red', linestyle='--', where='post')
                ax_loss.set_ylabel('Loss (%)', color='red')
                ax_loss.legend(loc='upper right')
                ax_loss.set_ylim(0,None)


            # Goodput 
            axs[0].plot(df_server['time'], df_server['bandwidth'], label=f'{flow_server} Goodput')
            axs[0].set_title("Goodput (Mbps)")
            axs[0].set_ylabel("Goodput (Mbps)")

            # RTT
            if 'srtt' in df_client.columns:
                axs[1].plot(df_client['time'], df_client['srtt'], label=f'{flow_client} RTT')
                axs[1].set_title("RTT from Iperf (ms)")
            else:
                axs[1].plot(df_ss_client['time'], df_ss_client['srtt'], label=f'{flow_client} RTT')
                axs[1].set_title("RTT from SS (ms)")
            
            axs[1].set_ylabel("RTT (ms)")



            # Throughput
            axs[2].plot(df_client['time'], df_client['bandwidth'], label=f'{flow_client} CWND')
            axs[2].set_title("Throughput (Mbps)")
            axs[2].set_ylabel("Throughput (Mbps)")

            # # Bytes/Transferred ????
            # if 'transferred' in df_client.columns:
            #     axs[3].plot(df_client['time'], df_client['transferred'], label=f'{flow_client} Bytes')
            # else:
            #     axs[3].plot(df_client['time'], df_client['bytes'], label=f'{flow_client} Bytes')

            if not df_ss_client.empty:    
                if 'cwnd' in df_ss_client.columns:
                    axs[3].plot(df_ss_client['time'], df_ss_client['cwnd'], label=f'{flow_client} CWND')
                    axs[3].set_title("Cwnd from SS (packets)")
            else:
                axs[3].plot(
                    df_client['time'][df_client['cwnd'] != 100000],
                    df_client['cwnd'][df_client['cwnd'] != 100000],
                    label=f'{flow_client} CWND'
                )
                axs[3].set_title("Cwnd from Iperf (packets)")


            if 'retr' in df_client.columns:
                axs[4].plot(df_client['time'], df_client['retr'], label=f'{flow_client} Retransmits')
                axs[4].set_title("Retransmits from Iperf (packets)")
            else:
                axs[4].plot(df_ss_client['time'], df_ss_client['retr'], label=f'{flow_client} Retransmits')
                axs[4].set_title("Retransmits from SS (packets)")
    except:
        printRed("Error in plotting data for flows")
        # if 'rttvar' in df_client.columns:
        #     axs[5].plot(df_client['time'], df_client['rttvar'], label=f'{flow_client} Rttvar')
        #     axs[5].set_title("Rttvar from Iperf (ms)")
        # else:
        #     axs[5].plot(df_ss_client['time'], df_ss_client['rttvar'], label=f'{flow_client} Rttvar')
        #     axs[5].set_title("Rttvar from SS (ms)")

    queue_dir = os.path.join(path, 'queues')  # Specify the folder containing the queue files
    queue_files = [f for f in os.listdir(queue_dir) if f.endswith('.txt')]
    match = re.search(r"_(\d+)pkts_", queue_dir)

    queue_limit = int(match.group(1))

    axs[5].axhline(queue_limit, color='red', linestyle='--', label='Queue Limit')
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
        axs[5].plot(df_queue['time'], df_queue['root_pkts'], label=f'{queue_file} - root_pkts')
        axs[5].set_title("Queue size (packets)")
        axs[6].plot(df_queue['time'], df_queue['interval_drops'], linestyle='--', label=f'{queue_file} - root_drp')
        axs[6].set_title("Queue drops (packets)")


    for i, ax in enumerate(axs):
        ax.set_xlabel('Time (s)')
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
    printGreen(f"Plot saved to {output_file}")
    plt.close()

def plot_all_ns3_responsiveness(path: str) -> None:
    plt.rcParams.update({
        'font.size': 20,         # General font size
        'axes.titlesize': 20,    # Title font size
        'axes.labelsize': 20,    # Axis label font size
        'xtick.labelsize': 20,   # X-axis tick font size
        'ytick.labelsize': 20,   # Y-axis tick font size
        'legend.fontsize': 12,   # Legend font size
    })

    csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
    metrics = ['goodput', 'rtt', 'throughput', 'cwnd', 'bytes']
    file_mapping = {}

    for file in csv_files:
        if '-' in file and file.endswith('.csv'):
            parts = file.split('-')
            if len(parts) >= 3:  # Ensure the file has the expected format
                flow_name = f"{parts[0]}-{parts[1]}"  # e.g., TcpBbr-1
                metric = parts[2].split('.')[0]  # Extract metric (e.g., goodput)
                if metric in metrics:
                    if flow_name not in file_mapping:
                        file_mapping[flow_name] = {}
                    file_mapping[flow_name][metric] = os.path.join(path, file)
    emulation_info_file = os.path.join(path, 'emulation_info.json')
    with open(emulation_info_file, 'r') as f:
        emulation_info = json.load(f)

    fig, axs = plt.subplots(5, 1, figsize=(17, 30))
    netem_bw, netem_rtt, netem_loss = [], [], []

    for flow in emulation_info['flows']:
        if flow[6] == 'tbf':
            netem_bw.append([flow[4],flow[7][1]])
        if flow[6] == 'netem' and flow[7]:
            netem_rtt.append([flow[4], flow[7][2]])
            netem_loss.append([flow[4], (lambda x: x*100 if x is not None else None)(flow[7][6])])

    for flow_name, metrics_files in file_mapping.items():
        if 'goodput' in metrics_files:
            df = pd.read_csv(os.path.join(path, metrics_files['goodput']))
            axs[0].plot(df['time'], df['goodput'], label=f'{flow_name} Goodput')
            axs[0].set_title("Goodput (Mbps)")
            axs[0].set_ylabel("Goodput (Mbps)")
        if 'rtt' in metrics_files:
            df = pd.read_csv(os.path.join(path, metrics_files['rtt']))
            axs[1].plot(df['time'], df['rtt'], label=f'{flow_name} RTT')
            axs[1].set_title("Smooth Round-Trip Time (ms)")
            axs[1].set_ylabel("Milliseconds (ms)")

        if 'throughput' in metrics_files:
            df = pd.read_csv(os.path.join(path, metrics_files['throughput']))
            axs[2].plot(df['time'], df['throughput'], label=f'{flow_name} Throughput')
            axs[2].set_title("Throughtput (Mbps)")
            axs[2].set_ylabel("Throughtput (Mbps)")
    
        if 'cwnd' in metrics_files or 'bytes' in metrics_files:
            cwnd_df = pd.read_csv(os.path.join(path, metrics_files['cwnd'])) if 'cwnd' in metrics_files else pd.DataFrame()
            bytes_df = pd.read_csv(os.path.join(path, metrics_files['bytes'])) if 'bytes' in metrics_files else pd.DataFrame()
            axs[3].step(cwnd_df['time'], cwnd_df['cwnd']/1500, label=f'{flow_name} CWND (packets)', where='pre')
            axs[3].step(bytes_df['time'], bytes_df['bytes']/1500, label=f'{flow_name} Packets in flight', linestyle='--', where='pre')
            axs[3].set_title("Congestion Window and Packets in flgiht (packets)")
            axs[3].set_ylabel("Packets")

    if netem_bw:    
        bw_df = pd.DataFrame(netem_bw, columns=["time", "max_bw"])
        bw_df.sort_values(by="time", inplace=True)
        last_time = bw_df['time'].max() + 10
        last_bw = bw_df['max_bw'].iloc[-1]
        bw_df = pd.concat([bw_df, pd.DataFrame([{"time": last_time, "max_bw": last_bw}])], ignore_index=True)

        bw_df.set_index('time', inplace=True)
        axs[0].step(bw_df.index, bw_df['max_bw'], label='Available Bandwidth', color='black', linestyle='--', where='post')

    if netem_rtt:
        rtt_df = pd.DataFrame(netem_rtt, columns=["time", "rtt"])
        rtt_df.sort_values(by="time", inplace=True)
        last_time = rtt_df['time'].max() + 10
        last_rtt = rtt_df['rtt'].iloc[-1]
        rtt_df = pd.concat([rtt_df, pd.DataFrame([{"time": last_time, "rtt": last_rtt}])], ignore_index=True)
       
        rtt_df.set_index('time', inplace=True)
        axs[1].step(rtt_df.index, rtt_df['rtt'], label='Base RTT', color='black', linestyle='--', where='post')

    if netem_loss:
        loss_df = pd.DataFrame(netem_loss, columns=["time", "loss"])
        loss_df.sort_values(by="time", inplace=True)
        last_time = loss_df['time'].max() + 10
        last_loss = loss_df['loss'].iloc[-1]
        loss_df = pd.concat([loss_df, pd.DataFrame([{"time": last_time, "loss": last_loss}])], ignore_index=True)

        ax_loss = axs[0].twinx()
        ax_loss.step(loss_df['time'], loss_df['loss'], label='Loss (%)', color='red', linestyle='--', where='post')
        ax_loss.set_ylabel('Loss (%)', color='red')
        ax_loss.legend(loc='upper right')
        ax_loss.set_ylim(bottom=0)
        axs[0].set_ylim(bottom=0)
    queue_files = [os.path.join(path, f) for f in os.listdir(path) if f.startswith('queueSize-') and f.endswith('.csv')]
    for queue_file in queue_files:
        # Extract node and device ID for labeling (optional)
        file_name = os.path.basename(queue_file)
        node_device_id = file_name.split('-')[1].split('.')[0]

        # Read the file and preprocess
        df_queue = pd.read_csv(queue_file)
        df_queue['time'] = pd.to_numeric(df_queue['time'], errors='coerce')
        df_queue['time'] = df_queue['time'] - df_queue['time'].min()
        df_queue['root_pkts'] = df_queue['root_pkts'].astype(float)

        # Plot the data on the same axis
        axs[4].step(df_queue['time'], df_queue['root_pkts'], label=f'Node-Device {node_device_id}', where='post')
    axs[4].set_title("Packets in queue (packets)")
    axs[4].set_ylabel("Packets")

    for i, ax in enumerate(axs):
        ax.set_xlabel('Time (s)')
        ax.legend(loc='upper left')
        ax.grid(True)
        x_max = 0
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
    output_file = os.path.join(path, 'ns3_experiment_results.pdf')

    plt.savefig(output_file, dpi=1080)
    printBlueFill(f"NS3 experiment plots saved to {output_file}")
    plt.close()

def plot_all_ns3_responsiveness_extra(path: str) -> None:
    """
    Plot Goodput, RTT, Throughput, CWND, Bytes In Flight, and BBR State from NS3 experiment files.
    
    Args:
    path (str): The directory containing CSV files for the NS3 experiment.
    """
    # Identify and load all CSV files
    files = {
        "goodput": os.path.join(path, "TcpCubic-1-goodput.csv"),
        "rtt": os.path.join(path, "TcpCubic-1-rtt.csv"),
        "lastrtt": os.path.join(path, "TcpCubic-1-lastrtt.csv"),
        "throughput": os.path.join(path, "TcpCubic-1-throughput.csv"),
        "cwnd": os.path.join(path, "TcpCubic-1-cwnd.csv"),
        "bytes": os.path.join(path, "TcpCubic-1-bytes.csv"),
        "retransmits": os.path.join(path, "TcpCubic-1-retransmits.csv"),

        "root_pkts": os.path.join(path, "queueSize.csv"),



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
        #axs[1].plot(data["lastrtt"]["time"], data["lastrtt"]["lastrtt"], label="last RTT (ms)", )

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
        queue_data["time"] = pd.to_numeric(queue_data["time"], errors="coerce")
        queue_data["time"] = queue_data["time"] - queue_data["time"].min()
        queue_data["root_pkts"] = queue_data["root_pkts"].astype(float)  # Ensure numeric values
        axs[4].plot(queue_data["time"], queue_data["root_pkts"], label="Queue Size n0 d0 (Packets)")

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


    # Adjust layout and save the figure
    plt.tight_layout()
    output_file = os.path.join(path, "ns3_experiment_results_with_bbr.pdf")
    plt.savefig(output_file)
    printBlue(f"NS3 experiment plots saved to '{output_file}'.")
    plt.close()


    
