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
#from core.network_animation import *
import threading
from mininet.node import RemoteController
import subprocess
import sys
import os

def start_remote_controller(controller: str, path_selector: str, num_paths: int, path_penalty: float, output_path: str, path_selector_preset:str=None, host_ips:str=None):
    """
    Starts up a new Ryu instance (python3.7 for compatibility reasons) and passes it some parameters as environment variables.
    Will attempt to kill any currently running Ryu instaces
    This process is responsible for handling messages to/from the openflow controller to/from Mininet switches
    """
    # Kill any leftover ryu instances
    subprocess.run(['sudo', 'fuser', '-k', '6653/tcp'])

    controller_path = f'{HOME_DIR}/mininettestbed/controllers/{controller}.py'
    ryu_path = f'{HOME_DIR}/.local/bin/ryu-manager'
    pythonpath = f'{HOME_DIR}/.local/lib/python3.7/site-packages'

    # Set up the environment
    env = os.environ.copy()
    env['PYTHONPATH'] = pythonpath
    env['PATH'] = f"{HOME_DIR}/.local/bin:" + env['PATH']
    env['PATH_SELECTOR'] = path_selector
    env['NUM_PATHS'] = str(num_paths) 
    env['PATH_PENALTY'] = str(path_penalty)
    env['OUTPUT_PATH'] = str(output_path)
    env['PATH_SELECTOR_PRESET'] = path_selector_preset
    env['HOST_IPS'] = host_ips
    env['DEBUG_PRINTS'] = "False" # "True" evaluates to true, everything else is false

    # Run the subprocess
    ryu_process = subprocess.Popen(
        ['python3.7', ryu_path, '--observe-links', controller_path],
        env=env
    )

    return ryu_process

# This experiment runs a custom animated version of the Manhattan topology, intended to loosely simulate the behaviour of LEO satellite networks
def run_emulation(topology, protocol, params, bw, delay, qmult, tcp_buffer_mult=3, run=0, aqm='fifo', loss=None, n_flows=2, n_subflows=2, controller_name='None', path_selector="None", num_paths=8, path_penalty=100, seed="NO-SEED", path_selector_preset="None",  output_folder="mininet"):
    """
    A mesh-based experiment using the multipath custom controller.
    Hosts are assigned random positions until there is one per satellite, and flows begin at the same time.
    Meant to represent a worst-case scenario for congestion.
    TODO: find a deterministic way of adding positions. Maybe adapt the origianl manhattan animation script (look at manhattan_varied as an example)
    Intended values: 
        mesh_size = 4, 
        flows = mesh_size^2 / 2 (exactly one host per node)
        duration >= 20          (Don't run short experiment here, if your computer is busy then hosts can take a few seconds to get fully connected)
        delay ~= 18             (average ISL delay for starlink)
    """
    # This experiment is intended to be run only on the MultiCompetitionTopo
    if topology == "manhattan_openflow":
        topo = ManhattanOpenflow(**params)
    else:
        printRed("ERROR: topology \'%s\' not recognised" % topology)
        return

    # Experiment properties
    duration = 60
    subflows = n_subflows
    mesh_size = int(params.get('mesh_size') )

    
    bdp_in_bytes = int(bw * (2 ** 20) * 2 * delay * (10 ** -3) / 8)
    qsize_in_bytes = max(int(qmult * bdp_in_bytes), 1500)
    
    if seed != "NO-SEED":
        printGreen(f'USING SEED {seed}')
        random.seed(seed) # Set the specified seed for consistent results. Otherwise, randomize with each run (if this experiment contains any randomness)
    

    if path_selector == "preset":
        controller_path = path_selector_preset
    else:
        controller_path = f"{controller_name}_{path_selector}_{num_paths}maxpaths_{path_penalty}pathpenalty"
    #                                                    /Experiment_type           /events                          /network_characteristics (router/switch/link properties)                                   /routing          /protocol_parameters            /run
    output_path = f"{HOME_DIR}/cctestbed/{output_folder}/results_manhattan_openflow_random_flooded/{topology}_{seed}_{n_flows}flows/{aqm}_{bw}mbit_{delay}ms_{int(qsize_in_bytes/1500)}pkts_{loss}loss_{tcp_buffer_mult}tcpbuf/{controller_path}/{protocol}_{n_subflows}subflows/run{run}" 
    printRed(output_path)
    rmdirp(output_path)
    mkdirp(output_path)
    printGreen(f"delay is {delay}, bw is {bw}, qmult is {qmult}, qsize is {qsize_in_bytes}, bdp is {bdp_in_bytes}, loss is {loss}")
    net = Mininet(topo=topo, link=TCLink, autoSetMacs=True, autoStaticArp=True
                  ,controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653),
    )
    host_ips_list = [f"{host.IP()}:{host.name}" for host in net.hosts]
    host_ips = ' '.join(host_ips_list)
    # Start remote controller (start early to allow time for initialization)
    controller = start_remote_controller(controller_name, path_selector, num_paths, path_penalty, output_path, path_selector_preset=path_selector_preset, host_ips=host_ips)

    # Sample host positions from a random list
    host_positions = [(x, y) for x in range(1, mesh_size+1) for y in range(1, mesh_size+1)]
    random.shuffle(host_positions)
    for h, host in enumerate(net.hosts):
        x, y = host_positions[h]
        net.addLink(f'UT_{host.name}', f's{x}_{y}') 

    tcp_buffers_setup(bdp_in_bytes + qsize_in_bytes, multiplier=tcp_buffer_mult) # idk, buffers setup
    #assign_ips_by_link(net) # Assign interface IPs sequentially
    configure_ndiffports_endpoints(net, subflows)
    net.start()
    disable_offload(net)

    # EXPERIMENT:
    # -------------------------------------------------------------------------------------------------------------------------------------------
    network_config=[]       # list of network conditions, such as bandwidth, delay, and loss on each link
    traffic_config=[]       # list of connections open/close during the experiment
    monitors=['sysstat']    # list of stats/interfaces to monitor

    # Client/server/flow properties
    for f in range(1, n_flows + 1):
        network_config.append(NetworkConf(f's_c{f}', f'UT_c{f}', None,   delay/6,    3*bdp_in_bytes, True,  'fifo',  loss)) # Client<->Sat delay (Reported by starlink to be 1.8-3.6ms one-way)
        network_config.append(NetworkConf(f's_x{f}', f'UT_x{f}', None,   delay/6,    3*bdp_in_bytes, True,  'fifo',  loss)) # Server<->Sat delay (Reported by starlink to be 1.8-3.6ms one-way)
        traffic_config.append(TrafficConf(f'c{f}', f'x{f}', 0, duration, protocol)) # Standard flow for entire experiment
        # You can dynamically add links here. It works, but the controller is slow to react. Work on it if you have time. Do it before net.start() instead for now.
        # for h in ['c', 'x']:
        #     x, y = get_unique_position(mesh_size, positions=host_positions)
        #     add_switch_link(net, f'UT_{h}{f}', f's{x}_{y}')

    # Satellite mesh network config (bandwidth, delay, queues)
    for x in range (1, mesh_size+1):
        for y in range (1, mesh_size+1):
            if x != mesh_size:
                #network_config.append(NetworkConf(f's{x}_{y}', f's{x+1}_{y}', bw,     None,       qsize_in_bytes, True,    aqm,    None)) # Right
                #network_config.append(NetworkConf(f's{x}_{y}', f's{x+1}_{y}', None,   2*delay,    3*bdp_in_bytes, True,  'fifo',  loss)) # Delay
                network_config.append(NetworkConf(f's{x}_{y}', f's{x+1}_{y}', bw,     delay,       qsize_in_bytes, True,    aqm,    loss)) # COMBINED DELAY/BW
            if y != mesh_size:
                #network_config.append(NetworkConf(f's{x}_{y}', f's{x}_{y+1}', bw,     None,       qsize_in_bytes, True,    aqm,    None)) # Above
                #network_config.append(NetworkConf(f's{x}_{y}', f's{x}_{y+1}', None,   2*delay,    3*bdp_in_bytes, True,  'fifo',  loss)) # Delay
                network_config.append(NetworkConf(f's{x}_{y}', f's{x}_{y+1}', bw,     delay,       qsize_in_bytes, True,    aqm,    loss)) # COMBINED DELAY/BW

    # Monitor all satellite interfaces
    node: Node
    for node in net.switches:
        for intf in node.intfList():
            if "eth" in intf.name:
                printPink(f'Monitoring intf {intf.name}')
                monitors.append(intf.name)
    #monitors = ["sysstat", "s2_3-eth2", "s3_1-eth2", "s4_4-eth3"]
    # printGreen(monitors)
    # -------------------------------------------------------------------------------------------------------------------------------------------
    
    em = Emulation(net, network_config, traffic_config, output_path, .1)
    em.configure_network()
    em.configure_traffic()
    em.set_monitors(monitors) # monitors switch and router queue sizes

    #CLI(net)

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

    change_all_user_permissions(output_path)
    process_raw_outputs(output_path, emulation_start_time=em.start_time) # parsers.py does its thing
    change_all_user_permissions(output_path)
    plot_all_mn(output_path,aqm=aqm, multipath=True, duration=duration, combine_graph=True)


def get_unique_position(range, positions):
    """
    Returns a random integer position within the given range (1-range inclusive)
    new positions will be added to the list and duplicate positions will be reshuffled until they are new.
    """
    while True:
        pos = (random.randint(1, range), random.randint(1, range))
        printRed(f"Pos list: \n{positions}")
        if positions != "none" and pos not in positions:
            printGreen(f"appending {pos} to pos list")
            positions.append(pos)
            break
        printRed(f"NOT appending {pos} to pos list")
    return pos

if __name__ == '__main__':
    topology = 'manhattan_openflow'
    delay = int(sys.argv[1])
    bw = int(sys.argv[2])
    qmult = float(sys.argv[3])
    protocol = sys.argv[4]
    run = int(sys.argv[5])
    aqm = sys.argv[6]
    loss = sys.argv[7]
    n_flows = int(sys.argv[8])
    n_subflows = int(sys.argv[9])
    mesh_size = int(sys.argv[10]) # for manhattan only
    controller = sys.argv[11]
    seed = str(sys.argv[12])
    path_selector = str(sys.argv[13])
    num_paths = int(sys.argv[14])
    path_penalty = float(sys.argv[15])
    path_selector_preset = str(sys.argv[16])
    output_folder = sys.argv[17]
    params = {'n': n_flows,
              'mesh_size': mesh_size}
    
    run_emulation(topology, protocol, params, bw, delay, qmult, 22, run, aqm, loss, n_flows, n_subflows, controller, path_selector, num_paths, path_penalty, seed, path_selector_preset, output_folder) #Qsize should be at least 1 MSS.
