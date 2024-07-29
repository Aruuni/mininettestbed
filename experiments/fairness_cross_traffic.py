import os
import sys
import time

from threading import Timer


script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '..')
sys.path.append(mymodule_dir)

from core.topologies import DoubleDumbellTopo
from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSSwitch
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *
from core.common import *

def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2):
    if topology == 'DoubleDumbell':
        topo = DoubleDumbellTopo(n=params['n'])
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)
        return
        
    bdp_in_bytes = int(bw * (2**20) * 2 * delay * (10**-3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1510)
    
    net = Mininet(topo=topo, switch=OVSSwitch) # , controller=None)
    # net.addController("c0",
    #                 controller=RemoteController,
    #                 ip="127.0.0.1",
    #                 port=6633)
    path = "%s/mininettestbed/nooffload/fairness_cross_traffic/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (
        HOME_DIR, aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)
    rmdirp(path)
    mkdirp(path)

    # Configure size of TCP buffers
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)
    
    # Set up Mininet
    net.start()

    # Disable segmentation offloading
    #disable_offload(net)

    duration = int(2*delay)
        # Bring down cross traffic links initially
    # for h in range(2, 4):
    #net.configLinkStatus('x2%s', 's3b', 'down')
    # Network links configuration for both dumbbell topologies
    network_config = [
        NetworkConf('s1a', 's2a', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),
        NetworkConf('s2a', 's3a', bw, None, qsize_in_bytes, False, aqm, None),
        NetworkConf('s1b', 's2b', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),
        NetworkConf('s2b', 's3b', bw, None, qsize_in_bytes, False, aqm, None),
        # Cross traffic links
        NetworkConf('s1a', 's1b', bw, None, qsize_in_bytes, False, aqm, None),
        NetworkConf('s3a', 's3b', bw, None, qsize_in_bytes, False, aqm, None),
    ]
    
    traffic_config = [
        TrafficConf(f'c1{i+1}', f'x1{i+1}', 0, duration, protocol) for i in range(n_flows // 2)
    ] + [
        TrafficConf(f'c2{i+1}', f'x2{i+1}', 0, duration, protocol) for i in range(n_flows // 2)
    ] 
    #traffic_config.append(TrafficConf('god', 'god', 0, 3, 'cross_traffic'))
    # Create an emulation handler with links and traffic config
    net.configLinkStatus('s1a', 's1b', 'down')
    net.configLinkStatus('s3a', 's3b', 'down')
    em = Emulation(net, network_config, traffic_config, path)

    # Use tbf and netem to set up the network links as per config
    em.configure_network()

    # Schedule start and termination of traffic events 
    em.configure_traffic()
    # Set up system monitoring on the outgoing router's network interfaces and set up sysstat monitoring for all nodes
    monitors = ['s1a-eth1', 's2a-eth2', 's1b-eth1', 's2b-eth2', 'sysstat']
 
    em.set_monitors(monitors)

    # Run the emulation
    Timer(3, em.shift_traffic).start()
    em.run()

    # Store traffic config into json file
    em.dump_info()

    # Stop emulation
    net.stop()

    # Change user permissions for created directory and files since script was called as root
    change_all_user_permissions(path)

    # Process raw outputs into csv files
    process_raw_outputs(path)

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
