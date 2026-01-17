import os, sys, threading, itertools, random, traceback
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSController

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '..')
sys.path.append( mymodule_dir )

from core.topologies import *
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_CTRL_PORT = 42000 
_run_id_lock = threading.Lock()
_mn_clean_lock = threading.Lock()
_run_id_counter = itertools.count(1)
_print_lock = threading.Lock()


def next_ex_idx() -> int:
    # Guarantees uniqueness across threads
    with _run_id_lock:
        return next(_run_id_counter)



def run_emulation(topology: str, protocol: str, params, bw: int, delay:int, qmult:float, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2) -> None:
    rng = random.Random(params['ex_idx'])
    topo = DumbellTopo(**params)
    bdp_in_bytes = int(bw * (2 ** 20) * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 60

    net = Mininet(topo=topo, controller=None, autoSetMacs=True, autoStaticArp=True)
    #net.addController('c0', controller=OVSController, port=BASE_CTRL_PORT + params['ex_idx'])

    path = f"{HOME_DIR}/cctestbed/mininet/results_test/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}_{aqm}aqm/run{run}" 
    printC(path, "red", INFO)

    rmdirp(path)
    mkdirp(path)

    printC(f"delay is {delay}, bw is {bw}, qmult is {qmult}, qsize is {qsize_in_bytes}, bdp is {bdp_in_bytes}, loss is {loss}", "green", ALL)
    if (protocol == "bbr3"):
        protocol = "bbr"
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)

    net.start()
    disable_offload(net)

    network_config = [NetworkConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", None, delay, 3*bdp_in_bytes, False, 'fifo', loss),
                      NetworkConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", bw, None, qsize_in_bytes, False, aqm, None)]
    

    traffic_config = [TrafficConf(f"c1{params['ex_idx']}", f"x1{params['ex_idx']}", 0, duration, 'tcpdatagen')]
    n = rng.randint(3, 40)
    n2 = rng.randint(10, 100)
    traffic_config.append(TrafficConf(f"s1{params['ex_idx']}", f"s2{params['ex_idx']}", n, duration-n, 'netem', ((f"s1{params['ex_idx']}", f"s2{params['ex_idx']}"), None, n2, 3*bdp_in_bytes, False, 'fifo', None, 'change')))
    prev_time_ms = 0
    flows_order = []
    flows_order.append(prev_time_ms)
    for i in range(2, n_flows + 1):
        prev_time_ms += rng.randint(0, 5000) # random start gap, 
        start = prev_time_ms /1000
        dur = duration - (prev_time_ms/1000)
        flows_order.append(prev_time_ms)
        traffic_config.append(TrafficConf(f"c{i}{params['ex_idx']}", f"x{i}{params['ex_idx']}", start, dur, protocol))

    trace_mame = f"{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{protocol}_{run}run"
    bw2 = bw
    # has to be in ms, as time on tarce is in mn, lowest friction unfotunately
    

    em = Emulation(net, network_config, traffic_config, path, 0.1, False, params['ex_idx'], {"env_bw": bw, "scheme": protocol, "bw2": bw2, "trace_file": trace_mame, "flows_order": flows_order }) 
    em.configure_network()
    em.configure_traffic()
    # em.set_monitors([f"s1{params['ex_idx']}-eth1", f"s2{params['ex_idx']}-eth2", 'sysstat'])
    em.run()
    em.dump_info()
    with _mn_clean_lock:
        net.stop()
    
    change_all_user_permissions(path)
    # process_raw_outputs(path)
    # change_all_user_permissions(path)
    # plot_all_mn(path)
    # plot_all_cpu(path)
    
if __name__ == '__main__':
    # DELAYS = [10, 20, 40, 60, 80, 90, 100]
    # BANDWIDTHS = [40, 60, 80, 100, 120, 140]
    # PROTOCOLS = ['bbr', 'cubic']
    # QMULTS = [ 0.5, 1, 2, ]  # Multiples of BDP
    # RUNS = [1,2]
    DELAYS = [40]
    BANDWIDTHS = [100]
    PROTOCOLS = ['bbr']
    QMULTS = [2]  # Multiples of BDP
    RUNS = [1]
    QMULTS = [1]  # Multiples of BDP
    def _worker(protocol, bw, delay, qmult, run):
        # Each worker gets a unique run id + unique ex_idx, never reused.
        ex_idx = next_ex_idx()
        flows = 1
        params = {'n': flows, 'ex_idx': ex_idx}
        run_emulation('Dumbell', protocol, params, bw, delay, qmult, 22, run, "fifo", "0", flows)

    MAX_JOBS = 10

    jobs = []
    for protocol in PROTOCOLS: 
        for bw in BANDWIDTHS:   
            for delay in DELAYS:
                for qmult in QMULTS:
                    for run in RUNS:
                        jobs.append((protocol, bw, delay, qmult, run))

    with ThreadPoolExecutor(max_workers=MAX_JOBS) as ex:
        futures = [ex.submit(_worker, *job) for job in jobs]
        for fut in as_completed(futures):
            try:
                _ = fut.result()
            except Exception as e:
                print(f"[WORKER ERROR] {e}", file=sys.stderr)
                traceback.print_exc()
