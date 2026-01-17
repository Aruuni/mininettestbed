import os, sys, threading, itertools, random, traceback
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../..')
sys.path.append( mymodule_dir )
from core.topologies import *
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSController
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

_run_id_lock = threading.Lock()
_mn_clean_lock = threading.Lock()
_run_id_counter = itertools.count(1)
_print_lock = threading.Lock()

PROTOCOLS = ['sage'] #, 'bic', 'cdg', 'cubic', 'htcp', 'highspeed', 'hybla', 'illinois', 'vegas', 'veno', 'westwood', 'yeah']

DELAYS = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200]
QMULTS = [0.2,1,4] 
BANDWIDTHS = [100]
RUNS = list(range(1, 6))



# BANDWIDTHS = [100]
# PROTOCOLS = ['bbr'] #, 'bic', 'cdg', 'cubic', 'htcp', 'highspeed', 'hybla', 'illinois', 'vegas', 'veno', 'westwood', 'yeah']
# QMULTS = [1] 
# DELAYS = [30]

# BANDWIDTHS = [100]
# DELAYS = [20]
# QMULTS = [2]
# RUNS = [6]
MAX_JOBS = 6


def next_ex_idx() -> int:
    # Guarantees uniqueness across threads
    with _run_id_lock:
        return next(_run_id_counter)


def run_thread_fairness_aqm(protocol, params, bw, delay, qmult, run, aqm='fifo', loss=None, n_flows=2):       
    bdp_in_bytes = int(bw*(2**20)*delay*(10**-3)/8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1510)
    net = Mininet(topo=DumbellTopo(**params), controller=None, autoSetMacs=True, autoStaticArp=True)

    path = f"{HOME_DIR}/cctestbed/mininet/results_fairness_aqm/{aqm}/Dumbell_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{n_flows}flows_{protocol}/run{run}" 

    rmdirp(path)
    mkdirp(path)

    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=3)
    net.start()
    disable_offload(net)

    network_config = [NetworkConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', loss),
                      NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]
    if n_flows == 1:
        traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}", 0, 60, protocol)]
    elif n_flows == 2:
        traffic_config = [TrafficConf('c1', 'x1', 0, 600, protocol),
                           TrafficConf('c2', 'x2', 100, 700, protocol)]
    elif n_flows == 3:
        traffic_config = [TrafficConf('c1', 'x1', 0, 600, protocol),
                         TrafficConf('c2', 'x2', 100, 700, protocol),
                         TrafficConf('c3', 'x3', 200, 800, protocol)]
    elif n_flows == 4:
        traffic_config = [TrafficConf('c1', 'x1', 0, 100, protocol),
                         TrafficConf('c2', 'x2', 25, 100, protocol),
                         TrafficConf('c3', 'x3', 50, 100, protocol),
                         TrafficConf('c4', 'x4', 75, 100, protocol)]
    em = Emulation(net, network_config, traffic_config, path)
    em.configure_network()
    em.configure_traffic()
    em.run()
    em.dump_info()
    net.stop()
    with _mn_clean_lock:
        net.stop()
    change_all_user_permissions(path)
    process_raw_outputs(path)
    change_all_user_permissions(path)
    with _print_lock:
        plot_all_mn(path)
    with _print_lock:
        plot_all_cpu(path)
    change_all_user_permissions(path)
    
def run_thread_fairness_inter_rtt(protocol, params, bw, delay, qmult, run, aqm='fifo',):
    bdp_in_bytes = int(bw * (2 ** 20) * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = int(delay)
    net = Mininet(topo=DumbellTopo(**params), controller=None, autoSetMacs=True, autoStaticArp=True)
    path = f"{HOME_DIR}/cctestbed/gauntlet/results_fairness_inter_rtt/{aqm}/Dumbell_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{protocol}/run{run}" 
    rmdirp(path)
    mkdirp(path)
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=3)
    net.start()
    disable_offload(net)
    network_config = [NetworkConf(f"c1{params['ex_idx']}", f"s1{params['ex_idx']}", None, 20, 3*bdp_in_bytes, False, 'fifo', None),
                      NetworkConf(f"c2{params['ex_idx']}", f"s1{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', None),
                      NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]
    traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}",  0, duration, protocol), 
                      TrafficConf(f"c2{params['ex_idx']}", f"x2{params['ex_idx']}", int(duration/4), duration-int(duration/4), protocol)]
    
    em = Emulation(net, network_config, traffic_config, path)
    em.configure_network()
    em.configure_traffic()
    em.run()
    em.dump_info()
    net.stop()
    with _mn_clean_lock:
        net.stop()
    change_all_user_permissions(path)
    process_raw_outputs(path)
    change_all_user_permissions(path)
    with _print_lock:
        plot_all_mn(path)
    with _print_lock:
        plot_all_cpu(path)
    change_all_user_permissions(path)

def run_thread_fairness_intra_rtt(protocol, params, bw, delay, qmult, run, aqm='fifo'):
    bdp_in_bytes = int(bw * (2 ** 20) * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = int(delay)
    net = Mininet(topo=DumbellTopo(**params), controller=None, autoSetMacs=True, autoStaticArp=True)
    path = f"{HOME_DIR}/cctestbed/gauntlet/results_fairness_intra_rtt/{aqm}/Dumbell_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{protocol}/run{run}" 
    rmdirp(path)
    mkdirp(path)
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=3)
    net.start()
    disable_offload(net)
    network_config = [NetworkConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', None),
                      NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]
    traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}",  0, duration, protocol), 
                      TrafficConf(f"c2{params['ex_idx']}", f"x2{params['ex_idx']}", int(duration/4), duration-int(duration/4), protocol)]
    em = Emulation(net, network_config, traffic_config, path)
    em.configure_network()
    em.configure_traffic()
    em.run()
    em.dump_info()
    net.stop()
    with _mn_clean_lock:
        net.stop()
    change_all_user_permissions(path)
    process_raw_outputs(path)
    change_all_user_permissions(path)
    with _print_lock:
        plot_all_mn(path)
    with _print_lock:
        plot_all_cpu(path)
    change_all_user_permissions(path)
    
def run_thread_fairness_bw(protocol, params, bw, delay, qmult, run, aqm='fifo'):
    bdp_in_bytes = int(bw*(2**20)*delay*(10**-3)/8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1510)
    net = Mininet(topo=DumbellTopo(**params), controller=None, autoSetMacs=True, autoStaticArp=True)
    path = f"{HOME_DIR}/cctestbed/gauntlet/results_fairness_bw/{aqm}/Dumbell_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{protocol}/run{run}" 

    rmdirp(path)
    mkdirp(path)
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=3)
    
    net.start()
    disable_offload(net)

    network_config = [NetworkConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', None),
                      NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]
    traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}", 0, 100, protocol),
                      TrafficConf(f"c2{params['ex_idx']}", f"x2{params['ex_idx']}", 25, 125, protocol)]
    em = Emulation(net, network_config, traffic_config, path)
    em.configure_network()
    em.configure_traffic()
    em.run()
    em.dump_info()
    net.stop()
    with _mn_clean_lock:
        net.stop()
    change_all_user_permissions(path)
    process_raw_outputs(path)
    change_all_user_permissions(path)
    with _print_lock:
        plot_all_mn(path)
    with _print_lock:
        plot_all_cpu(path)
    change_all_user_permissions(path)
    



EXPERIMENTS = [
    run_thread_fairness_inter_rtt,
    run_thread_fairness_intra_rtt,
    run_thread_fairness_bw 
]

if __name__ == '__main__':
    def _worker(experiment, protocol, bw, delay, qmult, run):
        # Each worker gets a unique run id + unique ex_idx, never reused.
        ex_idx = next_ex_idx()
        flows = 2
        experiment(protocol, {'n': flows, 'ex_idx': ex_idx}, bw, delay, qmult, run, "fifo")

    jobs = []
    for experiment in EXPERIMENTS:
        for protocol in PROTOCOLS:
            for bw in BANDWIDTHS:
                for delay in DELAYS:
                    for qmult in QMULTS:
                            for run in RUNS:    
                                jobs.append((experiment, protocol, bw, delay, qmult, run))

    random.shuffle(jobs)
    with ThreadPoolExecutor(max_workers=MAX_JOBS) as ex:
        futures = [ex.submit(_worker, *job) for job in jobs]

        # Overall progress bar across all jobs
        if tqdm:
            with tqdm(total=len(futures), desc="Running experiments", unit="job") as pbar:
                for fut in as_completed(futures):
                    try:
                        _ = fut.result()
                    except Exception as e:
                        print(f"[WORKER ERROR] {e}", file=sys.stderr)
                        traceback.print_exc()
                    finally:
                        pbar.update(1)
        else:
            # Fallback progress if tqdm isn't installed
            done = 0
            total = len(futures)
            def render(d, t, width=40):
                filled = int(width * d / t)
                bar = "#" * filled + "-" * (width - filled)
                print(f"\r[{bar}] {d}/{t} jobs", end="", flush=True)

            render(done, total)
            for fut in as_completed(futures):
                try:
                    _ = fut.result()
                except Exception as e:
                    print(f"\n[WORKER ERROR] {e}", file=sys.stderr)
                    traceback.print_exc()
                finally:
                    done += 1
                    render(done, total)
            print()  # newline at end