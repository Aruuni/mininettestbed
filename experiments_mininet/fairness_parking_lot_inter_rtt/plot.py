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
from core.config import *
import subprocess
from multiprocessing import Pool

def plot_run(*args):
    topology, protocol, params, bw, delay, qmult, tcp_buffer_mult, run, aqm, loss, n_flows = args[0]



    fixed_bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * fixed_bdp_in_bytes), 1500)

    path = "%s/cctestbed/mininet/results_parking_lot_inter_rtt/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (HOME_DIR,aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)
    print(path)

    plot_all_mn(path)

    
if __name__ == '__main__':

    PROTOCOLS = ['bbr1', 'cubic',  'astraea', 'bbr3', 'orca', 'sage', 'vivace']
    #PROTOCOLS = ['pcc'] # , 'bbr3', 'orca', 'sage']

    BWS = [100]
    DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    QMULTS = [0.2, 1, 4]
    RUNS = [1, 2, 3, 4, 5]
    LOSSES=[0]

    # Careful, its a ram guzzler
    MAX_PLOTS = 8

    pool = Pool(processes=MAX_PLOTS)

    params_list = [("ParkingLot", protocol, {'n':4}, bw, delay, mult, 22, run, "fifo", 0, 4)
                for protocol in PROTOCOLS
                for bw in BWS
                for delay in DELAYS
                for mult in QMULTS
                #for run in [1]] #    
                for run in RUNS] #     

    pool.map(plot_run, params_list)

    pool.close()
    pool.join()