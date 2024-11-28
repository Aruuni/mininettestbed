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
        
    bdp_in_bytes = int(bw * (2**20) * 2 * delay * (10**-3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1510)
    
    net = Mininet(topo=topo)
    path = "%s/cctestbed/mininet/fairness_cross_traffic/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (HOME_DIR, aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)
    rmdirp(path)
    mkdirp(path)
    if (protocol == "bbr3"):
        protocol = "bbr"
        
    # Configure size of TCP buffers
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)
    
    # Set up Mininet
    net.start()

    # Disable segmentation offloading
    disable_offload(net)

    duration = 300

    network_config = [
        NetworkConf('r2a', 'r3a', bw, None, qsize_in_bytes, False, aqm, None),
        NetworkConf('r2b', 'r3b', bw, None, qsize_in_bytes, False, aqm, None),
    ]
    for i in range(0, n_flows):
        network_config.append(NetworkConf(f'c1_{i+1}', 'r1a', None, 50, 3*bdp_in_bytes, False, 'fifo', loss))
        network_config.append(NetworkConf(f'c2_{i+1}', 'r1b', None, delay, 3*bdp_in_bytes, False, 'fifo', loss))

    printDebug3(network_config)
    traffic_config = [
        TrafficConf(f'c1_{i+1}', f'x1_{i+1}', 0, duration, protocol) for i in range(n_flows)
    ] + [
        TrafficConf(f'c2_{i+1}', f'x2_{i+1}', 0, duration, protocol) for i in range(n_flows)
    ] 

    em = Emulation(net, network_config, traffic_config, path, 0.1)
    em.configure_routing(n_flows)
    # Use tbf and netem to set up the network links as per config
    em.configure_network()

    # Schedule start and termination of traffic events 
    em.configure_traffic()
    # Set up system monitoring on the outgoing router's network interfaces and set up sysstat monitoring for all nodes
    monitors = ['r2a-eth1', 'r2b-eth1', 'sysstat']
 
    em.set_monitors(monitors)


    Timer(100, em.reroute_traffic, args=(n_flows, True)).start()
    printDebug2(f'change to cross path routing happening at time {100} seconds')
    Timer(200, em.reroute_traffic, args=(n_flows, False)).start()
    printDebug2(f'change to original routing happening at time {200} seconds')

    em.run()
   # CLI(net)

    em.dump_info()
    net.stop()
    
    change_all_user_permissions(path)

    process_raw_outputs(path)
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
