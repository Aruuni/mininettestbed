import os, sys
from mininet.net import Mininet
from mininet.cli import CLI
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../..')
sys.path.append( mymodule_dir )

from threading import Timer, Thread 
from core.topologies import *
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *


def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2, interrupt=0):
    if topology == 'Dumbell':
        topo = DumbellTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 100
    
    net = Mininet(topo=topo)
    path = f"{HOME_DIR}/cctestbed/mininet/results_handover_hard/{aqm}/{topology}_{bw}mbit_{delay}ms_{interrupt}ms_interrupt_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 

    rmdirp(path)
    mkdirp(path)
    
    if protocol == "bbr1":
        protocol = "bbr"
    if (protocol == "bbr3"):
        protocol = "bbr"
    if (protocol == "vivace"):
        protocol = "pcc"

    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)

    net.start()
    disable_offload(net)

    network_config = [NetworkConf('s1', 's2', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),
                      NetworkConf('s2', 's3', bw, None, qsize_in_bytes, False, aqm, None)]
    

    em = Emulation(net, network_config, [TrafficConf('c1', 'x1', 0, duration, protocol)], path, 0.1)

    em.configure_network()
    em.configure_traffic()
    
    monitors = ['s1-eth1', 's2-eth2', 'sysstat']
        
    em.set_monitors(monitors)
    Timer(0, em.cut_link, args=("s1", "eth1", interrupt, duration, 5)).start()
    em.run()


    em.dump_info()
    net.stop()
    
    change_all_user_permissions(path)
    process_raw_outputs(path)
    change_all_user_permissions(path)
    plot_all_mn(path)

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
    interrupt = int(sys.argv[9])
    params = {'n':n_flows}

    run_emulation(topology, protocol, params, bw, delay, qmult, 22, run, aqm, loss, n_flows, interrupt) #Qsize should be at least 1 MSS.
