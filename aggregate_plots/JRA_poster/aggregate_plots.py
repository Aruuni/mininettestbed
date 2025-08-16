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

def traverse_experiments(parent_dir: Path):
    """
    Walks through the entire directory tree to find run folders and parse the results
    """
    
    for root, dirs, files in os.walk(parent_dir):
        root_path = Path(root)
        if root_path.name.startswith("run"):  # found a run folder
            process_run_folder(root_path)
    print("alld one :)")

def process_run_folder(run_path: Path):
    """
    Takes as input the path of an experiment (run folder) creates aggregate files in the aggregate folder
    """
    csvs_path = run_path / "csvs"
    if not csvs_path.exists():
        return None  # Skip if no csvs folder

    params = extract_run_parameters(run_path)

    avg_goodput, avg_flow_goodputs = compute_goodput(csvs_path)
    flow_rtts = compute_rtt(csvs_path)
    host_names = [f'c{i}' for i in range(1, len(avg_flow_goodputs) + 1)]

    experiment_summary = {
        "average_goodput": avg_goodput,
        "average_weighted_rtt": flow_rtts['weighted_rtt'].mean(),
        "average_min_subfow_rtt": flow_rtts['min_subflow_rtt'].mean(),
        "average_mean_subflow_rtt": flow_rtts['mean_subflow_rtt'].mean(),
        "average_max_subfow_rtt": flow_rtts['max_subflow_rtt'].mean()
    }

    flows_summary = {
        "host_name": host_names,
        "average_goodput": avg_flow_goodputs,
        "weighted_rtt": flow_rtts['weighted_rtt'],
        "min_subfow_rtt": flow_rtts['min_subflow_rtt'],
        "mean_subflow_rtt": flow_rtts['mean_subflow_rtt'],
        "max_subfow_rtt": flow_rtts['max_subflow_rtt']
    }

    # Save all the files!
    summary_dir = run_path / "summary"
    summary_dir.mkdir(exist_ok=True)

    # Experiment parameters
    params_file = summary_dir / "experiment_params.csv"
    pd.DataFrame([params]).to_csv(params_file, index=False)
    #printGreen(f"Saved experiment parameters to: {params_file}")

    # Experiment summary
    exp_summary_file = summary_dir / "experiment_summary.csv"
    pd.DataFrame([experiment_summary]).to_csv(exp_summary_file, index=False)
    #printGreen(f"Saved experiment summary to: {exp_summary_file}")
    
    # Flows Summary
    flows_summary_file = summary_dir / "flows_summary.csv"
    pd.DataFrame(flows_summary).to_csv(flows_summary_file, index=False)
    printGreen(f"Saved experiment summary to: {flows_summary_file}")
    printGreen(f"Compare with: {run_path}/combined.pdf")

    printGreen(pd.DataFrame(flows_summary))
    pprint.pprint(params)
    print('------------------------------------------------------------------\n\n')
    return ''

def compute_goodput(csvs_path: Path):
    """
    Example: compute total goodput from all client-server flows.
    You can modify this to average, max, min, etc.
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
    print(f'EXPERIMENT AVG GOODPUT: {avg_flow_goodput}')
    return avg_flow_goodput, flow_goodputs

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

        # Create a df with column named "total_goodput" containing the goodput totals for each interval.
        interval_goodput_totals = subflow_rtt_stats.groupby('interval')['mean_goodput'].sum().rename('interval_goodput_sum')

        # Add total_goodput column to grouped by merging. (will duplicate the value for every row in a particular interval)
        subflow_rtt_stats = subflow_rtt_stats.merge(interval_goodput_totals, on='interval')

        # Goodput weight per subflow/interval
        subflow_rtt_stats['weight'] = subflow_rtt_stats['mean_goodput'] / subflow_rtt_stats['interval_goodput_sum']

        # Weighted RTT per interval
        subflow_rtt_stats['weighted_rtt'] = subflow_rtt_stats['mean_rtt'] * subflow_rtt_stats['weight']

        other_stats_df = subflow_rtt_stats.groupby('interval')['weighted_rtt'].sum()

        # Finally, weighted RTT and other average RTT stats (should all be equal for subflow_count=1)
        # flow_rtt_stats = pd.DataFrame()
        flow_weighted_rtts.append(subflow_rtt_stats.groupby('interval')['weighted_rtt'].sum().mean())
        flow_min_subflow_rtt.append(subflow_rtt_stats.groupby('src')['mean_rtt'].mean().min())
        flow_mean_subflow_rtt.append(subflow_rtt_stats.groupby('src')['mean_rtt'].mean().mean())
        flow_max_subflow_rtt.append(subflow_rtt_stats.groupby('src')['mean_rtt'].mean().max())

        # flow_rtt_stats['weighted_rtt'] = [subflow_rtt_stats.groupby('interval')['weighted_rtt'].sum().mean()] # This flow's average weighted (experienced) RTT
        # flow_rtt_stats['min_subflow_rtt'] = [subflow_rtt_stats.groupby('src')['mean_rtt'].mean().min()] # This flow's lowest average subflow RTT (best path RTT)
        # flow_rtt_stats['mean_subflow_rtt'] = [subflow_rtt_stats.groupby('src')['mean_rtt'].mean().mean()] # This flow's "dumb" mean rtt (average across subflows, does not consider subflow usage rate)
        # flow_rtt_stats['max_subflow_rtt'] = [subflow_rtt_stats.groupby('src')['mean_rtt'].mean().max()] # This flow's highest average subflow RTT (worst path RTT)

        # printGreen(flow_rtt_stats)
        # printGreen('')
        
    flow_stats = {
        "weighted_rtt": flow_weighted_rtts,
        "min_subflow_rtt": flow_min_subflow_rtt,
        "mean_subflow_rtt": flow_mean_subflow_rtt,
        "max_subflow_rtt": flow_max_subflow_rtt
    }
    
    return pd.DataFrame(flow_stats)

def extract_run_parameters(run_path: Path):
    """
    Given a path like:
    .../manhattan_openflow_5201_8flows/fifo_10mbit_20ms_34pkts_0loss_22tcpbuf/strongly-disjoint-siblings/cubic_4subflows/run1
    Return a dict of parameters to store in the output.
    """
    parts = run_path.parts

    # Break the big chunks down
    topo_parts = parts[-5].split('_')  # manhattan_openflow_5201_8flows
    aqm_parts = parts[-4].split('_')   # fifo_10mbit_20ms_34pkts_0loss_22tcpbuf
    proto_parts = parts[-2].split('_') # cubic_4subflows

    # Topology section
    topology = '_'.join(topo_parts[:-2])
    seed = topo_parts[-2]
    flows = topo_parts[-1].removesuffix('flows')

    # AQM section
    aqm = aqm_parts[0]
    bw = aqm_parts[1]          # e.g. "10mbit"
    delay = aqm_parts[2]       # e.g. "20ms"
    qsize = aqm_parts[3]       # e.g. "34pkts"
    loss = aqm_parts[4]        # e.g. "0loss"
    tcpbuf = aqm_parts[5]      # e.g. "22tcpbuf"

    # Controller + protocol/subflows
    controller = parts[-3]                # strongly-disjoint-siblings
    proto = proto_parts[0]                 # cubic
    subflows = proto_parts[1].removesuffix('subflows')

    # Run ID
    run = parts[-1].removeprefix('run') # numeric part only
    
    params = {
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
        "run": int(run)
    }
    return params

if __name__ == "__main__":
    """
    All sub-folders of the parent folder will be walked through in an attempt to find experiment folders.
    Every experiment folder found will be processed.
    """
    parent = Path("/home/james/cctestbed/JRA_Poster_Experiments/results_manhattan_openflow_random_rate_limited")
    traverse_experiments(parent)
    parent = Path("/home/james/cctestbed/JRA_Poster_Experiments/results_manhattan_openflow_random_flooded")
    traverse_experiments(parent)
