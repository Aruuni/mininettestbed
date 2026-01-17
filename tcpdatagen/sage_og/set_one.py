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


DELAYS = [10, 20, 40, 80, 160]
BANDWIDTHS = [12, 24, 48, 96, 192]
PROTOCOLS = ['bbr', 'bic', 'cdg', 'cubic', 'htcp', 'highspeed', 'hybla', 'illinois', 'vegas', 'veno', 'westwood', 'yeah']
QMULTS = [ 1, 2, 4, 8, 16]  # Multiples of BDP

STEPS = [
    lambda bw: bw * 2,
    lambda bw: bw * 4,
    lambda bw: bw // 2,
    lambda bw: bw // 4,
]

# DELAYS = [40]
# BANDWIDTHS = [48]
# PROTOCOLS = ['bbr', 'bic', 'cdg', 'cubic', 'htcp', 'highspeed', 'hybla', 'illinois', 'vegas', 'veno', 'westwood', 'yeah']
# QMULTS = [4]  # Multiples of BDP



RUNS = list(range(1, len(STEPS) + 1))
BW2_PERIOD = 7
DURATION = 30
MAX_JOBS = 5



_run_id_lock = threading.Lock()
_mn_clean_lock = threading.Lock()
_run_id_counter = itertools.count(1)
_print_lock = threading.Lock()


def next_ex_idx() -> int:
    # Guarantees uniqueness across threads
    with _run_id_lock:
        return next(_run_id_counter)



def run_emulation(topology: str, protocol: str, params, bw: int, delay:int, qmult:float, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2, bw2=None) -> None:
    rng = random.Random(params['ex_idx'])
    topo = DumbellTopo(**params)
    bdp_in_bytes = int(bw * (2 ** 20) * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = DURATION

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

    flows_order = [0]

    flip = False
    for i in range(int(DURATION/BW2_PERIOD)):
        traffic_config.append(TrafficConf(f"s2{params['ex_idx']}", f"s3{params['ex_idx']}", (BW2_PERIOD*i), BW2_PERIOD, 'tbf', ((f"s2{params['ex_idx']}", f"s3{params['ex_idx']}"), bw2 if flip else bw, None, qsize_in_bytes, False, 'fifo', None, 'change')))
        flip = not flip

    trace_mame = f"{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{protocol}_{run}run"

    # has to be in ms, as time on tarce is in mn, lowest friction unfotunately
    datagen_params = {
        "env_bw": bw, 
        "scheme": protocol, 
        "bw2": bw2, 
        "bw2_flip_period": BW2_PERIOD, 
        "trace_file": trace_mame, 
        "flows_order": flows_order, 
        "timestamp": int(time.time() * 1_000), 
        'actor_version': "sage",
        'trace_set':"sage_traces2"
    }

    em = Emulation(net, network_config, traffic_config, path, 0.1, False, params['ex_idx'], datagen_params) 
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

    def _worker(protocol, bw, bw2, delay, qmult, run):
        # Each worker gets a unique run id + unique ex_idx, never reused.
        ex_idx = next_ex_idx()
        flows = 1
        params = {'n': flows, 'ex_idx': ex_idx}
        run_emulation('Dumbell', protocol, params, bw, delay, qmult, 22, run, "fifo", "0", flows, bw2)

    jobs = []
    for protocol in PROTOCOLS:
        for bw in BANDWIDTHS:
            for delay in DELAYS:
                for qmult in QMULTS:
                    for i, run in enumerate(RUNS):
                        bw2 = max(1, STEPS[i % len(STEPS)](bw))  # prevent 0
                        jobs.append((protocol, bw, bw2, delay, qmult, run))

    with ThreadPoolExecutor(max_workers=MAX_JOBS) as ex:
        futures = [ex.submit(_worker, *job) for job in jobs]
        for fut in as_completed(futures):
            try:
                _ = fut.result()
            except Exception as e:
                print(f"[WORKER ERROR] {e}", file=sys.stderr)
                traceback.print_exc()
