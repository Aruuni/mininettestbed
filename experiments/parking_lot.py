import os
import sys

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '..')
sys.path.append( mymodule_dir )


from core.topologies import *
from mininet.net import Mininet
from mininet.cli import CLI
from core.analysis import *

import json
from core.utils import *
from core.emulation import *
from core.config import *
ALLOWED = ['bbr', 'bbr1', 'pcc', 'cubic']


def run_emulation(topology: str, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2):
    if topology == 'Dumbell':
        topo = DumbellTopo(**params)
    elif topology == 'ParkingLot':
        topo = ParkingLot(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)

    duration = int((2*delay*1000)/1000)
    print('\033[94mDuration is %s seconds\033[0m' % (duration*2))
    
    net = Mininet(topo=topo)
 
    path = "%s/mininettestbed/nooffload/results_parking_lot/%s/%s_%smbit_%sms_%spkts_%sloss_%sflows_%stcpbuf_%s/run%s" % (HOME_DIR,aqm, topology, bw, delay, int(qsize_in_bytes/1500), loss, n_flows, tcp_buffer_mult, protocol, run)
    printDebug3(path)
    rmdirp(path)
    mkdirp(path)
    #  Configure size of TCP buffers
    #  TODO: check if this call can be put after starting mininet
    #  TCP buffers should account for QSIZE as well
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)

    net.start()

    disable_offload(net)

    #network_config = [NetworkConf(f's{i}', f's{i+1}', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),NetworkConf(f's{i}', f's{i+1}' bw, None, qsize_in_bytes, False, aqm, None)]
    bw_config = [NetworkConf(f's{i}', f's{i+1}', bw, None, qsize_in_bytes, False, aqm, loss) for i in range(1, n_flows,1)]
    delay_config = [NetworkConf(f'c{i}', f's{i-1}', None, 2*delay, 3*qsize_in_bytes, False, aqm, loss) for i in range(2, n_flows+1,1)]
    delay_config.append(NetworkConf('c1', 's1', None, 2*delay, 3*qsize_in_bytes, False, aqm, loss))
    #printDebug3(delay_config)
    network_config = bw_config + delay_config

    traffic_config = [TrafficConf('c1', 'x1', int(duration/2), int(duration/2)+duration, protocol)]
    #traffic_config = [TrafficConf('c1', 'x1', 0 , duration * 2, protocol)]
    for i in range(2,n_flows+1):
        traffic_config.append(TrafficConf(f'c{i}', f'x{i}', 0, duration*2, protocol)) 
    printDebug(traffic_config)
    em = Emulation(net, network_config, traffic_config, path, 0.1)

    em.configure_network()
    em.configure_traffic()
    monitors = ['s1-eth1', 's2-eth2', 's3-eth2', 'sysstat']
        
    em.set_monitors(monitors)
    em.run()
    #net.pingAll()
    #CLI(net)
    em.dump_info()
    net.stop()

    change_all_user_permissions(path)

    # Process raw outputs into csv files
    process_raw_outputs(path)
    plot_all(path, [{'src': flow.source, 'dst': flow.dest, 'start': flow.start , 'protocol': flow.protocol} for flow in traffic_config])

if __name__ == '__main__':

    topology = 'ParkingLot'
    
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

    # Plot results
    # plot_results(path)