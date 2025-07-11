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
from mininet.link import TCLink

def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2):
    # This experiment is intended to be run only on the MultiCompetitionTopo
    if topology == "MinimalMP":
        topo = MinimalMP(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    # Create Mininet (with MPTCP wrapper class)
    net = MPMininetWrapper(topo=topo, link=TCLink)

    # Experiment properties
    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 5

    # Generate path for plots, and delete old plot if necessary
    path = f"{HOME_DIR}/cctestbed/mininet/results_basic_mp/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 
    printRed(path)
    rmdirp(path)
    mkdirp(path)
    printGreen(f"delay is {delay}, bw is {bw}, qmult is {qmult}, qsize is {qsize_in_bytes}, bdp is {bdp_in_bytes}, loss is {loss}")
    
    # Convert names? I doubt I need this, but I'll keep it for now
    if protocol == "bbr1":
        protocol = "bbr"
    if (protocol == "bbr3"):
        protocol = "bbr"
    if (protocol == "vivace"):
        protocol = "pcc"
    
    # Start the mininet, and change some settings for experiment accuracy
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult)
    net.start()
    disable_offload(net)

    # EXPERIMENT:
    # -------------------------------------------------------------------------------------------------------------------------------------------
    monitors=[]         # list of stats/interfaces to monitor
    network_config=[]   # list of network conditions, such as bandwidth, delay, and loss on each link
    traffic_config=[]   # list of connections open/close during the experiment

    network_config.append(NetworkConf('s1a', 's1b', None,   2*delay,    3*bdp_in_bytes, False,  'fifo',  loss))
    network_config.append(NetworkConf('s1b', 's1c', bw,     None,       qsize_in_bytes, False,    aqm,    None))
    network_config.append(NetworkConf('s2a', 's2b', None,   2*delay,    3*bdp_in_bytes, False,  'fifo',  loss))
    network_config.append(NetworkConf('s2b', 's2c', bw,     None,       qsize_in_bytes, False,    aqm,    None))

    monitors = ['s1a-eth1', 's1a-eth2', 'sysstat']

    # monitors = ['s1a-eth1', 's1a-eth2','s1b-eth1', 's1b-eth2','s1c-eth1', 's1c-eth2',
    #             's2a-eth1', 's2a-eth2','s2b-eth1', 's2b-eth2','s2c-eth1', 's2c-eth2',
    #             'sysstat']


    # Generate traffic configurations
    traffic_config.append(TrafficConf('c1', 'x1', 0, duration, protocol)) # Start main flow (c1->x1) for entire experiment
    # -------------------------------------------------------------------------------------------------------------------------------------------

    # note to self: ss is run from the iperf functions
    em = Emulation(net, network_config, traffic_config, path, .1)
    em.configure_network()
    em.configure_traffic()
    em.set_monitors(monitors) # monitors switch and router queue sizes
    em.run()
    em.dump_info() # seems to create a .json that plot_all_mn() will use. Necessary if you want to plot. 
    # CLI(net)
    net.stop()
    
    change_all_user_permissions(path)
    process_raw_outputs(path) # Properly formats output files to prepare for plotting. I probably should move my formatting here? Oh well
    change_all_user_permissions(path)
    plot_all_mn(path)
    

if __name__ == '__main__':
    topology = 'MinimalMP'
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
