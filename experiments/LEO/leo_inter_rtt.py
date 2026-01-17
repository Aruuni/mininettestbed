import os, sys, threading, itertools, random, traceback
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSController

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../..')
sys.path.append( mymodule_dir )

from core.topologies import *
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *
from concurrent.futures import ThreadPoolExecutor, as_completed

_run_id_lock = threading.Lock()
_mn_clean_lock = threading.Lock()
_process_lock = threading.Lock()
_run_id_counter = itertools.count(1)

BWS    = [100]
DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
QMULTS = [0.2, 1, 4]
RUNS = [1, 2, 3, 4, 5]
PROTOCOLS = ['bbr', 'leocc', 'cubic', 'copa', 'bbr1']

DURATION = 200 
CHANGE_PERIOD = 5
MAX_JOBS = 5

# EXPERIMENT_PATH = f"cctestbed/benchmarks/results_intra_rtt_threading"
# BWS    = [180]
# DELAYS = [5]
# QMULTS = [ 1 ]
# RUNS = [4]
# PROTOCOLS = ['sage']

def  generate_traffic_shape(seed: int, qsize_in_bytes: int, interface_suf: str) -> list[TrafficConf]:
    random.seed(seed)
    start_time = CHANGE_PERIOD
    traffic_config = []
    for i in range(int(DURATION/CHANGE_PERIOD)):
        start_time = (CHANGE_PERIOD*i)
        random_bw = random.randint(50,100) # Mbps
        random_rtt = random.randint(5,100) # ms
        random_loss = round(random.uniform(0,1),2) 
        random_interrupt = random.randint(45,120) # ms
        traffic_config.append(TrafficConf(f"s1{interface_suf}", f"s2{interface_suf}", start_time, CHANGE_PERIOD, 'netem', ((f"s1{interface_suf}", f"s2{interface_suf}"), None, None, None, False, None, 0, 'change', random_interrupt, f"s2{interface_suf}-eth2")))
    return traffic_config

def next_ex_idx() -> int:
    with _run_id_lock:
        return next(_run_id_counter)

def run_emulation(protocol: str, params: dict, bw: int, delay: int, qmult:int, run: int, loss: float, aqm='fifo') -> None:
    rng = random.Random(params['ex_idx'])
    topo = DumbellTopo(**params)
    bdp_in_bytes = int(bw * (2 ** 20) * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    gap = 50

    net = Mininet(topo=topo, controller=None, autoSetMacs=True, autoStaticArp=True)
    path = f"{HOME_DIR}/cctestbed/mininet/results_leo/inter_rtt/Dumbbell_{aqm}aqm_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{2}flows_{protocol}/run{run}" 

    rmdirp(path), mkdirp(path), printC(path, "green", ALL)

    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=22)
    net.start()
    disable_offload(net)

    network_config = [NetworkConf(f"c1{params['ex_idx']}", f"s1{params['ex_idx']}", None, 10, 3*bdp_in_bytes, False, 'fifo', loss),
                      NetworkConf(f"c2{params['ex_idx']}", f"s1{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', loss),
                      NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]

    traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}", 0, DURATION, protocol), 
                      TrafficConf(f"c2{params['ex_idx']}", f"x2{params['ex_idx']}", gap, DURATION-gap, protocol)]
    traffic_config.extend(generate_traffic_shape(run, qsize_in_bytes, params['ex_idx']))

    em = Emulation(net, network_config, traffic_config, path, 0.1, False, params['ex_idx']) 
    em.configure_network()
    em.configure_traffic()
    em.set_monitors([f"s1{params['ex_idx']}-eth1", f"s2{params['ex_idx']}-eth2"])
    em.run()
    em.dump_info()

    with _mn_clean_lock:
        net.stop()
    
    with _process_lock:
        process_raw_out(path)
    if 'leoem' in protocol:
        # killall  the monitor_king
        os.system("pkill -f monitor_ping")
                                
if __name__ == '__main__':
    load_cc()   
    def _worker(protocol, bw, delay, qmult, run):
        # Each worker gets a unique run id + unique ex_idx, never reused.
        params = {'n': 2, 'ex_idx': next_ex_idx()}
        run_emulation(protocol, params, bw, delay, qmult, run, 0, 'fifo')
    jobs = []
    for protocol in PROTOCOLS: 
        for bw in BWS:   
            for delay in DELAYS:
                for qmult in QMULTS:
                    for run in RUNS:
                        jobs.append((protocol, bw, delay, qmult, run))
    random.shuffle(jobs)
    printC(f"Total jobs: {len(jobs)}", "green", INFO)
    with ThreadPoolExecutor(max_workers=MAX_JOBS) as ex:
        futures = [ex.submit(_worker, *job) for job in jobs]
        for fut in as_completed(futures):
            try:
                _ = fut.result()
            except Exception as e:
                print(f"[WORKER ERROR] {e}", file=sys.stderr)
                traceback.print_exc()