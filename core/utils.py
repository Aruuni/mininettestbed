import os 
import subprocess
from mininet.net import Mininet
from collections import namedtuple
from core.config import USERNAME
from mininet.node import OVSKernelSwitch, Host, Node, Link, Intf
import ipaddress
NetworkConf = namedtuple("NetworkConf", ['node1', 'node2', 'bw', 'delay', 'qsize', 'bidir', 'aqm', 'loss'])
TrafficConf = namedtuple("TrafficConf", ['source', 'dest', 'start', 'duration', 'protocol', 'params'])

Command = namedtuple("Command", ['command', 'params', 'waiting_time', 'node'])
default_dir = '.'

NetworkConf.__new__.__defaults__ = (None,) * len(NetworkConf._fields)
TrafficConf.__new__.__defaults__ = (None,) * len(TrafficConf._fields)

IPERF = ['bbr', 'bbr1', 'pcc', 'cubic', 'snap', 'lia', 'olia', 'balia', 'wvegas']
ORCA = ['orca', 'sage']

def mkdirp(path: str) -> None:
    try:
        os.makedirs( path,0o777 )
    except OSError:
        if not os.path.isdir( path ):
            raise

def rmdirp(path: str) -> None:
    try:
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(path)
    except OSError as e:
        if os.path.isdir(path):
            raise

def convert_to_mega_units(string):
    value, units = string.split(" ")
    if "K" in units:
        return float(value)/(2**10)
    elif "M" in units:
        return float(value)
    elif "G" in units:
        return float(value)*(2**10)
    else:
        return float(value)/(2**20)

def dump_system_config(path):
    with open('%s/sysctl.txt' % (path), 'w') as fout:
        fout.write(subprocess.check_output(['sysctl', 'net.core.netdev_max_backlog']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_rmem']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_wmem']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_mem']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_window_scaling']) + '\n')

def change_all_user_permissions(path):
    subprocess.call(['sudo','chown', '-R',USERNAME, path])


def tcp_buffers_setup(target_bdp_bytes, multiplier=3):
    # --- Configure TCP Buffers on all senders and receivers
    # The send and receive buffer sizes should be set to at least
    # 2BDP (if BBR is used as the congestion control algorithm, this should be set to even a
    # larger value). We also want to account for the router/switch buffer size, makingsure
    # the tcp buffer is not the bottleneck.

    if multiplier:
        os.system('sudo sysctl -w net.ipv4.tcp_rmem=\'10240 87380 %s\'' % (multiplier*(target_bdp_bytes)))
        os.system('sudo sysctl -w net.ipv4.tcp_wmem=\'10240 87380 %s\'' % (multiplier*(target_bdp_bytes)))

def disable_offload(net):
    for node_name, node in net.items():
        for intf_name in node.intfNames():
            if intf_name.startswith('c') or intf_name.startswith('x'):
                node.cmd('sudo ethtool -K %s tso off' % intf_name)
                node.cmd('sudo ethtool -K %s gro off' % intf_name)
                node.cmd('sudo ethtool -K %s gso off' % intf_name)
                node.cmd('sudo ethtool -K %s lro off' % intf_name)
                node.cmd('sudo ethtool -K %s ufo off' % intf_name)
            if intf_name.startswith('s'):
                os.system('sudo ethtool -K %s tso off' % intf_name)
                os.system('sudo ethtool -K %s gro off' % intf_name)
                os.system('sudo ethtool -K %s gso off' % intf_name)
                os.system('sudo ethtool -K %s lro off' % intf_name)
                #os.system('sudo ethtool -K %s ufo off' % intf_name) no need as no udp traffic


class MPMininetWrapper(Mininet):
    """
    Wrapper around Mininet to enable make hosts MPTCP ready by setting IP addresses and setting up routing.
    IP schema:
        10.0.x.y: where y denotes the host id and x the interface id, e.g. h1-eth0 has 10.0.0.1 and h2-eth2 has 10.0.1.2
    """
    HOST_IP = '10.0.{0}.{1}'
    HOST_MAC = '00:00:00:00:{0:02x}:{1:02x}'

    def __init__(self, *args, **kwargs):
        super(MPMininetWrapper, self).__init__(*args, **kwargs)
        print("Mininet object initialized. Performing MPTCP setup...")
        self.setup_routing()

    def setup_routing(self, ndiffports=True):
        """
        Set IP and MAC address for each interface on each host.
        :return:    None
        """

        # Loop through each host in the network
        for h, host in enumerate(self.hosts, start=1):
            subflow_count = 6

            # # Set appropriate MPTCP config values (I don't think either of these work right now??)
            # host.cmd('sudo sysctl -w net.mptcp.path_manager=kernel') # Mininet hosts need kernel path manager, host machine needs userspace
            # host.cmd('sudo sysctl -w net.mptcp.pm=0') # Mininet hosts need pm=0, host machine needs pm=1
            # host.cmd(f'ip mptcp limits set subflows {subflow_count}') # Max number of accepted subflows (upstream kernel, client and server)
            # host.cmd(f'ip mptcp limits set add_addr_accepted {subflow_count}') # Max number of accepted ADD_ADDR requests (upstream kernel, client)
            # host.cmd('sudo sysctl net.mptcp.mptcp_path_manager=fullmesh') # out-of-tree kernel


             # ndiffports necessary>

            # Loop through each interface in all hosts
            if ndiffports:
                host.cmd('sudo sysctl -w net.mptcp.allow_join_initial_address_port=1')
                for i, intf_name in enumerate(host.intfNames()):
                    host_id = h
                    ip = self.HOST_IP.format(i, host_id)
                    gateway = self.HOST_IP.format(i , 0)
                    mac = self.HOST_MAC.format(i, host_id)
                    endpoint_id = host_id * 10 + i + 1

                    # Configure routing tables and IP/Mac addresses in accordance with http://multipath-tcp.org/pmwiki.php/Users/ConfigureRouting
                    # host.intf(intf_name).config(ip='{}/24'.format(ip), mac=mac)
                    # host.cmd(f'ip rule add from {ip} table {i+1}')
                    # host.cmd(f'ip route add {gateway}/24 dev {intf_name} scope link table {i+1}')
                    # host.cmd(f'ip route add default via {gateway} dev {intf_name} table {i+1}')

                    # # Debug prints
                    # print('-------------------')
                    # print("host: " + str(host))
                    # print("h: "  + str(h))
                    # print("i: " + str(i))
                    # print("host_id: " + str(host_id))
                    # print("intf_name " + str(intf_name))
                    # print("ip: " + str(ip))
                    # print("gateway: " + str(gateway))
                    # print("mac: " + str(mac))
                    # print("endpoint_id: " + str(endpoint_id))
                    # print('-------------------')
            else:
                host.cmd('sudo sysctl -w net.mptcp.allow_join_initial_address_port=1')
                for i, intf_name in enumerate(host.intfNames()):
                    host_id = h
                    ip = self.HOST_IP.format(i, host_id)
                    gateway = self.HOST_IP.format(i , 0)
                    mac = self.HOST_MAC.format(i, host_id)
                    endpoint_id = host_id * 10 + i + 1

                    # Configure routing tables and IP/Mac addresses in accordance with http://multipath-tcp.org/pmwiki.php/Users/ConfigureRouting
                    host.intf(intf_name).config(ip='{}/24'.format(ip), mac=mac)
                    host.cmd(f'ip rule add from {ip} table {i+1}')
                    host.cmd(f'ip route add {gateway}/24 dev {intf_name} scope link table {i+1}')
                    host.cmd(f'ip route add default via {gateway} dev {intf_name} table {i+1}')

                    # Configure endpoints for each interface (may only be necessary for the upstream kernel)
                    host.cmd(f'ip mptcp endpoint add {ip} dev {intf_name} id {endpoint_id} subflow signal')

                    # # Debug prints
                    # print('-------------------')
                    # print("host: " + str(host))
                    # print("h: "  + str(h))
                    # print("i: " + str(i))
                    # print("host_id: " + str(host_id))
                    # print("intf_name " + str(intf_name))
                    # print("ip: " + str(ip))
                    # print("gateway: " + str(gateway))
                    # print("mac: " + str(mac))
                    # print("endpoint_id: " + str(endpoint_id))
                    # print('-------------------')
            host.cmd("echo " + str(host) + " initialized by MPMininetWrapper!")
        print("MPMininetWrapper MPTCP setup completed!")

# Maybe? useless function for setting up out-of-tree kernel MPTCP
def configure_out_of_tree_endpoints():
    pass

# Configures MPTCP endpoints the standard way (one subflow per interface)
def configure_endpoints():
    pass

# This really needs refactoring
# Configures MPTCP endpoints using the ndiffports technique (multiple subflows per interface with unique source ports, hashed to different paths via ECMP)
def configure_ndiffports_endpoints(net, subflows=2):
    for host in net.hosts:
        if not (str(host).startswith('c') or str(host).startswith('x')):
            continue

        host.cmd('sudo sysctl -w net.mptcp.path_manager=kernel') # Mininet hosts need kernel path manager
        host.cmd('sudo sysctl -w net.mptcp.pm_type=0') # Mininet hosts need pm=0
        host.cmd(f'ip mptcp limits set subflows {8}') # Max number of accepted subflows (upstream kernel, client and server)
        host.cmd(f'ip mptcp limits set add_addr_accepted {8}') # Max number of accepted ADD_ADDR requests (upstream kernel, client) 
        host.cmd('sudo sysctl -w net.mptcp.allow_join_initial_address_port=0') # needed for ndiffports
        host.cmd('sysctl net.mptcp.syn_retrans_before_tcp_fallback=50') # avoid TCP fallback for consistent experiments
        
        subflow_id = 1
        # Configures endpoints for each interface (there should only be one in ndiffports)
        for intf in host.intfList(): 
            host.cmd(f'sudo sysctl -w net.ipv4.conf.{intf}.rp_filter=0') # Make the rp_filter less strict
            for i in range(0, subflows - 1):
                if str(host).startswith('c'):
                    endpoint_cmd = f'ip mptcp endpoint add {intf.IP()} dev {intf} subflow' # id can be specfied with id {num} between dev and port
                elif str(host).startswith('x'):
                    endpoint_cmd = f'ip mptcp endpoint add {intf.IP()} dev {intf} id {subflow_id} port {9000 + i} signal' # id can be specfied with id {num} between dev and port 
                
                printBlue(f'{host} endpoint cmd: {endpoint_cmd}')
                host.cmd(endpoint_cmd)
                subflow_id += 1

# An alternative to node.connectionsTo() that respects link direction (useful for topologies that require bidirectional traffic policing)
def get_links(src_node: Node, target_node: Node):
        "Return [ intf1, intf2... ] for all intfs that connect self to node."
        # We could optimize this if it is important
        
        connections = []
        for intf in src_node.intfList():
            link = intf.link
            if link:
                node1, node2 = link.intf1.node, link.intf2.node
                if node1 == src_node and node2 == target_node:
                    connections += [ ( intf, link.intf2 ) ]
                elif node1 == target_node and node2 == src_node:
                    connections += [ ( link.intf1, intf ) ]
        printGreen(f'OLD {src_node.name} to {target_node.name} links: {src_node.connectionsTo(target_node)}')
        printPurple(f'{src_node.name} to {target_node.name} links: {connections}')
        return connections

# Adds a routing table entry to the given router, towards the dst_ip, through the nodes listed in next_hop_names
# This should be much more deterministic and reliable than assign_ECMP_routing_tables(). Use this to patch any mistakes it makes.
def add_route(net, router_name: str, next_hop_names: list[str], dst_ip: str, directional=False, ECMP=True, debug=True):
    router: Node = net.get(router_name)
    next_hop_intfs = [] # List of interfaces to route through
    if ECMP:
        router.cmd('sysctl net.ipv4.fib_multipath_hash_policy=1') # Enable layer 4 ECMP hashing (based on src ip, src port, dst ip, dst port, protocol)
    else:
        router.cmd('sysctl net.ipv4.fib_multipath_hash_policy=0') # Disable layer 4 ECMP hashing (based on src ip, src port, dst ip, dst port, protocol)
    # Find the correct target interface on each next_hop node
    for hop_name in next_hop_names:
        target_node: Node = net.get(hop_name)
        intf: Intf

        connecting_intf = None
        if directional:
            for link_intfs in get_links(router, target_node):
                if link_intfs[0].node.name == router_name: # Only recognizes the connecting interface if the link direction matches the routing direction (router -> nexthop)
                    connecting_intf = link_intfs[1]
        else:
            connecting_intf = router.connectionsTo(target_node)[0][1] # Recognizes the connecting interface regardless of link direction
        
        if connecting_intf:
            next_hop_intfs.append(connecting_intf)
        else:
            printRed(f"ERROR! {router_name} cannot route through {hop_name} because it is not directly linked.")
            return

    # Build the command based on the given target interfaces
    if len(next_hop_intfs) == 1:
        cmd = f'ip route replace {dst_ip} via {next_hop_intfs[0].IP()}'
    elif len(next_hop_intfs) > 1:
        cmd = f'ip route replace {dst_ip}'
        weight = 1
        for intf in next_hop_intfs:
            cmd = cmd + ' ' + (f'nexthop via {intf.IP()} weight {1}')
            weight += 1
    else:
        printRed("ERROR: Routing tabled incorrectly configured")
    
    # Send the command to the node
    if debug:
        printTC(f'Running the following command in {router_name}\'s terminal: {cmd}')
    router.cmdPrint(cmd)
        
# Adds a routing table entry to the given router, towards the dst_ip, through the nodes listed in next_hop_names
# This should be much more deterministic and reliable than assign_ECMP_routing_tables(). Use this to patch any mistakes it makes.
def add_default_gateway(net, router_name: str, next_hop_names: list[str], debug=True):
    router: Node = net.get(router_name)
    next_hop_intfs = [] # List of interfaces to route through

    # Find the correct target interface on each next_hop node
    for hop_name in next_hop_names:
        target_node: Node = net.get(hop_name)
        intf: Intf

        connecting_intf = router.connectionsTo(target_node)[0][1]
        if connecting_intf in target_node.intfList():
            next_hop_intfs.append(connecting_intf)
        else:
            printRed(f"ERROR! {router_name} cannot route through {hop_name} because it is not directly linked.")
            return

    # Build the command based on the given target interfaces
    if len(next_hop_intfs) == 1:
        cmd = f'ip route add default via {next_hop_intfs[0].IP()}'
    else:
        printRed("ERROR: Could not add default gateway")
    
    # Send the command to the node
    if debug:
        printPink(f'Running the following command in {router_name}\'s terminal: {cmd}')
    router.cmd(cmd)

# Assigns unique IPs within the same subnet to each link's interface pair
# limit of 256 links, or 256 nodes, or 256 nodes on a single interface
def assign_ips(net: Mininet):
    # List of unique IDs for each node, used for IP/subnet assignment
    node_ids = {}
    nodes_visited = 0
    
    # IP assignment Loop
    for link_num, link in enumerate(net.links):
        # printRed('---------------------')
        # print(link)

        interfaces = [link.intf1, link.intf2]
        # Assign IPs within the same subnet to the interface pair
        for intf in interfaces: 
            intf_id = str(intf).split('eth')[1] # Gets the number after 'eth'
            node = intf.node
            # If this is the first time we've seen a particular node, assign it a new ID
            if node not in node_ids:
                node_ids[node] = nodes_visited
                nodes_visited += 1
            ip = f'10.{link_num}.{node_ids[node]}.{nodes_visited%255}/16'
            node.setIP(ip, intf=str(intf))
            # print(intf)
            # printGreen(ip)

# Assigns IPs to maximize the number of links while maintaining correct link subnets
# Probably the best default, as long as you aren't attempting any sort of hierarchical routing
def assign_ips_by_link(net: Mininet):
    # List of unique IDs for each node, used for IP/subnet assignment
    
    # IP assignment Loop
    for link_num, link in enumerate(net.links):
        interfaces = [link.intf1, link.intf2]
        # Assign IPs within the same subnet to the interface pair
        for i, intf in enumerate(interfaces): 
            a = int(link_num/256%256)
            b = int(link_num%256)
            ip = f'10.{a}.{b}.{i}/24' # 10.link.link.intf - link num spans two bytes, intf is per link (0 or 1)
            intf.node.setIP(ip, intf=str(intf))
            # print(intf)
            # printGreen(ip)


# Assigns interface IPs sequentially, maximizing the amount of possible IPs
# Ensure unique IPs for each interface, but may break default gateways and make routing/debugging tricky
def assign_sequential_ips(net: Mininet):
    # List of unique IDs for each node, used for IP/subnet assignment
    intf_visited = 4278190080 # skip the 0.0.0.0/8 subnet
    
    # IP assignment Loop
    for link in net.links:
        interfaces = [link.intf1, link.intf2]
        for intf in interfaces: 
            ip = f'{ipaddress.IPv4Address(intf_visited)}/16' # Assign IP sequentially
            intf.node.setIP(ip, intf=str(intf))
            intf_visited += 1

            print(intf)
            printGreen(ip)

# # Assigns routing tables and default gateways to every host. Assumes all links are forward-facing from c1 to x1.
# def assign_routing_tables(net: Mininet):
#     # Routing table assignment loop
#     for link_num, link in enumerate(net.links):
#         printGreen('---------------------')
#         print(link)

#         interfaces = [link.intf1, link.intf2]
#         node_a = interfaces[0].node
#         node_b = interfaces[1].node
#         printPink(interfaces[0].ip)
#         printPink(interfaces[1].ip)

#         if 'c' in str(node_a):
#             printBlue("found c1")
#             c1cmd = f'ip route add default via {interfaces[1].IP()}'
#             printPurple(f"C1CMD: {c1cmd}")
#             node_a.cmd(c1cmd)
#         elif 'x' in str(node_b):
#             printBlue("found x1")
#             node_b.cmd(f'ip route add default via {interfaces[0].IP()}')
#         else:
#             c1_ip = net.get('c1').IP(intf='c1-eth0')
#             x1_ip = net.get('x1').IP(intf='x1-eth0')
#             node_a.cmd(f'ip route add {x1_ip} via {interfaces[1].IP()}') # Forward
#             node_b.cmd(f'ip route add {c1_ip} via {interfaces[0].IP()}') # Backward

# Assigns routing tables and default gateways to every host. Assumes all links are forward-facing from c1 to x1.
# Adds a special case for routers with multiple paths
def enable_ECMP_all_routers(net: Mininet):
    for router in net.hosts:
        router.cmd('sysctl net.ipv4.fib_multipath_hash_policy=1') # Enable layer 4 ECMP hashing (based on src ip, src port, dst ip, dst port, protocol)

def assign_ECMP_routing_tables(net: Mininet):
    # Contains a list of hops for each router toward either c1 or x1
    forward_hops = {} # r1 : [ip_1, ip_2, ...]
    backward_hops = {} # node : [ip_1, ip_2, ...]

    # Routing table assignment loop
    for link_num, link in enumerate(net.links):
        # printGreen('---------------------')
        # print(link)

        interfaces = [link.intf1, link.intf2]
        node_a = interfaces[0].node
        node_b = interfaces[1].node
        # printPink(interfaces[0].ip)
        # printPink(interfaces[1].ip)
        
        # Add default gateways if the links contains a client/server, otherwise add IPs to routing table lists
        if str(node_a).startswith('c'):
            c1cmd = f'ip route add default via {interfaces[1].IP()}'
            # printPurple(f"Sending command to c1: {c1cmd}")
            node_a.cmd(c1cmd)
        elif str(node_b).startswith('x'):
            x1cmd = f'ip route add default via {interfaces[0].IP()}'
            # printPurple(f"Sending command to x1: {c1cmd}")
            node_b.cmd(x1cmd)
        else:
            if node_a not in forward_hops: 
                forward_hops[node_a] = []
            if node_b not in backward_hops:
                backward_hops[node_b] = []
            forward_hops[node_a].append( f'{interfaces[1].IP()} dev {interfaces[0]}') # Add a possible route from node_a to x1
            backward_hops[node_b].append( f'{interfaces[0].IP()} dev {interfaces[1]}') # Add a possible route from node_b to c1

    c1_ip = net.get('c1').IP(intf='c1-eth0')
    x1_ip = net.get('x1').IP(intf='x1-eth0')   

    # print("FORWARD HOPS: ")
    # print(forward_hops)
    # print("BACKWARD HOPS: ")
    # print(backward_hops)

    # Create routing table entries toward x1 for each router
    for router in forward_hops:
        router.cmd('sysctl net.ipv4.fib_multipath_hash_policy=1') # Enable layer 4 ECMP hashing (based on src ip, src port, dst ip, dst port, protocol)
        routes = len(forward_hops[router])
        if routes == 1:
            cmd = f'ip route add {x1_ip} via {forward_hops[router][0]}'
        elif routes > 1:
            cmd = f'ip route add {x1_ip}'
            weight = 1
            for ip in forward_hops[router]:
                cmd = cmd + ' ' + (f'nexthop via {ip} weight {1}')
                weight += 1
        else:
            printRed("ERROR: Routing tabled incorrectly configured")
        # printGreen(f'{router}: {cmd}')
        router.cmd(cmd)
    
    # Create routing table entries toward c1 for each router
    for router in backward_hops:
        router.cmd('sysctl net.ipv4.fib_multipath_hash_policy=1') # Enable layer 4 ECMP hashing (based on src ip, src port, dst ip, dst port, protocol)
        routes = len(backward_hops[router])
        if routes == 1:
            cmd = f'ip route add {c1_ip} via {backward_hops[router][0]}'
        elif routes > 1:
            cmd = f'ip route add {c1_ip}'
            for ip in backward_hops[router]:
                cmd = cmd + ' ' + (f'nexthop via {ip} weight 1')
        else:
            printRed("ERROR: Routing tabled incorrectly configured")
        # printGreen(f'{router}: {cmd}')
        router.cmd(cmd)

def get_intf(net, ip):
    for h in net.hosts:
        for intf in h.intfList():
            if intf.IP() == ip:
                return intf.name

RESET = "\033[0m"

def printDebug(string):
    COLOR="\033[95m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")
def printDebug2(string):
    COLOR="\033[103m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")
def printDebug3(string):
    COLOR="\033[42m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")
def printBlue(string):
    COLOR = "\033[94m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printBlueFill(string):
    COLOR = "\033[104m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printGreen(string):
    COLOR = "\033[32m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printGreenFill(string):
    COLOR = "\033[102m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printYellow(string):
    COLOR = "\033[33m" 
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printYellowFill(string):
    COLOR = "\033[103m" 
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printRed(string):
    COLOR = "\033[31m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printSS(string):
    COLOR = "\033[33m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printTC(string):
    COLOR = "\033[90m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printPink(string):
    COLOR = "\033[95m"
    print("\r\033[K", end='', flush=True) 
    print(f"{COLOR}{string}{RESET}")

def printPinkFill(string):
    COLOR = "\033[105m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")