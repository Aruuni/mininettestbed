import json
import sys
import matplotlib.pyplot as plt
import os

def plot_metrics(path, num_pairs):
    fig, axs = plt.subplots(5, 1, figsize=(10, 15))

    for dumbbell_index in range(1, 3):  # For both dumbbell topologies
        for flow in range(1, num_pairs + 1):  # For each flow

            file_path_client = f'iperf_result_{dumbbell_index}_c{flow}.json'
            file_path_server = f'iperf_result_{dumbbell_index}_x{flow}.json'
            if not os.path.exists(file_path_client) and not os.path.exists(file_path_server):
                print(f"File not found!")
                continue

            with open(file_path_client, 'r') as f:
                data_client = json.load(f)
            with open(file_path_server, 'r') as f:
                data_server = json.load(f)

            # Initialize lists to hold values
            times, times_server, goodputs, throughputs, rtts, cwnds, retransmissions = [], [], [], [], [], [], []
            
            for interval in data_server['intervals']:
                # Time
                start_time = interval['sum']['start']
                times_server.append(start_time)

                # Goodput (bits per second)
                goodput = interval['sum']['bits_per_second'] / 1e6
                goodputs.append(goodput)

            for interval in data_client['intervals']:
                # Time
                start_time = interval['sum']['start']
                times.append(start_time)

                # Throughput (bits per second)
                throughput = interval['sum']['bits_per_second'] / 1e6  # Convert to Mbps
                throughputs.append(throughput)

                # RTT and CWND from the stream (assume single stream per pair)
                if 'streams' in interval:
                    stream = interval['streams'][0]
                    rtt = stream['rtt'] / 1000  # Convert to ms
                    rtts.append(rtt)
                    cwnd = stream['snd_cwnd'] / 1024  # Convert to KBytes
                    cwnds.append(cwnd)
                    retransmissions.append(stream['retransmits'])
            # Plot throughput
            axs[0].plot(times_server, goodputs, label=f'Dumbbell {dumbbell_index} Flow {flow}')
            axs[0].set_ylabel('Goodput (Mbps)')
            axs[0].set_title('Goodput over Time')


            # Plot throughput
            axs[1].plot(times, throughputs, label=f'Dumbbell {dumbbell_index} Flow {flow}')
            axs[1].set_ylabel('Throughput (Mbps)')
            axs[1].set_title('Throughput over Time')

            # Plot RTT
            axs[2].plot(times, rtts, label=f'Dumbbell {dumbbell_index} Flow {flow}')
            axs[2].set_ylabel('RTT (ms)')
            axs[2].set_title('RTT over Time')

            # Plot CWND
            axs[3].plot(times, cwnds, label=f'Dumbbell {dumbbell_index} Flow {flow}')
            axs[3].set_ylabel('CWND (KBytes)')
            axs[3].set_title('CWND over Time')

            # Plot retransmissions
            axs[4].plot(times, retransmissions, label=f'Dumbbell {dumbbell_index} Flow {flow}')
            axs[4].set_ylabel('Retransmissions')
            axs[4].set_title('Retransmissions over Time')

    # Add legends and labels
    for ax in axs:
        ax.legend()
        ax.set_xlabel('Time (s)')

    plt.tight_layout()
    plt.savefig("metrics.pdf")

if __name__ == "__main__":
    num_pairs = int(sys.argv[1])  # Replace with the actual number of flows
    plot_metrics(num_pairs)
