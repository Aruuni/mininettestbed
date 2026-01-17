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

STEPS = [
    lambda delay: int(delay * 1.5),
    lambda delay: delay * 2,
    lambda delay: delay * 3,
    lambda delay: delay * 4,
    # lambda delay: delay // 2,
    # lambda delay: delay // 4,
]

DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
BANDWIDTHS = [100]
PROTOCOLS = ['sage_delay_real2'] #, 'bic', 'cdg', 'cubic', 'htcp', 'highspeed', 'hybla', 'illinois', 'vegas', 'veno', 'westwood', 'yeah']
QMULTS = [1] 
RUNS = list(range(1, len(STEPS) + 1))

# DELAYS = [30]
# BANDWIDTHS = [100]
# PROTOCOLS = ['bbr'] #, 'bic', 'cdg', 'cubic', 'htcp', 'highspeed', 'hybla', 'illinois', 'vegas', 'veno', 'westwood', 'yeah']
# QMULTS = [1] 

DURATION = 50
MAX_JOBS = 5
RESULT_PATH = "cctestbed/benchmarks/resutls_delay_jump_threading"

_run_id_lock = threading.Lock()
_mn_clean_lock = threading.Lock()
_run_id_counter = itertools.count(1)
_print_lock = threading.Lock()

def next_ex_idx() -> int:
    # Guarantees uniqueness across threads
    with _run_id_lock:
        return next(_run_id_counter)

def run_threeading_step_delay(topology: str, protocol: str, params, bw: int, delay:int, qmult:float, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2, bw2=None, delay2=None) -> None:
    topo = DumbellTopo(**params)
    bdp_in_bytes = int(bw * (2 ** 20) * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)

    net = Mininet(topo=topo, controller=None, autoSetMacs=True, autoStaticArp=True)
    path = f"{HOME_DIR}/{RESULT_PATH}/{topology}_{bw}mbit_{delay}ms_to_{delay2}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{protocol}_{aqm}/run{run}" 
    printC(path, "red", INFO)

    rmdirp(path)
    mkdirp(path)
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)

    net.start()
    disable_offload(net)

    network_config = [NetworkConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', loss), NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]
    traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}", 0, DURATION, protocol)]
    traffic_config.append(TrafficConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", 20, DURATION-20, 'netem', ((f"s1{params['ex_idx']}", f"s2{params['ex_idx']}"), None, delay2, qsize_in_bytes* 3, False, 'fifo', None, 'change')))

    em = Emulation(net, network_config, traffic_config, path, 0.1, False, params['ex_idx'], None) 
    em.configure_network()
    em.configure_traffic()
    #em.set_monitors([f"s1{params['ex_idx']}-eth1", f"s2{params['ex_idx']}-eth2", 'sysstat'])
    em.run()
    em.dump_info()
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

if __name__ == '__main__':
    def _worker(protocol, bw, bw2, delay, delay2,  qmult, run):
        # Each worker gets a unique run id + unique ex_idx, never reused.
        ex_idx = next_ex_idx()
        flows = 1
        params = {'n': flows, 'ex_idx': ex_idx}
        run_threeading_step_delay('Dumbell', protocol, params, bw, delay, qmult, 22, run, "fifo", "0", flows, bw2, delay2)

    jobs = []
    for protocol in PROTOCOLS:
        for bw in BANDWIDTHS:
            for delay in DELAYS:
                for qmult in QMULTS:
                    for i in range(len(STEPS)):
                        for run in RUNS:    
                            delay2 = max(1, STEPS[i % len(STEPS)](delay))  # prevent 0
                            jobs.append((protocol, bw, bw, delay, delay2, qmult, run))

    random.shuffle(jobs)
    with ThreadPoolExecutor(max_workers=MAX_JOBS) as ex:
        futures = [ex.submit(_worker, *job) for job in jobs]
        for fut in as_completed(futures):
            try:
                _ = fut.result()
            except Exception as e:
                print(f"[WORKER ERROR] {e}", file=sys.stderr)
                traceback.print_exc()
