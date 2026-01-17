import os, sys, threading, itertools, random, json
import numpy as np
from mininet.net import Mininet
from mininet.cli import CLI
from concurrent.futures import ThreadPoolExecutor, as_completed
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../..')
sys.path.append( mymodule_dir )

from core.topologies import *
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *

DELAYS = [50]
BANDWIDTHS = [50]
PROTOCOLS = ['bbr1']
QMULTS = [1]  # Multiples of BDP
RUNS = [i for i in range(1, 51)]
DURATION = 300  # seconds
CHANGE_PERIOD = 15 #s

_run_id_lock = threading.Lock()
_mn_clean_lock = threading.Lock()
_process_lock = threading.Lock()
_run_id_counter = itertools.count(1)

def next_ex_idx() -> int:
    # Guarantees uniqueness across threads
    with _run_id_lock:
        return next(_run_id_counter)

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
        traffic_config.append(TrafficConf(f"s2{interface_suf}", f"s3{interface_suf}", start_time, CHANGE_PERIOD, 'tbf', ((f"s2{interface_suf}", f"s3{interface_suf}"), random_bw, None, qsize_in_bytes, False, 'fifo', None, 'change', random_interrupt, f"s2{interface_suf}-eth2")))
        traffic_config.append(TrafficConf(f"s1{interface_suf}", f"s2{interface_suf}", start_time, CHANGE_PERIOD, 'netem', ((f"s1{interface_suf}", f"s2{interface_suf}"), None, random_rtt, qsize_in_bytes, False, 'fifo', 0, 'change', None, None)))
    return traffic_config

def run_emulation(protocol: str, params: dict, bw: int, delay: int, qmult:int, run: int, aqm='fifo') -> None:
    topo = DumbellTopo(**params)
    bdp_in_bytes = int(bw*(2**20)*2*delay*(10**-3)/8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    
    net = Mininet(topo=topo, controller=None, autoSetMacs=True, autoStaticArp=True)
    path = f"{HOME_DIR}/cctestbed/mininet/results_leo/responsiveness/Dumbbell_{aqm}aqm_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_0loss_1flow_{protocol}/run{run}" 
   
    rmdirp(path), mkdirp(path), printC(path, "green", ALL)

    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=22)
    
    net.start()
    disable_offload(net)

    network_config = [NetworkConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', None),
                      NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]
    traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}", 0, DURATION, protocol)]
    traffic_config.extend(generate_traffic_shape(run, qsize_in_bytes, params['ex_idx']))
    
    em = Emulation(net, network_config, traffic_config, path)

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

    def run_worker(protocol, bw, delay, qmult, run):
        # Each worker gets a unique run id + unique ex_idx, never reused.
        ex_idx = next_ex_idx()
        params = {'n': 1, 'ex_idx': ex_idx}
        run_emulation(protocol, params, bw, delay, qmult, run)

    MAX_JOBS = 5
    if 'leocc' in PROTOCOLS and MAX_JOBS > 1: 
        raise ValueError("monitor ping doesnt work when emulating multiple paths at the same time.")
    jobs = []
    for protocol in PROTOCOLS:
        for bw in BANDWIDTHS:
            for run in RUNS:
                jobs.append( (protocol, bw, DELAYS[0], QMULTS[0], run) )

    with ThreadPoolExecutor(max_workers=MAX_JOBS) as ex:
        futures = [ex.submit(run_worker, *job) for job in jobs]
        for fut in as_completed(futures):
                fut.result()
    
    # test
    #run_emulation("copa", {'n': 1, 'ex_idx': 1}, 50, 59, 1, 69)