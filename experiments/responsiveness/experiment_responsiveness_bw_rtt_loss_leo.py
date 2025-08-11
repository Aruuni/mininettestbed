import os
import sys

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../..')
sys.path.append( mymodule_dir )

from core.topologies import *
from mininet.net import Mininet
from core.analysis import *

import json
from core.utils import *
from core.emulation import *
import random
import numpy as np
from core.config import *


def  generate_traffic_shape(seed, qsize_in_bytes):
    random.seed(seed)
    RUN_LENGTH = 300 #s
    CHANGE_PERIOD = 15 #s
    start_time = CHANGE_PERIOD
    traffic_config = []
    for i in range(int(RUN_LENGTH/CHANGE_PERIOD)):
        start_time = (CHANGE_PERIOD*i)
        random_bw = random.randint(50,100) # Mbps
        random_rtt = random.randint(5,100) # ms
        random_loss = round(random.uniform(0,1),2) 

        traffic_config.append(TrafficConf('s2', 's3', start_time, CHANGE_PERIOD, 'tbf', 
                                      (('s2', 's3'), random_bw, None, qsize_in_bytes, False, 'fifo', None, 'change')))
        traffic_config.append(TrafficConf('s1', 's2', start_time, CHANGE_PERIOD, 'netem', 
                                      (('s1', 's2'), None, random_rtt, qsize_in_bytes, False, 'fifo', random_loss, 'change')))
            
    return traffic_config


def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2):
    if topology == 'Dumbell':
        topo = DumbellTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    #TODO  check this 
    bdp_in_bytes = int(bw*(2**20)*2*delay*(10**-3)/8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    
    net = Mininet(topo=topo)
    path = f"{HOME_DIR}/cctestbed/mininet/results_responsiveness_bw_rtt_loss_leo/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 

    rmdirp(path)
    mkdirp(path)
    if (protocol == "bbr3"):
        protocol = "bbr"
    if (protocol == "vivace"):
        protocol = "pcc"   
    change_all_user_permissions(path)

    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)
    

    net.start()
    disable_offload(net)
    network_config = [NetworkConf('s1', 's2', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),
                      NetworkConf('s2', 's3', bw, None, qsize_in_bytes, False, aqm, None)]
    
    # Changes in the network parameters are treated as traffic configurations and are added in the same config
    if n_flows == 1:
        traffic_config = [TrafficConf('c1', 'x1', 0, 300, protocol)]
        traffic_config.extend(generate_traffic_shape(run, qsize_in_bytes))
    else:
        print("ERROR: number of flows greater than 1")
        exit()


    em = Emulation(net, network_config, traffic_config, path)

    em.configure_network()
    em.configure_traffic()
    monitors = ['s1-eth1', 's2-eth2', 'sysstat']

    em.set_monitors(monitors)
    em.run()
    em.dump_info()
    net.stop()
    
    change_all_user_permissions(path)
    process_raw_outputs(path)
    change_all_user_permissions(path)
    plot_all_mn(path)
    change_all_user_permissions(path)

if __name__ == '__main__':

    topology = 'Dumbell'
    delay = int(sys.argv[1])
    bw = int(sys.argv[2])
    qmult = float(sys.argv[3])
    protocol = sys.argv[4]
    run = int(sys.argv[5])
    aqm = sys.argv[6]
    loss = sys.argv[7]
    n_flows = int(sys.argv[8])
    params = {'n':n_flows}
    print('Loss is %s' % loss)
    run_emulation(topology, protocol, params, bw, delay, qmult, 22, run, aqm, loss, n_flows) #Qsize should be at least 1 MSS. 