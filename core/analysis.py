import json, glob
from core.parsers import *
from core.utils import *
import pandas as pd
import matplotlib.pyplot as plt

def process_raw_outputs(path: str) -> None:
    with open(f"{path}/emulation_info.json", 'r') as fin:
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
            df = parse_orca_output(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)
            remove(f"{path}/{sender}_output.txt")

            if parse_ss_to_csv(f"{path}/{sender}_ss.csv", f"{csv_path}/{sender}_ss.csv", start_time):
                remove(f"{path}/{sender}_ss.csv")

            df = parse_orca_output(f"{path}/{receiver}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
            remove(f"{path}/{receiver}_output.txt")
        if 'sage' in flow[-2]:
            df = parse_orca_output(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)
            remove(f"{path}/{sender}_output.txt")

            if parse_ss_to_csv(f"{path}/{sender}_ss.csv", f"{csv_path}/{sender}_ss.csv", start_time):
                remove(f"{path}/{sender}_ss.csv")

            df = parse_orca_output(f"{path}/{receiver}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
            remove(f"{path}/{receiver}_output.txt")
        elif 'aurora' in flow[-2]:
            df = parse_aurora_output(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)

            df = parse_aurora_output(f"{path}/{receiver}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
        elif 'astraea' in flow[-2]:
            df = parse_astraea_output(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)
            remove(f"{path}/{sender}_output.txt")

            df = parse_astraea_output(f"{path}/{receiver}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
            remove(f"{path}/{receiver}_output.txt")
        elif flow[-2] == 'vivace-uspace':
            df = parse_vivace_uspace_output(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)
            
            df = parse_vivace_uspace_output(f"{path}/{receiver}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
        elif flow[-2] in IPERF:
            df = parse_iperf_json(f"{path}/{sender}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{sender}.csv", index=False)
            remove(f"{path}/{sender}_output.txt")

            if parse_ss_to_csv(f"{path}/{sender}_ss.csv", f"{csv_path}/{sender}_ss.csv", start_time):
                remove(f"{path}/{sender}_ss.csv")
            
            df = parse_iperf_json(f"{path}/{receiver}_output.txt", start_time)
            df.to_csv(f"{csv_path}/{receiver}.csv", index=False)
            remove(f"{path}/{receiver}_output.txt")
        else:
            printC(f"Unknown protocol {flow[-2]} for flow {flow}, set it up correctly at core/analysis.py, skipping...", "red", ERROR)

def plot_all_mn(path: str, aqm='fifo') -> None:
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
        printC("Error in plotting data for flows", "red", ERROR)

    
    queue_dir = os.path.join(path, 'queues')
    queue_files = [f for f in os.listdir(queue_dir) if f.endswith('.txt')]

    m = re.search(r'_(\d+)pkts_', queue_dir)
    if m:
        queue_limit = int(m.group(1))
        axs[5].axhline(queue_limit, linestyle='--', color='red', label='Queue Limit')

    for queue_file in queue_files:
        queue_path = os.path.join(queue_dir, queue_file)
        df_queue = pd.read_csv(queue_path)

        # Normalize time
        df_queue['time'] = pd.to_numeric(df_queue['time'], errors='coerce')
        df_queue['time'] = df_queue['time'] - df_queue['time'].min()

        # Plot instantaneous queue size (packets)
        if 'root_pkts' in df_queue.columns:
            axs[5].plot(df_queue['time'], df_queue['root_pkts'] / 1500,
                        label=f'{queue_file} - root')
        axs[5].set_title("Queue size (packets)")
        
        if 'root_drp' in df_queue.columns:
            axs[6].plot(df_queue['time'],
                    df_queue['root_drp'].diff().fillna(0),
                    linestyle='--', label=f'{queue_file} - root')
            axs[6].set_title("Queue drops (packets)")
    x_max = 0
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
        time_interval = max(10, int(x_max / 20))  # Adjust ticks to ~20 intervals
        ax.xaxis.set_major_locator(plt.MultipleLocator(time_interval))

    # Adjust layout and save the figure
    plt.tight_layout(rect=[0, 0, 1, 1], pad=1.0)
    output_file = os.path.join(path, "plot" + '.pdf')

    plt.savefig(output_file)
    printC(f"Plot saved to {output_file}", "green", INFO)
    plt.close()


def plot_all_cpu(path: str) -> None:
    """
    Generate a single figure with 7 stacked subplots:
      Subplots 1-6: client (cpu_c*.log) aggregate CPU lines only (ALL / -1), one subplot per metric
      Subplot 7:    root (cpu_root.log) per-core utilization lines (100 - %idle), one line per core
    Root is omitted from the first 6 subplots as requested.
    """
    cpu_dir = os.path.join(path, "sysstat")
    client_files = sorted(glob.glob(os.path.join(cpu_dir, "cpu_c*.log")))
    root_file = os.path.join(cpu_dir, "cpu_root.log")

    metrics = ["%user", "%nice", "%system", "%iowait", "%steal", "%idle"]
    metric_titles = {
        "%user": "CPU User (%)",
        "%nice": "CPU Nice (%)",
        "%system": "CPU System (%)",
        "%iowait": "CPU I/O Wait (%)",
        "%steal": "CPU Steal (%)",
        "%idle": "CPU Idle (%)",
    }

    def _read_cpu_log(file_path: str) -> pd.DataFrame:
        # sadf -d output is ; delimited; header is usually commented with '#'
        df = pd.read_csv(
            file_path,
            sep=";",
            comment="#",
            header=None,
            names=["hostname", "interval", "timestamp", "CPU"] + metrics,
            engine="python",
        )
        # ensure numeric where expected
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["interval"] = pd.to_numeric(df["interval"], errors="coerce")
        # strip CPU string and keep as original column; also make a numeric copy for filtering
        cpu_str = df["CPU"].astype(str).str.strip()
        df["CPU_num"] = pd.to_numeric(cpu_str, errors="coerce")  # cores: 0..N, ALL often = -1 or NaN
        df["CPU_str"] = cpu_str.str.lower()
        return df.dropna(subset=["timestamp"])  # drop any header rows that slipped through

    # Read all client logs and root log (if present)
    client_dfs = [(_read_cpu_log(f), os.path.basename(f).replace(".log", "")) for f in client_files]
    root_df = _read_cpu_log(root_file) if os.path.exists(root_file) else None

    # Determine a global t0 for consistent time alignment across all files
    t0_candidates = []
    for df, _ in client_dfs:
        if not df.empty:
            t0_candidates.append(df["timestamp"].min())
    if root_df is not None and not root_df.empty:
        t0_candidates.append(root_df["timestamp"].min())
    if not t0_candidates:
        print("No CPU logs found.")
        return
    t0 = min(t0_candidates)

    # Prepare figure: 6 metric subplots + 1 per-core subplot
    fig, axs = plt.subplots(7, 1, figsize=(16, 30), sharex=True, constrained_layout=True)

    # ---- Clients: aggregate-only lines on subplots 1..6 ----
    if client_dfs:
        for df, label in client_dfs:
            if df.empty:
                continue
            df = df.copy()
            df["time"] = df["timestamp"] - t0

            # Aggregate rows: either CPU == "all"/"ALL" OR CPU_num == -1 (some sadf variants)
            is_agg = (df["CPU_str"] == "all") | (df["CPU_num"] == -1)
            df_all = df[is_agg]
            if df_all.empty:
                # Fallback: if no explicit ALL/-1, try grouping by timestamp averaging per-core
                df_all = (df[df["CPU_num"].notna() & (df["CPU_num"] >= 0)]
                            .groupby("time", as_index=False)[metrics].mean())

            for i, metric in enumerate(metrics):
                axs[i].plot(df_all["time"], df_all[metric], label=label)
                axs[i].set_title(metric_titles[metric])
                axs[i].set_ylabel("%")
                axs[i].grid(True)

        for i in range(6):
            axs[i].legend(loc="upper right")
    else:
        for i, metric in enumerate(metrics):
            axs[i].set_title(metric_titles[metric])
            axs[i].set_ylabel("%")
            axs[i].grid(True)

    # ---- Root per-core on subplot 7 ----
    ax_pc = axs[6]
    ax_pc.set_title("Root per-core CPU Utilization (100 - %idle)")
    ax_pc.set_ylabel("% Busy")
    ax_pc.set_xlabel("Time (s)")
    ax_pc.grid(True)

    if root_df is not None and not root_df.empty:
        df = root_df.copy()
        df["time"] = df["timestamp"] - t0

        # Per-core rows: numeric CPU >= 0
        df_cores = df[df["CPU_num"].notna() & (df["CPU_num"] >= 0)]
        if df_cores.empty:
            print("Root log found, but no per-core rows detected (CPU values not numeric).")
        else:
            # Plot one line per core: %busy = 100 - %idle
            for core_id, core_df in df_cores.groupby("CPU_num"):
                ax_pc.plot(core_df["time"], 100.0 - core_df["%idle"], label=f"Core {int(core_id)}")

            ax_pc.set_ylim(0, 100)
            ax_pc.legend(ncol=4, fontsize=9, loc="upper right")
    else:
        print("No root CPU log found; skipping per-core subplot.")

    # Save figure
    out = os.path.join(path, "cpu_plot.pdf")
    plt.savefig(out)
    printC(f"CPU plot (with per-core subplot) saved to {out}", "magenta", INFO)
    plt.close(fig)