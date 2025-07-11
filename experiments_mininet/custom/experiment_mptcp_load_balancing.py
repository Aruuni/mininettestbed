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
    if topology == "MultiCompetitionTopo":
        topo = MultiCompetitionTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    # Create Mininet (with MPTCP wrapper class)
    net = MPMininetWrapper(topo=topo, link=TCLink)

    # Experiment properties
    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 20

    # Generate path for plots, and delete old plot if necessary
    path = f"{HOME_DIR}/cctestbed/mininet/results_mptcp_load_balancing/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 
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
    c1, x1 = net.get('c1', 'x1')    # The main client/server, with access to all paths
    c2, x2 = net.get('c2', 'x2')    # Competing client/server, with access to a single path
    numPaths = params.get('n')      # Number of possible paths between c1 and x1

    monitors=[]         # list of stats/interfaces to monitor
    network_config=[]   # list of network conditions, such as bandwidth, delay, and loss on each link
    traffic_config=[]   # list of connections open/close during the experiment

    # Configure each path from c1 to x1
    for p in range(1, numPaths+1):
        printRed(p)
        network_config.append(NetworkConf('s' + str(p) + '.1', 's' + str(p) + '.2', None,   2*delay,    3*bdp_in_bytes, False,  'fifo',  loss))

        network_config.append(NetworkConf('s' + str(p) + '.2', 's' + str(p) + '.3', bw,     None,       qsize_in_bytes, False,    aqm,    None))

        # only two switch interfaces actually produce useful information- something about outgoing vs incoming interfaces and how the netwrok config is split into two
        # monitors.append('s' + str(p) + '.1' + '-eth1')
        # monitors.append('s' + str(p) + '.1' + '-eth2')
        # monitors.append('s' + str(p) + '.2' + '-eth1')
        monitors.append('s' + str(p) + '.2' + '-eth2') # This is the only interface that should have a monitor! This is where the queue lives
        # monitors.append('s' + str(p) + '.3' + '-eth1')
        # monitors.append('s' + str(p) + '.3' + '-eth2')
    monitors.append('sysstat') # Not sure what this does? Seems necessary, and is also the source of my x_max issues


    # Generate traffic configurations
    traffic_config.append(TrafficConf('c1', 'x1', 0, duration, protocol)) # Start main flow (c1->x1) for entire experiment
    traffic_config.append(TrafficConf('c2', 'x2', (duration/2), duration/2, 'cubic')) # Start competing flow (c2->x2) halfway through the experiment
    # -------------------------------------------------------------------------------------------------------------------------------------------

    # note to self: ss is run from the iperf functions
    em = Emulation(net, network_config, traffic_config, path, .1)
    em.configure_network()
    em.configure_traffic()
    em.set_monitors(monitors) # monitors switch and router queue sizes
    em.run()
    em.dump_info() # seems to create a .json that plot_all_mn() will use. Necessary if you want to plot. 
    CLI(net)
    net.stop()
    
    change_all_user_permissions(path)
    process_raw_outputs(path) # Properly formats output files to prepare for plotting. I probably should move my formatting here? Oh well
    change_all_user_permissions(path)
    plot_all_mn(path)

if __name__ == '__main__':
    topology = 'MultiCompetitionTopo'
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
