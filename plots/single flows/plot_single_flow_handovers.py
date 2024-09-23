import json
import matplotlib.pyplot as plt
import os
import argparse

def load_iperf_json(file_path):
    """ Load JSON data from iperf3 output file """
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def plot_iperf_results(folder):
    """ Plot RTT and Bandwidth from client iperf3 JSON files """

    # Define file names
    client_file = os.path.join(folder, 'c1_output.txt')
    
    # Load data from file
    client_data = load_iperf_json(client_file)
    
    # Extract RTT and Bandwidth information
    client_intervals = client_data['intervals']
    
    client_rtt = [x['streams'][0].get('rtt', 0) / 1000.0 for x in client_intervals]  # Convert to milliseconds
    client_bandwidth = [x['streams'][0]['bits_per_second'] / 1e6 for x in client_intervals]  # Convert to Mbps

    # Time intervals
    time_intervals = [x['sum']['end'] for x in client_intervals]
    
    # Create output folder in the current directory
    output_folder = 'plots'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Plot RTT
    if client_rtt:
        plt.figure(figsize=(10, 6))
        plt.plot(time_intervals, client_rtt, label='Client RTT (ms)', linestyle='-')  # No markers
        plt.title('RTT (Round Trip Time) Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('RTT (ms)')
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(output_folder, 'rtt_plot.pdf'))
        plt.close()
    
    # Plot Bandwidth
    if client_bandwidth:
        plt.figure(figsize=(10, 6))
        plt.plot(time_intervals, client_bandwidth, label='Client Bandwidth (Mbps)', linestyle='-')  # No markers
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
    parser.add_argument('folder', type=str, help='Path to the folder containing the client iperf3 output file (c1_output.txt)')

    args = parser.parse_args()
    
    # Call the plot function with command-line arguments
    plot_iperf_results(args.folder)
