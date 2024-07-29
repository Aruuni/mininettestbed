import os
import subprocess
from collections import namedtuple

NetworkConf = namedtuple("NetworkConf", ['node1', 'node2', 'bw', 'delay', 'qsize', 'bidir', 'aqm', 'loss'])
TrafficConf = namedtuple("TrafficConf", ['source', 'dest', 'start', 'duration', 'proto', 'params'])
Command = namedtuple("Command", ['command', 'params', 'waiting_time'])
default_dir = '.'

NetworkConf.__new__.__defaults__ = (None,) * len(NetworkConf._fields)
TrafficConf.__new__.__defaults__ = (None,) * len(TrafficConf._fields)


def mkdirp( path ):
    try:
        os.makedirs( path,0o777 )
    except OSError:
        if not os.path.isdir( path ):
            raise

def rmdirp(path):
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
    subprocess.call(['chmod', '-R', 'u+w', path])
    subprocess.call(['chmod', '-R', 'u+r', path])

def tcp_buffers_setup(target_bdp_bytes, multiplier=3):
    # --- Configure TCP Buffers on all senders and receivers
    # The send and receive buffer sizes should be set to at least
    # 2BDP (if BBR is used as the congestion control algorithm, this should be set to even a
    # larger value). We also want to account for the router/switch buffer size, makingsure
    # the tcp buffere is not the bottleneck.

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
                os.system('sudo ethtool -K %s ufo off' % intf_name)



RESET = "\033[0m"

def printDebug(string):
    start = "\033[95m" # pink
    print(f"{start}{string}{RESET}")
def printDebug2(string):
    start = "\033[103m" # yellow
    print(f"{start}{string}{RESET}")
def printDebug3(string):
    start = "\033[42m\033[30m" # green
    print(f"{start}{string}{RESET}")




def printIperf3(string):
    start = "\033[104m" # background blue
    print(f"{start}{string}{RESET}")
def printIperf3SS(string):
    start = "\033[94m" # blue
    print(f"{start}{string}{RESET}")


def printOrca(string):
    start = "\033[102m" # backgroundgreen
    print(f"{start}{string}{RESET}")
def printOrcaSS(string):
    start = "\033[32m" # green
    print(f"{start}{string}{RESET}")


def printSage(string):
    start = "\033[31m" # red
    print(f"{start}{string}{RESET}")

def printSS(string):
    start = "\033[33m" # red
    print(f"{start}{string}{RESET}")

def printTC(string):
    start = "\033[90m" # gray
    print(f"{start}{string}{RESET}")
