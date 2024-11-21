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

import subprocess
from multiprocessing import Pool

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
        random_loss = round(random.uniform(0,5),2) # ms
        traffic_config.append(TrafficConf('s2', 's3', start_time, CHANGE_PERIOD, 'tbf', 
                                      (('s2', 's3'), random_bw, None, qsize_in_bytes, False, 'fifo', None, 'change')))
        traffic_config.append(TrafficConf('s1', 's2', start_time, CHANGE_PERIOD, 'netem', 
                                      (('s1', 's2'), None, random_rtt, qsize_in_bytes, False, 'fifo', None, 'change')))
            
    return traffic_config

def plot_run(*args):
    topology, protocol, params, bw, delay, qmult, tcp_buffer_mult, run, aqm, loss, n_flows = args[0]
    if topology == 'Dumbell':
        topo = DumbellTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    bdp_in_bytes = int(bw*(2**20)*2*delay*(10**-3)/8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    
    path = "%s/cctestbed/mininet/results_responsiveness_bw_rtt_leo/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (HOME_DIR,aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)

    plot_all_mininet_responsiveness(path)

if __name__ == '__main__':

    PROTOCOLS = ['bbr', 'cubic',  'pcc'] # , 'bbr3', 'orca', 'sage']
    #PROTOCOLS = ['pcc'] # , 'bbr3', 'orca', 'sage']

    BWS = [50]
    DELAYS = [50]
    QMULTS = [1]
    RUNS = [1]
    LOSSES=[0]

    MAX_SIMULATIONS = 12

    pool = Pool(processes=MAX_SIMULATIONS)

    params_list = [("Dumbell", protocol, {'n':1}, bw, delay, mult, 22, run, "fifo", 0, 1)
                for protocol in PROTOCOLS
                for bw in BWS
                for delay in DELAYS
                for mult in QMULTS
                #for run in [1]] #    
                for run in range(1,51)] #     

    pool.map(plot_run, params_list)

    pool.close()
    pool.join()










