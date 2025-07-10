import os 
import subprocess
from mininet.net import Mininet
from collections import namedtuple
from core.config import USERNAME
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
            if 'c' in  intf_name or 'x' in intf_name:
                node.cmd('sudo ethtool -K %s tso off' % intf_name)
                node.cmd('sudo ethtool -K %s gro off' % intf_name)
                node.cmd('sudo ethtool -K %s gso off' % intf_name)
                node.cmd('sudo ethtool -K %s lro off' % intf_name)
                node.cmd('sudo ethtool -K %s ufo off' % intf_name)
            if 's' in intf_name:
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

    def setup_routing(self):
        """
        Set IP and MAC address for each interface on each host.
        :return:    None
        """

        # Loop through each host in the network
        for h, host in enumerate(self.hosts, start=1):
            # Set appropriate MPTCP config values (I don't think either of these work right now??)
            host.cmd('ip mptcp limits set add_addr_accepted 1') # upstream kernel
            host.cmd('sudo sysctl net.mptcp.mptcp_path_manager=fullmesh') # out-of-tree kernel

            # Loop through each interface in all hosts
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

                # Debug prints
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

RESET = "\033[0m"

def printDebug(string):
    COLOR="\033[95m"
    print(f"{COLOR}{string}{RESET}")
def printDebug2(string):
    COLOR="\033[103m"
    print(f"{COLOR}{string}{RESET}")
def printDebug3(string):
    COLOR="\033[42m"
    print(f"{COLOR}{string}{RESET}")




def printBlue(string):
    COLOR = "\033[94m"
    print(f"{COLOR}{string}{RESET}")

def printBlueFill(string):
    COLOR = "\033[104m"
    print(f"{COLOR}{string}{RESET}")

def printGreen(string):
    COLOR = "\033[32m"
    print(f"{COLOR}{string}{RESET}")

def printGreenFill(string):
    COLOR = "\033[102m"
    print(f"{COLOR}{string}{RESET}")

def printPurple(string):
    COLOR = "\033[93m" 
    print(f"{COLOR}{string}{RESET}")

def printRed(string):
    COLOR = "\033[31m"
    print(f"{COLOR}{string}{RESET}")

def printSS(string):
    COLOR = "\033[33m"
    print(f"{COLOR}{string}{RESET}")

def printTC(string):
    COLOR = "\033[90m"
    print(f"{COLOR}{string}{RESET}")

def printPink(string):
    COLOR = "\033[95m" 
    print(f"{COLOR}{string}{RESET}")

def printPinkFill(string):
    COLOR = "\033[105m"
    print(f"{COLOR}{string}{RESET}")