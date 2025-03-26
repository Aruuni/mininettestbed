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


def run_simulation(*args):
    topology, protocol, params, bw, delay, qmult, tcp_buffer_mult, run, aqm, loss, n_flows = args[0]

    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    fixed_bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * fixed_bdp_in_bytes), 1500)

    duration = int((2*delay*1000)/1000)
    
    path = f"{HOME_DIR}/cctestbed/ns3/results_fairness_intra_rtt/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 

    mkdirp(path)
    
    traffic_config = [TrafficConf('c1', 'x1',  0, 2*duration, protocol), 
                      TrafficConf('c2', 'x2', int(duration/2), int(duration/2)+duration, protocol)]

    emulation_info = {}
    emulation_info['topology'] = str(topology)
    flows = []
    for config in traffic_config:
        flow = [config.source, config.dest, "na", "na", config.start, config.duration, config.protocol, config.params]
        flows.append(flow)
    emulation_info['flows'] = flows
    with open(path + "/emulation_info.json", 'w') as fout:
        json.dump(emulation_info,fout)
    


    command = f'cd {HOME_DIR}/ns-3-dev; time ./ns3 run --no-build "scratch/CCTestBed.cc --configJSON={path}/emulation_info.json --path={path} --delay={delay} --bandwidth={bw} --queuesize={int(qsize_in_bytes/1500)} --seed={run}" > {path}/output.txt 2>&1'
    printGreen(command)
    subprocess.run(command, shell=True)

if __name__ == '__main__':

    PROTOCOLS = ['bbr', 'bbr3', 'cubic']
    BWS = [100]
    DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    QMULTS = [0.2, 1, 4]
    RUNS = [1, 2, 3, 4, 5]
    LOSSES=[0]

    MAX_SIMULATIONS = 45

    pool = Pool(processes=MAX_SIMULATIONS)

    params_list = [("Dumbell", protocol, {'n':2}, bw, delay, mult, 22, run, "fifo", 0, 2)
                for protocol in PROTOCOLS
                for bw in BWS
                for delay in DELAYS
                for mult in QMULTS
                for run in RUNS
                ]      

    pool.map(run_simulation, params_list)

    pool.close()
    pool.join()

