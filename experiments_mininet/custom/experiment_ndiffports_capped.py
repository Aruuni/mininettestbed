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

# This experiment is a variant of ndiffports_2 that imposes an artifical cap on the amount of traffic the main connection is allowed to send
# The intent is to give the packet scheduler more agency over traffic shifting, and hopefully produce some fairness
# This will likely require getting per-subflow throughputs, not just CWNDs

def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2):
    # This experiment is intended to be run only on the MultiCompetitionTopo
    if topology == "Ndiffports2":
        topo = Ndiffports2(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    # Create Mininet (with MPTCP wrapper class)
    net = Mininet(topo=topo, link=TCLink)

    # Experiment properties
    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 60
    subflows = 3

    # Generate path for plots, and delete old plot if necessary
    path = f"{HOME_DIR}/cctestbed/mininet/results_ndiffports_capped/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 
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
    
    
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult) # idk, buffers setup
    assign_ips(net) # Assign unique IPs in their appropriate per-link subnets
    assign_ECMP_routing_tables(net) # Automatically configure routing tables and default gateways, may not be perfect
    configure_ndiffports_endpoints(net, subflows)

    c1_ip = net.get('c1').IP()
    x1_ip = net.get('x1').IP()
    c2_ip = net.get('c2').IP()
    x2_ip = net.get('x2').IP()

    # Fix some routes misconfigured by assign_ECMP_routing_tables()
    add_route(net, 'r2b', ['r1a'], c1_ip)
    add_route(net, 'r2c', ['r1d'], x1_ip)

    # Add routes from c2 to x2
    add_route(net, 'r2q', ['r2a'], x2_ip)
    add_route(net, 'r2a', ['r2b'], x2_ip)
    add_route(net, 'r2b', ['r2c'], x2_ip)
    add_route(net, 'r2c', ['r2d'], x2_ip)

    # Add routes from x2 to c2
    add_route(net, 'r2d', ['r2c'], c2_ip)
    add_route(net, 'r2c', ['r2b'], c2_ip)
    add_route(net, 'r2b', ['r2a'], c2_ip)
    add_route(net, 'r2a', ['r2q'], c2_ip)

    # Disable MPTCP on the competing connection
    net.get('c2').cmdPrint('ip mptcp limits set subflows 0')
    net.get('x2').cmdPrint('ip mptcp limits set subflows 0')
    net.get('c2').cmdPrint('ip mptcp limits set add_addr_accepted 0')
    net.get('x2').cmdPrint('ip mptcp limits set add_addr_accepted 0')

    CLI(net)
    net.start()
    disable_offload(net)

    # EXPERIMENT:
    # -------------------------------------------------------------------------------------------------------------------------------------------
    monitors=[]         # list of stats/interfaces to monitor
    network_config=[]   # list of network conditions, such as bandwidth, delay, and loss on each link
    traffic_config=[]   # list of connections open/close during the experiment

    
    # delay
    network_config.append(NetworkConf('r2c', 'r2d', None,   2*delay,    3*bdp_in_bytes, False,  'fifo',  loss))
    network_config.append(NetworkConf('r2c', 'r1d', None,   2*delay,    3*bdp_in_bytes, False,  'fifo',  loss))
    network_config.append(NetworkConf('r1c', 'r1d', None,   2*delay,    3*bdp_in_bytes, False,  'fifo',  loss))

    # Rate limiters
    network_config.append(NetworkConf('r1q', 'r1a', bw,     None,       .5*qsize_in_bytes, False,    aqm,    None)) # Queue is stored in router r?b, b for bandwidth teehee
    network_config.append(NetworkConf('r2q', 'r2a', bw,     None,       .5*qsize_in_bytes, False,    aqm,    None)) # Queue is stored in router r?b, b for bandwidth teehee
    
    # Regular Network Queues
    network_config.append(NetworkConf('r1b', 'r1c', bw,     None,       qsize_in_bytes, False,    aqm,    None)) # Queue is stored in router r?b, b for bandwidth teehee
    network_config.append(NetworkConf('r2b', 'r2c', bw,     None,       qsize_in_bytes, False,    aqm,    None)) # Queue is stored in router r?b, b for bandwidth teehee
    

    # Traffic Config
    traffic_config.append(TrafficConf('c1', 'x1', 0, duration, protocol)) # Start main flow (c1->x1) for entire experiment
    traffic_config.append(TrafficConf('c2', 'x2', duration/2, duration/2, 'cubic')) # Start optional competing flow halfway through experiment

    # Track queues (these may be the wrong interfaces?)
    monitors = ['r1b-eth1', 'r2b-eth1', 'r1q-eth1', 'r2q-eth1', 'sysstat'] # might be the wrong interfaces, worry about it later
    # -------------------------------------------------------------------------------------------------------------------------------------------
    
    # note to self: ss is run from the iperf functions
    em = Emulation(net, network_config, traffic_config, path, .1)
    em.configure_network()
    em.configure_traffic()
    em.set_monitors(monitors) # monitors switch and router queue sizes
    em.run()
    em.dump_info() # seems to create a .json that plot_all_mn() will use. Necessary if you want to plot. 
    #CLI(net)
    net.stop()
    
    change_all_user_permissions(path)
    process_raw_outputs(path) # Properly formats output files to prepare for plotting. I probably should move my formatting here? Oh well
    change_all_user_permissions(path)
    plot_all_mn(path)

if __name__ == '__main__':
    topology = 'Ndiffports2'
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
