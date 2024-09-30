import os
import sys
import time

from threading import Timer


script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '..')
sys.path.append(mymodule_dir)

from core.topologies import DoubleDumbbellTopo
from mininet.net import Mininet
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
    path = "%s/mininettestbed/nooffload/fairness_cross_traffic/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (
        HOME_DIR, aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)
    
    rmdirp(path)
    mkdirp(path)

    # Configure size of TCP buffers
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)
    
    # Set up Mininet
    net.start()

    # Disable segmentation offloading
    disable_offload(net)

    duration = int(2*delay)

    network_config = [
        NetworkConf('r1a', 'r2a', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),
        NetworkConf('r2a', 'r3a', bw, None, qsize_in_bytes, False, aqm, None),
        NetworkConf('r1b', 'r2b', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),
        NetworkConf('r2b', 'r3b', bw, None, qsize_in_bytes, False, aqm, None),
    ]
    
    traffic_config = [
        TrafficConf(f'c1_{i+1}', f'x1_{i+1}', 0, duration, protocol) for i in range(n_flows)
    ] + [
        TrafficConf(f'c2_{i+1}', f'x2_{i+1}', 0, duration, protocol) for i in range(n_flows)
    ] 
    def delayed_reroute_traffic(delay, flip):
        time.sleep(delay)
        reroute_traffic(n_flows, flip)
    
    def reroute_traffic(num_pairs, flip):

        printDebug3("Rerouting traffic")
        r1b, r3b = net.get('r1b', 'r3b')
        # thsi is for the case of HARD handover  ??
        #r2b.cmd('ifconfig r2b-eth1 down')

        if flip:
            for i in range(1, num_pairs + 1):
                x2_subnet = f'192.168.{i+3*num_pairs}.0/24'
                c2_subnet = f'192.168.{i+2*num_pairs}.0/24'
                r1b.cmd(f'ip route replace {x2_subnet} via 10.0.5.1')
                r3b.cmd(f'ip route replace {c2_subnet} via 10.0.6.1')
        else:
            for i in range(1, num_pairs + 1):
                x2_subnet = f'192.168.{i+3*num_pairs}.0/24'
                c2_subnet = f'192.168.{i+2*num_pairs}.0/24'
                r1b.cmd(f'ip route replace {x2_subnet} via 10.0.3.1')
                r3b.cmd(f'ip route replace {c2_subnet} via 10.0.4.1')
    em = Emulation(net, network_config, traffic_config, path, 0.1)
    em.configure_routing(n_flows)
    # Use tbf and netem to set up the network links as per config
    em.configure_network()

    # Schedule start and termination of traffic events 
    em.configure_traffic()
    # Set up system monitoring on the outgoing router's network interfaces and set up sysstat monitoring for all nodes
    monitors = ['r1a-eth0', 'r2a-eth1', 'r1b-eth0', 'r2b-eth1', 'sysstat']
 
    em.set_monitors(monitors)
    #em.reroute_traffic(n_flows, delay-(delay/2))
    #em.reroute_traffic(n_flows, False)
    threading.Thread(target=delayed_reroute_traffic, args=(5,True)).start()
    threading.Thread(target=delayed_reroute_traffic, args=(10,False)).start()  
    em.run()
    em.dump_info()
    net.stop()

    # Change user permissions for created directory and files since script was called as root
    change_all_user_permissions(path)

    # Process raw outputs into csv files
    process_raw_outputs(path)
    plot_all(path, [{'src': flow.source, 'dest': flow.dest, 'start': flow.start } for flow in traffic_config])

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
