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
    CHANGE_PERIOD = 100 #s
    start_time = 0
    traffic_config = []
    #for i in range(int(RUN_LENGTH/CHANGE_PERIOD)):
        #start_time = (CHANGE_PERIOD*i)
    random_bw = random.randint(50,100) # Mbps
    random_rtt = random.randint(5,100) # ms
    random_loss = round(random.uniform(0,0.01),4) 
    # traffic_config.append(TrafficConf('s2', 's3', start_time, CHANGE_PERIOD, 'tbf', 
    #                               (('s2', 's3'), random_bw, None, qsize_in_bytes, False, 'fifo', None, 'change')))
    traffic_config.append(TrafficConf('s1', 's2', start_time, CHANGE_PERIOD, 'netem', 
                                    (('s1', 's2'), None, 50, qsize_in_bytes, False, 'fifo', 0.01, 'change')))
            
    return traffic_config

def run_simulation(*args):
    topology, protocol, params, bw, delay, qmult, tcp_buffer_mult, run, aqm, loss, n_flows = args[0]
    if topology == 'Dumbell':
        topo = DumbellTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    bdp_in_bytes = int(bw*(2**20)*2*delay*(10**-3)/8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    
    path = "%s/cctestbed/ns3/results_custom_ns3/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (HOME_DIR,aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)
    rmdirp(path)
    mkdirp(path)
 
    traffic_config = [TrafficConf('c1', 'x1', 0, 100, protocol), TrafficConf('c2', 'x2', 20, 100, protocol)]
    traffic_config.extend(generate_traffic_shape(run, qsize_in_bytes))
    printRed(traffic_config)

    emulation_info = {}
    emulation_info['topology'] = str(topology)
    flows = []
    for config in traffic_config:
        flow = [config.source, config.dest, "na", "na", config.start, config.duration, config.protocol, config.params]
        flows.append(flow)
    emulation_info['flows'] = flows
    with open(path + "/emulation_info.json", 'w') as fout:
        json.dump(emulation_info,fout)
    
    command = f'cd {HOME_DIR}/ns-3-dev; time ./ns3 run --no-build "scratch/CCTestBed.cc --configJSON={path}/emulation_info.json --path={path} --delay={delay} --bandwidth={bw} --queuesize={250} --seed={run}" > {path}/output.txt 2>&1'
    printGreen(command)
    subprocess.run(command, shell=True)
    plot_all_ns3_responsiveness(path)

if __name__ == '__main__':

    PROTOCOLS = ['bbr', 'bbr3', 'cubic']
    PROTOCOLS = ['bbr']
    BWS = [50]
    DELAYS = [50]
    QMULTS = [1]
    RUNS = [1]
    LOSSES=[0]

    MAX_SIMULATIONS = 23

    pool = Pool(processes=MAX_SIMULATIONS)

    params_list = [("Dumbell", protocol, {'n':2}, bw, delay, mult, 22, run, "fifo", 0, 2)
                for protocol in PROTOCOLS
                for bw in BWS
                for delay in DELAYS
                for mult in QMULTS
                for run in [1]] #    
                #for run in range(1,51)] #     

    pool.map(run_simulation, params_list)

    pool.close()
    pool.join()

