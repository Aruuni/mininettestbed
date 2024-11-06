import os
import sys

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '..')
sys.path.append( mymodule_dir )


from core.topologies import *
from mininet.net import Mininet
from core.analysis import *
import subprocess
import json
from core.utils import *
from core.emulation import *
from core.config import *
import subprocess
from multiprocessing import Pool

def run_simulation(*args):
    topology, protocol, params, bw, delay, qmult, tcp_buffer_mult, run, aqm, loss, n_flows = args[0]
    if topology == 'Dumbell':
        topo = DumbellTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)

    duration = int((2*delay*1000)/1000)

    

    path = "%s/mininettestbed/ns3/results_fairness_intra_rtt_async/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (HOME_DIR,aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)
    #rmdirp(path)
    mkdirp(path)

    
    if n_flows == 1:
        traffic_config = [TrafficConf('c1', 'x1', 0, 60, protocol)]
                        #   TrafficConf('c2', 'x2', 25, 75, protocol),
                        #   TrafficConf('c3', 'x3', 50, 50, protocol),
                        #   TrafficConf('c4', 'x4', 75, 25, protocol)]
    elif n_flows == 2:
        traffic_config = [TrafficConf('c1', 'x1', 0, 2*duration, protocol),
                           TrafficConf('c2', 'x2', int(duration/2), int(duration/2)+duration, protocol)]
    elif n_flows == 3:
        traffic_config = [TrafficConf('c1', 'x1', 0, 100, protocol),
                         TrafficConf('c2', 'x2', 25, 125, protocol),
                         TrafficConf('c3', 'x3', 50, 150, protocol)]
    elif n_flows == 4:
        traffic_config = [TrafficConf('c1', 'x1', 0, 100, protocol),
                         TrafficConf('c2', 'x2', 25, 125, protocol),
                         TrafficConf('c3', 'x3', 50, 150, protocol),
                         TrafficConf('c4', 'x4', 75, 175, protocol)]

    emulation_info = {}
    emulation_info['topology'] = str(topology)
    flows = []
    for config in traffic_config:
        flow = [config.source, config.dest, "na", "na", config.start, config.duration, config.protocol, config.params]
        flows.append(flow)
    emulation_info['flows'] = flows
    with open(path + "/emulation_info.json", 'w') as fout:
        json.dump(emulation_info,fout)

    #net.stop()
    
    command = f'cd /home/mihai/ns-3-dev; time ./ns3 run --no-build "scratch/CCTestBed.cc --configJSON={path}/emulation_info.json --path={path} --delay={delay} --bandwidth={bw} --seed={run}"'
    subprocess.run(command, shell=True)
    # Process raw outputs into csv files
    plot_all_ns3(path)

if __name__ == '__main__':

    PROTOCOLS = ['cubic', 'bbr']
    BWS = [100]
    DELAYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    QMULTS = [0.2,1,4]
    RUNS = [1, 2, 3, 4, 5]
    LOSSES=[0]

    MAX_SIMULATIONS = 10



    pool = Pool(processes=MAX_SIMULATIONS)

    params_list = [("Dumbell", protocol, {'n':2}, bw, delay, mult, 22, run, "fifo", 0, 2)
                for protocol in PROTOCOLS
                for bw in BWS
                for delay in DELAYS
                for mult in QMULTS
                for run in RUNS]

    pool.map(run_simulation, params_list)

    pool.close()
    pool.join()

