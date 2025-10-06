import os, re
from subprocess import Popen, PIPE
from multiprocessing import Process
from time import sleep, time
from core.parsers import *
from core.utils import *

def monitor_qlen(iface: str, interval_sec=0.1, path=default_dir) -> None:
    mkdirp(path)
    start = time()
    fname=f"{path}/{iface}.txt"
    pat_queued = re.compile(r'backlog\s+([\d]+\w+)\s+\d+p')
    pat_dropped = re.compile(r'dropped\s+([\d]+)') 
    cmd = f"tc -s qdisc show dev {iface}"
    f = open(fname, 'w')
    f.write("time,root_pkts,root_drp,child_pkts,child_drp\n")
    f.close()
    matches_queued_root, matches_dropped_root, matches_queued_child, matches_dropped_child = 0, 0, 0, 0
    while 1:
        p = Popen(cmd, shell=True, stdout=PIPE)
        output = p.stdout.read()
        tmp = ""
        output = output.decode('utf-8')
        matches_queued = pat_queued.findall(output)
        matches_dropped = pat_dropped.findall(output)
        if len(matches_queued) != len(matches_dropped):
            print("WARNING: Two matches have different lengths!")
            print(output)

        if matches_queued and matches_dropped:
            tmp += f"{time()-start},{to_bytes(matches_queued[0]) - matches_queued_root},{int(matches_dropped[0]) - matches_dropped_root}"
            matches_queued_root, matches_dropped_root = to_bytes(matches_queued[0]), int(matches_dropped[0])
            if len(matches_queued) > 1 and len(matches_dropped)> 1: 
                tmp += f",{to_bytes(matches_queued[1]) - matches_queued_child},{int(matches_dropped[1]) - matches_dropped_child}\n"
                matches_queued_child, matches_dropped_child = to_bytes(matches_queued[1]), int(matches_dropped[1])

            else:
                tmp += ",,\n"
        f = open(fname, 'a')
        f.write(tmp)
        f.close
        sleep(interval_sec)
    return

def monitor_qlen_on_router(iface: str, mininode, interval_sec=0.1, path = default_dir) -> None:
    mkdirp(path)
    fname=f"{path}/{iface}.txt"
    start = time()
    pat_queued = re.compile(r'backlog\s+([\d]+\w+)\s+\d+p')
    pat_dropped = re.compile(r'dropped\s+([\d]+)') 
    cmd = f"tc -s qdisc show dev {iface}"
    f = open(fname, 'w')
    f.write("time,root_pkts,root_drp,child_pkts,child_drp\n")
    f.close()
    while 1:
        output = mininode.cmd(cmd)
        tmp = ""
        matches_queued = pat_queued.findall(output)
        matches_dropped = pat_dropped.findall(output)
        if len(matches_queued) != len(matches_dropped):
            print("WARNING: Two matches have different lengths!")
            print(output)
        if matches_queued and matches_dropped:
            tmp += f"{time()-start},{matches_queued[0]},{matches_dropped[0]}"
            if len(matches_queued) > 1 and len(matches_dropped)> 1: 
                tmp += f",{matches_queued[1]},{matches_dropped[1]}\n"
            else:
                tmp += ",,\n"
        f = open(fname, 'a')
        f.write(tmp)
        f.close
        sleep(interval_sec)
    return

def start_sysstat(interval: int, count: int, folder: str, node=None) -> None:
    mkdirp(f"{folder}/sysstat")
    if node == None:
        cmd = f"sudo /usr/lib/sysstat/sadc -S SNMP {interval} {count} {folder}/sysstat/datafile_root.log &"
        os.system(cmd)
    else:
        cmd = f"sudo /usr/lib/sysstat/sadc -S SNMP {interval} {count} {folder}/sysstat/datafile_{node.name}.log &"
        node.popen(cmd,shell=True)

def stop_sysstat(folder: str, sending_nodes: list) -> None:
    #Popen("killall -9 sadc", shell=True).wait()
    # Run sadf to generate CSV like (semi-colon separated) file
    cmd = f"sadf -d -U -- -n DEV {folder}/sysstat/datafile_root.log > {folder}/sysstat/dev_root.log"
    Popen(cmd, shell=True).wait()
    cmd = f"sadf -d -U -- -n EDEV {folder}/sysstat/datafile_root.log > {folder}/sysstat/edev_root.log"
    Popen(cmd, shell=True).wait()
    cmd = f"sadf -d -U -- -P ALL {folder}/sysstat/datafile_root.log > {folder}/sysstat/cpu_root.log"
    Popen(cmd, shell=True).wait()
    for node_name in sending_nodes:
        # Run sadf to generate CSV like (semi-colon separated) file
        cmd = f"sadf -d -U -- -n DEV {folder}/sysstat/datafile_{node_name}.log > {folder}/sysstat/dev_{node_name}.log"
        Popen(cmd, shell=True).wait()
        cmd = f"sadf -d -U -- -n EDEV {folder}/sysstat/datafile_{node_name}.log > {folder}/sysstat/edev_{node_name}.log"
        Popen(cmd, shell=True).wait()
        cmd = f"sadf -d -U -- -n ETCP {folder}/sysstat/datafile_{node_name}.log > {folder}/sysstat/etcp_{node_name}.log"
        Popen(cmd, shell=True).wait()
        cmd = f"sadf -d -U -- -n UDP {folder}/sysstat/datafile_{node_name}.log > {folder}/sysstat/udp_{node_name}.log"
        Popen(cmd, shell=True).wait()
        cmd = f"sadf -d -U -- -P ALL {folder}/sysstat/datafile_{node_name}.log > {folder}/sysstat/cpu_{node_name}.log"
        Popen(cmd, shell=True).wait()
    return