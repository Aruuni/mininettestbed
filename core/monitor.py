from subprocess import Popen, PIPE
from core.parsers import *
from multiprocessing import Process
from time import sleep, time
import subprocess
import os
import re
from core.utils import *

def monitor_qlen(iface, interval_sec = 0.1, path = default_dir, debug=True):
    """
    Runs and records output of tc at a regular interval on the given interface.
    Used to monitor qdisc statistics, like queue sizes and packet dropped
    """
    mkdirp(path) # Create queues the output directory (and its parent folders)
    filename=f'{path}/{iface}.txt'
    tc_cmd = f"tc -s qdisc show dev {iface}" # Command to check interface info
    file = open(filename, 'w') # open the file in write mode (deletes if exists)
    file.write('time,qdisc_name,qdisc_id,qdisc_pkts,qdisc_drp\n')
    file.close()
    pat_name = re.compile(r"qdisc\s+(\w+)\s+\d+:")  # Qdisc name
    pat_id = re.compile(r"qdisc\s+\w+\s+(\d+):")  # Qdisc ID
    pat_queued = re.compile(r'backlog\s+([\d]+\w+)\s+\d+p') # Number of packets ("backlog" in the tc output)
    pat_dropped = re.compile(r'dropped\s+([\d]+)') # Number of packets dropped, cumulative ("dropped" in the tc output)

    debug_print_freq = 30 # Debug print every n iterations
    debug_count = 0 # used for debug prints
    while 1:
        # Run TC (outputs a single line) and match important values on that line
        tc_process = Popen(tc_cmd, shell=True, stdout=PIPE)
        tc_output = tc_process.stdout.read().decode('utf-8')
        matches_name = pat_name.findall(tc_output)
        matches_id = pat_id.findall(tc_output)
        matches_queued = pat_queued.findall(tc_output)
        matches_dropped = pat_dropped.findall(tc_output)
        if debug and debug_count == 0:
                debug_count = (debug_count + 1) % debug_print_freq
                printGreen(iface)
                printRed(tc_output)
        if len(matches_queued) != len(matches_dropped):
            printRed(f"WARNING: Two matches have different lengths!\n{tc_output}") # not actually an issue, just might not play nice with the parsing method. just means one of the qdiscs doesn't output both backlog and dropped.
        timestamp = time()
        for i in range(0,len(matches_name)): # for each found qdisc
            qdisc_name = matches_name[i]
            qdisc_id = matches_id[i] 
            qdisc_pkts = matches_queued[i]
            qdisc_drp = matches_dropped[i]
            qdisc_info = f"{timestamp},{qdisc_name},{qdisc_id},{qdisc_pkts},{qdisc_drp}\n"
            file = open(filename, 'a') # open file in append mode
            file.write(f'{qdisc_info}')
            file.close()
            if debug and debug_count == 0:
                printTC(qdisc_info)
        sleep(interval_sec)

def monitor_qlen_on_router(iface, mininode, interval_sec = 0.1, path = default_dir):
    mkdirp(path)
    fname='%s/%s.txt' % (path, iface)
    pat_queued = re.compile(r'backlog\s+([\d]+\w+)\s+\d+p')
    pat_dropped = re.compile(r'dropped\s+([\d]+)') 
    cmd = "tc -s qdisc show dev %s" % (iface)
    f = open(fname, 'w')
    f.write('time,root_pkts,root_drp,child_pkts,child_drp\n')
    f.close()
    while 1:
        output = mininode.cmd(cmd)
        tmp = ''
        matches_queued = pat_queued.findall(output)
        matches_dropped = pat_dropped.findall(output)
        if len(matches_queued) != len(matches_dropped):
            print("WARNING: Two matches have different lengths!")
            printGreen(iface)
            printRed(output)
        if matches_queued and matches_dropped:
            tmp += '%f,%s,%s' % (time(), matches_queued[0],matches_dropped[0])
            if len(matches_queued) > 1 and len(matches_dropped)> 1: 
                tmp += ',%s,%s\n' % (matches_queued[1], matches_dropped[1])
            else:
                tmp += ',,\n'
        f = open(fname, 'a')
        f.write(tmp)
        f.close()
        sleep(interval_sec)
    return

def monitor_ifconfig(iface, interval_sec = 1, path = default_dir):
    mkdirp(path)
    fname='%s/%s.txt' % (path, iface)
    pat_queued = re.compile(r'backlog\s+\d+\w+\s+([\d]+)p')
    pat_dropped = re.compile(r'dropped\s+([\d]+)') 
    cmd = "ifconfig %s" % (iface)
    # f = open(fname, 'w')
    # f.write('time,root_pkts,root_drp,child_pkts,child_drp\n')
    # f.close()
    while 1:
        p = Popen(cmd, shell=True, stdout=PIPE)
        output = p.stdout.read()
        # tmp = ''
        # matches_queued = pat_queued.findall(output)
        # matches_dropped = pat_dropped.findall(output)
        # if len(matches_queued) != len(matches_dropped):
        #     print("WARNING: Two mathces have different lengths!")
        #     print(output)
        # if matches_queued and matches_dropped:
        #     tmp += '%f,%s,%s' % (time(), matches_queued[0],matches_dropped[0])
        #     if len(matches_queued) > 1 and len(matches_dropped)> 1: 
        #         tmp += ',%s,%s\n' % (matches_queued[1], matches_dropped[1])
        #     else:
        #         tmp += ',,,\n'
        # f = open(fname, 'a')
        # f.write(tmp)
        # f.close
        sleep(interval_sec)
    return


def monitor_devs_ng(fname="%s/txrate.txt" % default_dir, interval_sec=1):
    """Uses bwm-ng tool to collect iface tx rate stats.  Very reliable."""
    cmd = ("sleep 1; bwm-ng -t %s -o csv "
           "-u bits -T rate -C ',' > %s" %
           (interval_sec, fname))
    Popen(cmd, shell=True).wait()

def start_qmon(iface, interval_sec=0.1, outfile="q.txt"):
    monitor = Process(target=monitor_qlen,
                      args=(iface, interval_sec, outfile))
    monitor.start()
    return monitor


def start_sysstat(interval, count, folder, node=None):
    mkdirp("%s/sysstat" % (folder))
    if node == None:
        cmd = "sudo /usr/lib/sysstat/sadc -S SNMP %s %s %s/sysstat/datafile_root.log &" % (interval, int(count), folder)
        os.system(cmd)
    else:
        cmd = "sudo /usr/lib/sysstat/sadc -S SNMP %s %s %s/sysstat/datafile_%s.log &" % (interval, int(count), folder, node.name )
        print("\033[38;2;165;42;42mSending command '%s' to node %s\033[0m" % (cmd, node.name))
        node.popen(cmd,shell=True)


def stop_sysstat(folder, sending_nodes):
    Popen("killall -9 sadc", shell=True).wait()
    # Run sadf to generate CSV like (semi-colon separated) file
    cmd = "sadf -d -U -- -n DEV %s/sysstat/datafile_root.log > %s/sysstat/dev_root.log" % (folder,folder)
    Popen(cmd, shell=True).wait()
    cmd = "sadf -d -U -- -n EDEV %s/sysstat/datafile_root.log > %s/sysstat/edev_root.log" % (folder,folder)
    Popen(cmd, shell=True).wait()
    cmd = "sadf -d -U -- -P ALL %s/sysstat/datafile_root.log > %s/sysstat/cpu_root.log" % (folder,folder)
    Popen(cmd, shell=True).wait()
    for node_name in sending_nodes:
        # Run sadf to generate CSV like (semi-colon separated) file
        cmd = "sadf -d -U -- -n DEV %s/sysstat/datafile_%s.log > %s/sysstat/dev_%s.log" % (folder,node_name,folder, node_name)
        Popen(cmd, shell=True).wait()
        cmd = "sadf -d -U -- -n EDEV %s/sysstat/datafile_%s.log > %s/sysstat/edev_%s.log" % (folder,node_name,folder, node_name)
        Popen(cmd, shell=True).wait()
        cmd = "sadf -d -U -- -n ETCP %s/sysstat/datafile_%s.log > %s/sysstat/etcp_%s.log" % (folder,node_name,folder, node_name)
        Popen(cmd, shell=True).wait()
        cmd = "sadf -d -U -- -n UDP %s/sysstat/datafile_%s.log > %s/sysstat/udp_%s.log" % (folder,node_name,folder, node_name)
        Popen(cmd, shell=True).wait()
        cmd = "sadf -d -U -- -P ALL %s/sysstat/datafile_%s.log > %s/sysstat/cpu_%s.log" % (folder,node_name,folder, node_name)
        Popen(cmd, shell=True).wait()

    return


# Should still work, I just made the code more readible so I could debug it
# def monitor_qlen_OLD(iface, interval_sec = 0.1, path = default_dir, ):
#     mkdirp(path)
#     fname='%s/%s.txt' % (path, iface)
#     pat_queued = re.compile(r'backlog\s+([\d]+\w+)\s+\d+p')
#     pat_dropped = re.compile(r'dropped\s+([\d]+)') 
#     cmd = "tc -s qdisc show dev %s" % (iface)
#     f = open(fname, 'w')
#     f.write('time,root_pkts,root_drp,child_pkts,child_drp\n')
#     f.close()
#     count = 0
#     while 1:
#         p = Popen(cmd, shell=True, stdout=PIPE)
#         output = p.stdout.read()
#         tmp = ''
#         output = output.decode('utf-8')
#         matches_queued = pat_queued.findall(output)
#         matches_dropped = pat_dropped.findall(output)
#         if len(matches_queued) != len(matches_dropped):
#             printRed("\nWARNING: Two matches have different lengths!")
#             printRed(output)
#         if matches_queued and matches_dropped:
#             tmp += '%f,%s,%s' % (time(), matches_queued[0],matches_dropped[0])
#             if len(matches_queued) > 1 and len(matches_dropped)> 1: 
#                 tmp += ',%s,%s\n' % (matches_queued[1], matches_dropped[1])
#             else:
#                 tmp += ',,\n'
#         count = (count + 1) % 100
#         if count == 1:
#             printGreen(iface)
#             printRed(output)
#             printRed("")
#         f = open(fname, 'a')
#         f.write(tmp)
#         f.close
#         sleep(interval_sec)
#     return




    
