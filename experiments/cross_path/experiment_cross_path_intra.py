import os
import sys
import time

from threading import Timer, Thread 


script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)

from core.topologies import DoubleDumbbellTopo
from mininet.net import Mininet
from mininet.cli import CLI
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *
def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2):
    if topology == 'DoubleDumbell':
        topo = DoubleDumbbellTopo(n=params['n'])
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)
        return
        
    bdp_in_bytes_1 = int(bw * (2**20) * 2 * 25 * (10**-3) / 8)
    qsize_in_bytes_1 = max(int(qmult * bdp_in_bytes_1), 1510)

    bdp_in_bytes_2 = int(bw * (2**20) * 2 * delay * (10**-3) / 8)
    qsize_in_bytes_2 = max(int(qmult * bdp_in_bytes_2), 1510)
    
    net = Mininet(topo=topo)
    path = f"{HOME_DIR}/cctestbed/mininet/results_soft_handover_fairness_intra_rtt/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes_2/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}"

    rmdirp(path)
    mkdirp(path)
    printC(path, "green_fill", ALL)
    if (protocol == "bbr3"):
        protocol = "bbr"
    if (protocol == "vivace"):
        protocol = "pcc"

    tcp_buffers_setup(bdp_in_bytes_2 + qsize_in_bytes_2, multiplier=tcp_buffer_mult)
    
    net.start()
    disable_offload(net)

    duration = delay * 12

    network_config = [
        NetworkConf('r2a', 'r3a', bw, None, qsize_in_bytes_1, False, aqm, None),
        NetworkConf('r2b', 'r3b', bw, None, qsize_in_bytes_2, False, aqm, None),
    ]
    for i in range(0, n_flows):
        network_config.append(NetworkConf(f'c1_{i+1}', 'r1a', None, 2*delay, 3*bdp_in_bytes_1, False, 'fifo', loss))
        network_config.append(NetworkConf(f'c2_{i+1}', 'r1b', None, 2*delay, 3*bdp_in_bytes_2, False, 'fifo', loss))

    traffic_config = [
        TrafficConf(f'c1_{i+1}', f'x1_{i+1}', 0, duration, protocol) for i in range(n_flows)
    ] + [
        TrafficConf(f'c2_{i+1}', f'x2_{i+1}', 0, duration, protocol) for i in range(n_flows)
    ] 

    em = Emulation(net, network_config, traffic_config, path, 0.1)

    em.configure_routing(n_flows)
    em.configure_network()
    em.configure_traffic()

    monitors = ['r2a-eth1', 'r2b-eth1', 'sysstat']
 
    em.set_monitors(monitors)


    Timer(delay * 4, em.reroute_traffic, args=(n_flows, True)).start()
    printC(f'change to cross path routing happening at time {delay * 2} seconds', "yellow_fill", ALL)
    Timer(delay * 8, em.reroute_traffic, args=(n_flows, False)).start()
    printC(f'change to original routing happening at time {delay * 4} seconds', "yellow_fill", ALL )

    em.run()
    em.dump_info()
    net.stop()
    
    change_all_user_permissions(path)
    process_raw_outputs(path)
    plot_all_mn(path)
    change_all_user_permissions(path)
        
if __name__ == '__main__':
    topology = 'DoubleDumbell'
    
    delay = int(sys.argv[1])
    bw = int(sys.argv[2])
    qmult = float(sys.argv[3])
    protocol = sys.argv[4]
    run = int(sys.argv[5])
    aqm = sys.argv[6]
    loss = sys.argv[7]
    n_flows = int(sys.argv[8])
    params = {'n': n_flows}

    # Same kernel setting as original Orca
    os.system('sudo sysctl -w net.ipv4.tcp_low_latency=1')
    os.system('sudo sysctl -w net.ipv4.tcp_autocorking=0')
    os.system('sudo sysctl -w net.ipv4.tcp_no_metrics_save=1')
    #def enable_tcp_keepalive(host):
    os.system('sysctl -w net.ipv4.tcp_keepalive_time=60')
    os.system('sysctl -w net.ipv4.tcp_keepalive_intvl=10')
    os.system('sysctl -w net.ipv4.tcp_keepalive_probes=5')

    run_emulation(topology, protocol, params, bw, delay, qmult, 22, run, aqm, loss, n_flows)
