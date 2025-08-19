import os
import pandas as pd
from pathlib import Path
import pprint
import numpy as np

RESET = "\033[0m"
def printGreen(string):
    COLOR = "\033[32m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

# Make directory and all relevant parent directories if they do not exist
def mkdirp(path: str) -> None:
    try:
        os.makedirs( path,0o777 )
    except OSError:
        if not os.path.isdir( path ):
            raise

def traverse_experiments(parent_dir:Path, output:Path):
    """
    Walks through the entire directory tree to find run folders and parse the results.
    """
    all_results = []
    failures = []
    for root, dirs, files in os.walk(parent_dir):
        root_path = Path(root)
        if root_path.name.startswith("run"):  # found a run folder
            print('---------------------------------------------------------------------------------------')
            try:
                result = process_run_folder(root_path)
                if result:
                    all_results.append(result)
                    printGreen(f'Experiment successfully processed! Results total: {len(all_results)}')
                else:
                    failures.append(root_path)
                    printGreen(f'Experiment failed to process. Failures total: {len(failures)}')
            except FileNotFoundError:
                failures.append(root_path)
                printGreen(f'Experiment missing crucial file. Failures total: {len(failures)}')
            print('---------------------------------------------------------------------------------------\n\n')
    results = pd.DataFrame(all_results)

    printGreen(f'\n{len(failures)} experiments failed to process: ')
    printGreen(failures)

    printGreen(f'\n{len(results)} experiments failed to process: ')
    printGreen(results)

    mkdirp(output)
    results.to_csv(output / "all_experiments_summary.csv", index=False)

def process_run_folder(run_path: Path):
    """
    Takes a particular experiment run and process it, determing experiment parameters, flow averages, and run-wide average values.
    Returns a dict containing this run's parameters and results
    """
    csvs_path = run_path / "csvs"
    if not csvs_path.exists():
        return None  # Skip if no csvs folder

    params = extract_run_parameters(run_path)

    avg_goodput, avg_flow_goodputs = compute_goodput(csvs_path)
    avg_throughput, avg_flow_throughputs = compute_throughput(csvs_path)
    avg_cwnd, avg_flow_cwnds = compute_cwnd(csvs_path)
    flow_rtts = compute_rtt(csvs_path)
    exp_fairness = compute_fairness(run_path / "aggregate")
    host_names = [f'c{i}' for i in range(1, len(avg_flow_goodputs) + 1)]

    experiment_summary = {
        "average_goodput": avg_goodput,
        "average_throughput": avg_throughput,
        "average_cwnd": avg_cwnd,
        "average_weighted_rtt": flow_rtts['weighted_rtt'].mean(),
        "average_min_subfow_rtt": flow_rtts['min_subflow_rtt'].mean(),
        "average_mean_subflow_rtt": flow_rtts['mean_subflow_rtt'].mean(),
        "average_max_subfow_rtt": flow_rtts['max_subflow_rtt'].mean(),
        "mean_fairness": exp_fairness['mean_fairness'],
        "normalized_fairness": exp_fairness['normalized_fairness'],
    }
    experiment_summary = params | experiment_summary # Combine parameters and summary values into a single dict

    flows_summary = {
        "host_name": host_names,
        "average_goodput": avg_flow_goodputs,
        "average_throughput": avg_flow_throughputs,
        "average_cwnd": avg_flow_cwnds,
        "weighted_rtt": flow_rtts['weighted_rtt'],
        "min_subfow_rtt": flow_rtts['min_subflow_rtt'],
        "mean_subflow_rtt": flow_rtts['mean_subflow_rtt'],
        "max_subfow_rtt": flow_rtts['max_subflow_rtt'],
    }

    # Save all the files!
    summary_dir = run_path / "summary"
    summary_dir.mkdir(exist_ok=True)

    # Experiment parameters
    params_file = summary_dir / "experiment_params.csv"
    pd.DataFrame([params]).to_csv(params_file, index=False)

    # Experiment summary
    exp_summary_file = summary_dir / "experiment_summary.csv"
    pd.DataFrame([experiment_summary]).to_csv(exp_summary_file, index=False)
    
    # Flows Summary
    flows_summary_file = summary_dir / "flows_summary.csv"
    pd.DataFrame(flows_summary).to_csv(flows_summary_file, index=False)
    
    pprint.pprint(params)
    printGreen(f"Saved experiment summary to: {flows_summary_file}")
    printGreen(f"Compare with: {run_path}/combined.pdf")
    printGreen(pd.DataFrame([experiment_summary]))
    printGreen(pd.DataFrame(flows_summary))
    return experiment_summary

def compute_goodput(csvs_path: Path):
    """
    Goodput lol
    """
    flow_goodputs = []
    for file in sorted(csvs_path.glob("c*_ss_mp.csv")):
        df = pd.read_csv(file)
        if "delivery_rate" in df.columns:
            num_subflows = len(df['src'].unique())
            avg_subflow_goodput = df["delivery_rate"].mean()
            avg_flow_goodput = avg_subflow_goodput * num_subflows
            flow_goodputs.append(avg_flow_goodput)
    avg_flow_goodput = np.mean(flow_goodputs)

    return avg_flow_goodput, flow_goodputs

def compute_throughput(csvs_path: Path):
    """
    Throughput lol
    """
    flow_throughputs = []
    for file in sorted(csvs_path.glob("c*_ss_mp.csv")):
        df = pd.read_csv(file)
        if "send" in df.columns:
            num_subflows = len(df['src'].unique())
            avg_subflow_throughput = df["send"].mean()
            avg_flow_throughput = avg_subflow_throughput * num_subflows
            flow_throughputs.append(avg_flow_throughput)
    avg_flow_throughput = np.mean(flow_throughputs)

    return avg_flow_throughput, flow_throughputs

def compute_cwnd(csvs_path: Path):
    """
    cwnd lol
    """
    flow_cwnds = []
    for file in sorted(csvs_path.glob("c*_ss_mp.csv")):
        df = pd.read_csv(file)
        if "send" in df.columns:
            num_subflows = len(df['src'].unique())
            avg_subflow_cwnd = df["cwnd"].mean()
            avg_flow_cwnd = avg_subflow_cwnd * num_subflows
            flow_cwnds.append(avg_flow_cwnd)
    avg_flow_cwnd = np.mean(flow_cwnds)

    return avg_flow_cwnd, flow_cwnds

def compute_rtt(csvs_path: Path, interval: float = .5):
    """
    Computes weighted RTT based on subflow goodput ratios.
    This is more accurate to the experience of a user becuase it accounts for how much the high RTT paths were used.
    Computed over fixed time intervals provided by the interval parameter.
    """
    flow_weighted_rtts = []
    flow_min_subflow_rtt = []
    flow_mean_subflow_rtt = []
    flow_max_subflow_rtt = []
    for file in sorted(csvs_path.glob("c*_ss_mp.csv")):
        df = pd.read_csv(file)
        df["interval"] = (df["time"] // interval) * interval # Put ss entries into fixed interval groups

        # Find the average RTT/goodput for each subflow (per interval). Agg preforms some aggregate calcuation over the specified axes of each group.
        subflow_rtt_stats = df.groupby(['interval', 'src'], as_index=False).agg( 
            mean_rtt=("srtt", "mean"),
            mean_goodput=('delivery_rate', 'mean')
        )
        # Compute the goodput totals per interval and use them to calculate each subflow's weighted RTTs
        interval_goodput_totals = subflow_rtt_stats.groupby('interval')['mean_goodput'].sum().rename('interval_goodput_sum')
        subflow_rtt_stats = subflow_rtt_stats.merge(interval_goodput_totals, on='interval')
        subflow_rtt_stats['weight'] = subflow_rtt_stats['mean_goodput'] / subflow_rtt_stats['interval_goodput_sum']
        subflow_rtt_stats['weighted_rtt'] = subflow_rtt_stats['mean_rtt'] * subflow_rtt_stats['weight']

        # Finally, weighted RTT and other average RTT stats (should all be equal for subflow_count=1)
        flow_weighted_rtts.append(subflow_rtt_stats.groupby('interval')['weighted_rtt'].sum().mean())
        flow_min_subflow_rtt.append(subflow_rtt_stats.groupby('src')['mean_rtt'].mean().min())
        flow_mean_subflow_rtt.append(subflow_rtt_stats.groupby('src')['mean_rtt'].mean().mean())
        flow_max_subflow_rtt.append(subflow_rtt_stats.groupby('src')['mean_rtt'].mean().max())

    flow_stats = {
        "weighted_rtt": flow_weighted_rtts,
        "min_subflow_rtt": flow_min_subflow_rtt,
        "mean_subflow_rtt": flow_mean_subflow_rtt,
        "max_subflow_rtt": flow_max_subflow_rtt
    }
    
    return pd.DataFrame(flow_stats)

def compute_fairness(agg_path: Path):
    """
    Computes overall fairness rating from each experiment's fairness output
    """
    # Drop all invalid entries and clean up values where flow count is 1
    df = pd.read_csv(agg_path / 'fairness.csv').dropna()
    df['normalized_fairness'] = (df['fairness']-df['min_fairness']) * (1.0/(1.0-df['min_fairness']))
    df['normalized_fairness'] = df['normalized_fairness'].fillna(1.0)

    fairness = {
        'mean_fairness': df['fairness'].mean(),
        'normalized_fairness': df['normalized_fairness'].mean()
    }

    return fairness

def extract_run_parameters(run_path: Path):
    """
    Given a path like:
    .../manhattan_openflow_5201_8flows/fifo_10mbit_20ms_34pkts_0loss_22tcpbuf/strongly-disjoint-siblings/cubic_4subflows/run1
    Return a dict of parameters to store in the output.
    """
    parts = run_path.parts

    # Break the big chunks down
    experiment = parts[-6].removeprefix('results_')
    topo_parts = parts[-5].split('_')  # manhattan_openflow_5201_8flows
    aqm_parts = parts[-4].split('_')   # fifo_10mbit_20ms_34pkts_0loss_22tcpbuf
    proto_parts = parts[-2].split('_') # cubic_4subflows

    # Topology section
    topology = '_'.join(topo_parts[:-2])
    seed = topo_parts[-2]
    flows = topo_parts[-1].removesuffix('flows')

    # AQM section
    aqm = aqm_parts[0]
    bw = aqm_parts[1].removesuffix('mbit')          # e.g. "10mbit"
    delay = aqm_parts[2].removesuffix('ms')       # e.g. "20ms"
    qsize = aqm_parts[3].removesuffix('pkts')       # e.g. "34pkts"
    loss = aqm_parts[4].removesuffix('loss')        # e.g. "0loss"
    tcpbuf = aqm_parts[5].removesuffix('tcpbuf')      # e.g. "22tcpbuf"

    # Controller + protocol/subflows
    controller = parts[-3]                # strongly-disjoint-siblings
    proto = proto_parts[0]                 # cubic
    subflows = proto_parts[1].removesuffix('subflows')

    # Run ID
    run = parts[-1].removeprefix('run') # numeric part only
    
    params = {
        "experiment": experiment,
        "topology": topology,
        "seed": seed,
        "flows": int(flows),
        "aqm": aqm,
        "bw": bw,
        "delay": delay,
        "qsize": qsize,
        "loss": loss,
        "tcpbuf": tcpbuf,
        "controller": controller,
        "proto": proto,
        "subflows": int(subflows),
        "run": int(run),
        "plot_path": str(run_path / "combined.pdf")
    }
    return params

if __name__ == "__main__":
    """
    All sub-folders of the parent folder will be walked through in an attempt to find experiment folders.
    Every experiment folder found will be processed.
    """
    parent = Path("/home/james/cctestbed/JRA_Poster_Experiments_2")
    output = Path("/home/james/JRA_results_2")
    traverse_experiments(parent, output)

