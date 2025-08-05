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
from mininet.node import RemoteController
import subprocess
import sys
import os

# Starts the ryu remote controller as a subprocess. This is so ugly and bad because of PATH issues
# Mihai please save me
def start_remote_controller(controller: str):

    # sudo ss -lptn 'sport = :6653' ...can be used to check if any processes are already listening on port 6653.
    # If they exist, they are likely leftover Ryu instances that did not close properly. Close them. TODO

    controller_path = f'{HOME_DIR}/mininettestbed/controllers/{controller}.py'
    ryu_path = f'{HOME_DIR}/.local/bin/ryu-manager'
    pythonpath = f'{HOME_DIR}/.local/lib/python3.7/site-packages'

    # Set up the environment
    env = os.environ.copy()
    env['PYTHONPATH'] = pythonpath
    env['PATH'] = f"{HOME_DIR}/.local/bin:" + env['PATH']

    # Run the subprocess
    ryu_process = subprocess.Popen(
        ['python3.7', ryu_path, '--observe-links', controller_path],
        env=env
    )

    return ryu_process

# This experiment runs a custom animated version of the Manhattan topology, intended to loosely simulate the behaviour of LEO satellite networks
def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2, n_subflows=2, controller_name='None'):
    # This experiment is intended to be run only on the MultiCompetitionTopo
    if topology == "openflowtest":
        topo = OpenFlowTest(**params)
    else:
        print("ERROR: topology \'%s\' not recognised" % topology)

    net = Mininet(topo=topo, link=TCLink, autoSetMacs=True, autoStaticArp=True,
                  controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653),
    )

    # Switch/Controller/SDN/Openflow/Ryu (there are too many terms I don't yet know which this is, send help)
    # The openflow controller is a host running an instance Ryu, a python library that sends/recieves instructions to/from switches via the openflow protocol (maybe?)
    # Start the remote controller

    # I can't get this working. Mihai will probably know whats up.
    controller = start_remote_controller(controller_name)

    # Experiment properties
    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    duration = 20
    subflows = n_subflows

    # Generate path for plots, and delete old plot if necessary
    path = f"{HOME_DIR}/cctestbed/mininet/results_openflow_test/{aqm}/{topology}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{n_flows}flows_{n_subflows}subflows_{tcp_buffer_mult}tcpbuf_{protocol}/run{run}" 
    printRed(path)
    rmdirp(path)
    mkdirp(path)
    printGreen(f"delay is {delay}, bw is {bw}, qmult is {qmult}, qsize is {qsize_in_bytes}, bdp is {bdp_in_bytes}, loss is {loss}")
    
    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult) # idk, buffers setup
    #assign_ips_by_link(net) # Assign interface IPs sequentially
    configure_ndiffports_endpoints(net, subflows)
    net.start()
    disable_offload(net)

    # EXPERIMENT:
    # -------------------------------------------------------------------------------------------------------------------------------------------
    network_config=[]   # list of network conditions, such as bandwidth, delay, and loss on each link
    traffic_config=[]   # list of connections open/close during the experiment
    monitors=[]         # list of stats/interfaces to monitor

    # Client and server delay (bidirectional)
    network_config.append(NetworkConf('s_c1', 's1a', None,   2*delay,    3*bdp_in_bytes, True,  aqm,  loss))
    # Bandwidth policing (different per-path)
    network_config.append(NetworkConf(f's1a', f's1b', bw,     None,       qsize_in_bytes, False,    aqm,    None)) # Slow (normal)
    network_config.append(NetworkConf(f's1a', f's2b', bw,     None,       qsize_in_bytes, False,    aqm,    None)) # FAST alternate path

    # Traffic config
    traffic_config.append(TrafficConf(f'c1', f'x1', 0, duration, protocol)) # Start main flow (c1->x1) for entire experiment
   
    # monitors
    monitors.append('s1a-eth2')
    monitors.append('s1a-eth3')
    monitors.append('sysstat')
    # -------------------------------------------------------------------------------------------------------------------------------------------
    
    CLI(net)
    em = Emulation(net, network_config, traffic_config, path, .1)
    em.configure_network()
    em.configure_traffic()
    em.set_monitors(monitors) # monitors switch and router queue sizes

    threads = []
    threads.append(threading.Thread(target=em.run))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    em.dump_info() # seems to create a .json that plot_all_mn() will use. Necessary if you want to plot.
    net.stop()

    # Close the controller subprocess, if there is one
    if controller:
        controller.terminate()
        controller.wait()

    change_all_user_permissions(path)
    process_raw_outputs(path, emulation_start_time=em.start_time) # parsers.py does its thing
    change_all_user_permissions(path)
    plot_all_mn(path,aqm=aqm, multipath=True)


if __name__ == '__main__':
    topology = 'openflowtest'
    delay = int(sys.argv[1])
    bw = int(sys.argv[2])
    qmult = float(sys.argv[3])
    protocol = sys.argv[4]
    run = int(sys.argv[5])
    aqm = sys.argv[6]
    loss = sys.argv[7]
    n_flows = int(sys.argv[8])
    n_subflows = int(sys.argv[9])
    # mesh_size = int(sys.argv[9]) # for manhattan only
    controller = sys.argv[11]
    params = {'n': n_flows}

    run_emulation(topology, protocol, params, bw, delay, qmult, 22, run, aqm, loss, n_flows, n_subflows, controller) #Qsize should be at least 1 MSS.


