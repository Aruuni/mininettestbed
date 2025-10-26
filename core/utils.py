import sys,os, pwd, grp, re
import subprocess
from collections import namedtuple
from core.config import USERNAME
NetworkConf = namedtuple("NetworkConf", ['node1', 'node2', 'bw', 'delay', 'qsize', 'bidir', 'aqm', 'loss'])
TrafficConf = namedtuple("TrafficConf", ['source', 'dest', 'start', 'duration', 'protocol', 'params'])

Command = namedtuple("Command", ['command', 'params', 'waiting_time', 'node'])
default_dir = '.'

NetworkConf.__new__.__defaults__ = (None,) * len(NetworkConf._fields)
TrafficConf.__new__.__defaults__ = (None,) * len(TrafficConf._fields)

IPERF = ['bbr', 'bbr1', 'pcc', 'cubic', 'snap']
ORCA = ['orca', 'sage']

def mkdirp(path: str) -> None:
    """
    Recursive mkdir with permissive mode and optional chown to `username`.
    """
    try:
        os.makedirs(path, mode=0o770, exist_ok=True)
    except OSError:
        if not os.path.isdir(path):
            raise
    try:
        pw = pwd.getpwnam(USERNAME)
        os.chown(path, pw.pw_uid, pw.pw_gid)
    except KeyError:
        raise RuntimeError(f"User {USERNAME} not found")
                               
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
def remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        if os.path.isfile(path):
            raise
        
def to_bytes(value: str) -> int:
    if isinstance(value, int):
        return value

    s = str(value).strip().replace('_', '')
    m = re.fullmatch(r'(?i)\s*(\d+)\s*([KMG]?b)?\s*', s)
    if not m:
        raise ValueError(f"Unrecognized size format: {value!r}")

    n = int(m.group(1))
    suffix = (m.group(2) or '').lower()

    # Match tc’s SI byte units
    mul = {'': 1, 'b': 1, 'kb': 1_000, 'mb': 1_000_000, 'gb': 1_000_000_000, }
    return n * mul.get(suffix, 1)

def dump_system_config(path: str) -> None:
    with open(f'{path}/sysctl.txt', 'w') as fout:
        fout.write(subprocess.check_output(['sysctl', 'net.core.netdev_max_backlog']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_rmem']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_wmem']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_mem']) + '\n')
        fout.write(subprocess.check_output(['sysctl', 'net.ipv4.tcp_window_scaling']) + '\n')

def handle_interrupt(signum, frame):
    """Handle SIGINT and SIGTERM signals to clean up Mininet properly."""
    print("\n[!] Caught interrupt signal, cleaning up Mininet...")
    try:
        subprocess.run(["sudo", "mn", "-c"], check=False)
        print("[✓] Mininet cleaned up successfully.")
    except Exception as e:
        print(f"[x] Error during cleanup: {e}")
    finally:
        sys.exit(0)

def change_all_user_permissions(path: str) -> None:
    subprocess.call(['sudo','chown', '-R',USERNAME, path])


def tcp_buffers_setup(target_bdp_bytes: int, multiplier=3) -> None:
    # WE WANT BIG BEAUTIFUL TCP BUFFERS, SOME SAY THE BIGGEST BUFFERS, I LOOK AT THESE BUFFERS AND I SAY: "WOW, WHAT A BEAUTIFUL BUFFER"
    os.system(f"sudo sysctl -w net.ipv4.tcp_rmem='10240 87380 {multiplier*target_bdp_bytes}' > /dev/null")
    os.system(f"sudo sysctl -w net.ipv4.tcp_wmem='10240 87380 {multiplier*target_bdp_bytes}' > /dev/null")


def disable_offload(net) -> None:
    for node_name, node in net.items():
        for intf_name in node.intfNames():
            if 'c' in  intf_name or 'x' in intf_name:
                node.cmd(f'sudo ethtool -K {intf_name} tso off')
                node.cmd(f'sudo ethtool -K {intf_name} gro off')
                node.cmd(f'sudo ethtool -K {intf_name} gso off')
                node.cmd(f'sudo ethtool -K {intf_name} lro off')
                # node.cmd(f'sudo ethtool -K {intf_name} ufo off')
            if 's' in intf_name:
                os.system(f'sudo ethtool -K {intf_name} tso off')
                os.system(f'sudo ethtool -K {intf_name} gro off')
                os.system(f'sudo ethtool -K {intf_name} gso off')
                os.system(f'sudo ethtool -K {intf_name} lro off')
                #os.system('sudo ethtool -K {intf_name} ufo off') no need as no udp traffic


ERROR = -3
DEBUG=0
INFO=1
ALL=2

_COLORS = {
    "reset": "\033[0m",

    # foreground (text)
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",

    # background (fill)
    "black_fill":   "\033[40m",
    "red_fill":     "\033[41m",
    "green_fill":   "\033[42m",
    "yellow_fill":  "\033[43m",
    "blue_fill":    "\033[44m",
    "magenta_fill": "\033[45m",
    "cyan_fill":    "\033[46m",
    "white_fill":   "\033[47m",
}

LOG_LEVEL = 1


RESET = "\033[0m"
def printC(msg: str, color="white", log_level=2) -> None:
    """
    Possible colors: black, red, green, yellow, blue, magenta, cyan, white. Can use [color]_fill for background color.  \\
    Log levels: ERROR=-3, DEBUG=0, INFO=1, ALL=2.
    """
    if log_level <= LOG_LEVEL:
        print(f"{_COLORS[color]}{msg}{RESET}", flush=True)
