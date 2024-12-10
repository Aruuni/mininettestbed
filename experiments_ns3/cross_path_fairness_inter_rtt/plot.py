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


def plot_run(*args):
    topology, protocol, params, bw, delay, qmult, tcp_buffer_mult, run, aqm, loss, n_flows = args[0]

    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)

    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)

    path = f"{HOME_DIR}/cctestbed/ns3/cross_path_fairness_inter_rtt/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 
    plot_all_ns3_responsiveness(path)

if __name__ == '__main__':

    # PROTOCOLS = ['bbr', 'bbr3', 'cubic']
    # BWS = [100]
    # DELAYS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    # QMULTS = [0.2, 1, 4]
    # RUNS = [1, 2, 3, 4, 5]
    # LOSSES=[0]

    PROTOCOLS = ['bbr']
    BWS = [10]
    DELAYS = [50]
    QMULTS = [1]
    RUNS = [1]
    LOSSES=[0]

    MAX_SIMULATIONS = 6

    pool = Pool(processes=MAX_SIMULATIONS)

    params_list = [("Dumbell", protocol, {'n':2}, bw, delay, mult, 22, run, "fifo", 0, 2)
                for protocol in PROTOCOLS
                for bw in BWS
                for delay in DELAYS
                for mult in QMULTS
                for run in RUNS
                ]      

    pool.map(plot_run, params_list)

    pool.close()
    pool.join()










