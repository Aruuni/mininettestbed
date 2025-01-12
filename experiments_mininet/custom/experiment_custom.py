import os, sys
from mininet.net import Mininet
from mininet.cli import CLI
script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../..')
sys.path.append( mymodule_dir )


from core.topologies import *
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *


def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2):
    if topology == 'Dumbell':
        topo = DumbellTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 50
    
    net = Mininet(topo=topo)
    path = f"{HOME_DIR}/cctestbed/mininet/results_custom/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 
    printRed(path)

    rmdirp(path)
    mkdirp(path)
    printGreen(f"delay is {delay}, bw is {bw}, qmult is {qmult}, qsize is {qsize_in_bytes}, bdp is {bdp_in_bytes}, loss is {loss}")

    if (protocol == "bbr3"):
        protocol = "bbr"
    if (protocol == "vivace"):
        protocol = "pcc"
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)

    net.start()
    #disable_offload(net)

    network_config = [NetworkConf('s1', 's2', None, 2*delay, 3*bdp_in_bytes, False, 'fifo', loss),
                      NetworkConf('s2', 's3', bw, None, qsize_in_bytes, False, aqm, None)]
    

    traffic_config = [TrafficConf('c1', 'x1', 0, duration, "cubic"), 
                      TrafficConf('c2', 'x2', 10, duration-10, protocol),
     #                 TrafficConf('c3', 'x3', 5, duration-5, protocol)
                      
                      
                      ]


    
    em = Emulation(net, network_config, traffic_config, path, 0.1)

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

    run_emulation(topology, protocol, params, bw, delay, qmult, 22, run, aqm, loss, n_flows) #Qsize should be at least 1 MSS.
