import json
import matplotlib.pyplot as plt
import os
import argparse

def load_iperf_json(file_path):
    """ Load JSON data from iperf3 output file """
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def plot_iperf_results(client_file, server_file, output_folder='plots'):
    """ Plot RTT and Bandwidth from client and server iperf3 JSON files """
    
    # Load data from files
    client_data = load_iperf_json(client_file)
    server_data = load_iperf_json(server_file)
    
    # Extract RTT and Bandwidth information
    client_intervals = client_data['intervals']
    server_intervals = server_data['intervals']
    
    client_rtt = [x['streams'][0]['rtt'] / 1000.0 for x in client_intervals]  # Convert to milliseconds
    server_rtt = [x['streams'][0]['rtt'] / 1000.0 for x in server_intervals]  # Convert to milliseconds

    client_bandwidth = [x['streams'][0]['bits_per_second'] / 1e6 for x in client_intervals]  # Convert to Mbps
    server_bandwidth = [x['streams'][0]['bits_per_second'] / 1e6 for x in server_intervals]  # Convert to Mbps
    
    # Time intervals
    time_intervals = [x['sum']['end'] for x in client_intervals]
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Plot RTT
    plt.figure(figsize=(10, 6))
    plt.plot(time_intervals, client_rtt, label='Client RTT (ms)', marker='o', linestyle='-')
    plt.plot(time_intervals, server_rtt, label='Server RTT (ms)', marker='x', linestyle='--')
    plt.title('RTT (Round Trip Time) Over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('RTT (ms)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_folder, 'rtt_plot.pdf'))
    plt.close()

    # Plot Bandwidth
    plt.figure(figsize=(10, 6))
    plt.plot(time_intervals, client_bandwidth, label='Client Bandwidth (Mbps)', marker='o', linestyle='-')
    plt.plot(time_intervals, server_bandwidth, label='Server Bandwidth (Mbps)', marker='x', linestyle='--')
    plt.title('Bandwidth Over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Bandwidth (Mbps)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_folder, 'bandwidth_plot.pdf'))
    plt.close()

    print(f"Plots saved to {output_folder} as PDFs.")

if __name__ == "__main__":
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Plot RTT and Bandwidth from iperf3 JSON output files.')
    parser.add_argument('client_file', type=str, help='Path to the client iperf3 JSON output file (e.g., c1_output.txt)')
    parser.add_argument('server_file', type=str, help='Path to the server iperf3 JSON output file (e.g., x1_output.txt)')
    parser.add_argument('--output', type=str, default='plots', help='Folder to save the output PDF plots (default: plots)')

    args = parser.parse_args()
    
    # Call the plot function with command-line arguments
    plot_iperf_results(args.client_file, args.server_file, args.output)
