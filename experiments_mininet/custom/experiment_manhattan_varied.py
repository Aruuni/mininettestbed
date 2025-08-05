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
from core.network_animation import *
import threading

# Host positions (relative)
cross_corners = {  'c1' : (0, 0, 0.0),
                    'x1' : (1.0, 1.0, 0.0),
                    'c2' : (0.0, 1.0, 0.0),
                    'x2' : (1.0, 0.0, 0.0),
                    }

perfect_opposite = {  'c1' : (0.0, 0.0, 0.0),
                    'x1' : (1.0, 0.0, 0.0),
                    'c2' : (1.0, 0.0, 0.0),
                    'x2' : (0.0, 0.0, 0.0),
                    }

shared_diagonal = {  'c1' : (.1, 0, 0.0),
                    'x1' : (1, .9, 0.0),
                    'c2' : (0, .1, 0.0),
                    'x2' : (.9, 1, 0.0),
                    }

varied_positions = {'c1' : (0, 0, 0.0),
                    'x1' : (1, 1, 0.0),
                    'c2' : (0, 1, 0.0),
                    'x2' : (1, 0, 0.0),
                    'c3' : (0, .2, 0.0),
                    'x3' : (1, .8, 0.0),
                    'c4' : (0, .8, 0.0),
                    'x4' : (1, .2, 0.0),
                    'c5' : (.2, 1, 0.0),
                    'x5' : (.8, 0, 0.0),
                    'c6' : (.8, 1, 0.0),
                    'x6' : (.2, 0, 0.0),
                    }

# This experiment runs a custom animated version of the Manhattan topology, intended to loosely simulate the behaviour of LEO satellite networks
def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2, n_subflows=2):
    # This experiment is intended to be run only on the MultiCompetitionTopo
    if topology == "manhattan":
        topo = ManhattanTopo(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    net = Mininet(topo=topo, link=TCLink)

    # Experiment properties
    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 10
    subflows = n_subflows
    host_positions = varied_positions

    # Generate path for plots, and delete old plot if necessary
    path = f"{HOME_DIR}/cctestbed/mininet/results_manhattan_varied/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{n_subflows}subflows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 
    printRed(path)
    rmdirp(path)
    mkdirp(path)
    printGreen(f"delay is {delay}, bw is {bw}, qmult is {qmult}, qsize is {qsize_in_bytes}, bdp is {bdp_in_bytes}, loss is {loss}")
    
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult) # idk, buffers setup
    assign_ips_by_link(net) # Assign interface IPs sequentially
    configure_ndiffports_endpoints(net, subflows)
    net.start()
    disable_offload(net)

    # EXPERIMENT:
    # -------------------------------------------------------------------------------------------------------------------------------------------
    monitors=[]         # list of stats/interfaces to monitor
    network_config=[]   # list of network conditions, such as bandwidth, delay, and loss on each link
    traffic_config=[]   # list of connections open/close during the experiment

    # Network configuration and static routing
    for i in range(1, n_flows+1):
        # Client up
        add_default_gateway(net, f'c{i}', [f'r_c{i}'])
        add_default_gateway(net, f'r_c{i}', [f'UT_c{i}'])

        # Client down
        client_ip = net.get(f'c{i}').IP()
        add_route(net, f'UT_c{i}', [f'r_c{i}'], client_ip)

        # Server up
        add_default_gateway(net, f'x{i}', [f'r_x{i}'])
        add_default_gateway(net, f'r_x{i}', [f'UT_x{i}'])

        # Server down
        server_ip = net.get(f'x{i}').IP()
        add_route(net, f'UT_x{i}', [f'r_x{i}'], server_ip)

        # Client and server delay
        network_config.append(NetworkConf(f'r_c{i}', f'UT_c{i}', None,   2*delay,    3*bdp_in_bytes, False,  'fifo',  loss))
    
    # Bandwidth policing in the mesh
    printRed(params)
    mesh_size = int(params.get('mesh_size') )

    # Bidirectional bandwidth/queue policing
    for x in range (1, mesh_size+1):
        for y in range (1, mesh_size+1):
            if x != mesh_size:
                network_config.append(NetworkConf(f'r{x}_{y}', f'r{x+1}_{y}', bw,     None,       qsize_in_bytes, True,    aqm,    None)) # Right
            if y != mesh_size:
                network_config.append(NetworkConf(f'r{x}_{y}', f'r{x}_{y+1}', bw,     None,       qsize_in_bytes, True,    aqm,    None)) # Above


    for f in range(1, n_flows + 1):
        traffic_config.append(TrafficConf(f'c{f}', f'x{f}', 0, duration, protocol)) # Start main flow (c1->x1) for entire experiment
    

    monitors = []
    # Track queues (these may be the wrong interfaces?)

    node: Node
    for node in net.hosts:
        if node.name.startswith('r') and not node.name.startswith('r_'):
            for intf in node.intfList():
                if int(intf.name.split('eth')[1]) >= n_flows * 2:
                    printPink(f'Monitoring intf {intf.name}')
                    monitors.append(intf.name)
    # monitors.append('r5_2-eth14')
    monitors.append('sysstat')
    print(monitors)
    # -------------------------------------------------------------------------------------------------------------------------------------------
    
    

    anim = ManhattanTopoAnimator(net=net, topo=topo, host_positions=host_positions, direction=(-.05, 0), relative=True)
    #CLI(net)
    em = Emulation(net, network_config, traffic_config, path, .1)
    em.configure_network()
    em.configure_traffic()
    em.set_monitors(monitors) # monitors switch and router queue sizes

    threads = []

    #threads.append(threading.Thread(target = anim.run, kwargs=({'duration': duration, 'interval': 1})))
    threads.append(threading.Thread(target=em.run))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    em.dump_info() # seems to create a .json that plot_all_mn() will use. Necessary if you want to plot.
    net.stop()
    
    change_all_user_permissions(path)
    process_raw_outputs(path, emulation_start_time=em.start_time) # parsers.py does its thing
    change_all_user_permissions(path)
    plot_all_mn(path,aqm=aqm, multipath=True)


if __name__ == '__main__':
    topology = 'manhattan'
    delay = int(sys.argv[1])
    bw = int(sys.argv[2])
    qmult = float(sys.argv[3])
    protocol = sys.argv[4]
    run = int(sys.argv[5])
    aqm = sys.argv[6]
    loss = sys.argv[7]
    n_flows = int(sys.argv[8])
    n_subflows = int(sys.argv[9])
    mesh_size = int(sys.argv[10])
    params = {'n': n_flows,
              'mesh_size': mesh_size}

    run_emulation(topology, protocol, params, bw, delay, qmult, 22, run, aqm, loss, n_flows, n_subflows) #Qsize should be at least 1 MSS.
