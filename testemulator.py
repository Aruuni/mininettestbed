#!/usr/bin/env python

import sys
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink
from core.utils import *
import os 
from threading import Timer

class LinuxRouter(Node):
    "A Node with IP forwarding enabled."

    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

class DoubleDumbbellTopo(Topo):
    "Two isolated dumbbell topologies with dynamic client-server pairs."

    def build(self, num_pairs=1, delay1=10, delay2=10):
        # First Dumbbell Topology
        r1a = self.addNode('r1a', cls=LinuxRouter)
        r2a = self.addNode('r2a', cls=LinuxRouter)
        r3a = self.addNode('r3a', cls=LinuxRouter)

        # Second Dumbbell Topology
        r1b = self.addNode('r1b', cls=LinuxRouter)
        r2b = self.addNode('r2b', cls=LinuxRouter)
        r3b = self.addNode('r3b', cls=LinuxRouter)

        # Spine links
        self.addLink(r1a, r2a, intfName1='r1a-eth0', intfName2='r2a-eth0', cls=TCLink, delay=delay1)
        self.addLink(r2a, r3a, intfName1='r2a-eth1', intfName2='r3a-eth0', cls=TCLink, bw=100)

        self.addLink(r1b, r2b, intfName1='r1b-eth0', intfName2='r2b-eth0', cls=TCLink, delay=delay2)
        self.addLink(r2b, r3b, intfName1='r2b-eth1', intfName2='r3b-eth0', cls=TCLink, bw=100)

        self.addLink(r1a, r1b, intfName1='r1a-eth1', intfName2='r1b-eth1')
        self.addLink(r3a, r3b, intfName1='r3a-eth1', intfName2='r3b-eth1')


        for i in range(1, num_pairs + 1):
            c = self.addHost(f'c1_{i}', ip=f'192.168.{i}.100/24', defaultRoute=f'via 192.168.{i}.1')
            x = self.addHost(f'x1_{i}', ip=f'192.168.{i+num_pairs}.100/24', defaultRoute=f'via 192.168.{i+num_pairs}.1')
            
            c2 = self.addHost(f'c2_{i}', ip=f'192.168.{i+2*num_pairs}.100/24', defaultRoute=f'via 192.168.{i+2*num_pairs}.1')
            x2 = self.addHost(f'x2_{i}', ip=f'192.168.{i+3*num_pairs}.100/24', defaultRoute=f'via 192.168.{i+3*num_pairs}.1')

            # Links between hosts and routers
            self.addLink(c, r1a, intfName2=f'r1a-eth{i+1}')
            self.addLink(r3a, x, intfName1=f'r3a-eth{i+1}')

            # Links between hosts and routers
            self.addLink(c2, r1b, intfName2=f'r1b-eth{i+1}')
            self.addLink(r3b, x2, intfName1=f'r3b-eth{i+1}')







def configure_routing(net, num_pairs):
    "Configure static routing on routers"
    r1a, r2a, r3a = net.get('r1a', 'r2a', 'r3a')
    r1b, r2b, r3b = net.get('r1b', 'r2b', 'r3b')

    # FIRST DUMBBELL
    r1a.setIP('10.0.1.1/24', intf='r1a-eth0')

    r2a.setIP('10.0.1.2/24', intf='r2a-eth0')
    r2a.setIP('10.0.2.1/24', intf='r2a-eth1')
    
    r3a.setIP('10.0.2.2/24', intf='r3a-eth0')

    r1a.setIP('10.0.5.1/24', intf='r1a-eth1')
    r3a.setIP('10.0.6.1/24', intf='r3a-eth1')
    
    # SECOND DUMBBELL
    r1b.setIP('10.0.3.1/24', intf='r1b-eth0')

    r2b.setIP('10.0.3.2/24', intf='r2b-eth0')
    r2b.setIP('10.0.4.1/24', intf='r2b-eth1')

    r3b.setIP('10.0.4.2/24', intf='r3b-eth0')

    r1b.setIP('10.0.5.2/24', intf='r1b-eth1')
    r3b.setIP('10.0.6.2/24', intf='r3b-eth1')

    # Configure routing for the client-server pairs
    for i in range(1, num_pairs + 1):
        # interfaces between 1 and 3 nodes and the c and x nodes in their respective dumbbells
        r1a.setIP(f'192.168.{i}.1/24', intf=f'r1a-eth{i+1}')
        r3a.setIP(f'192.168.{i+num_pairs}.1/24', intf=f'r3a-eth{i+1}')

        r1b.setIP(f'192.168.{i+2*num_pairs}.1/24', intf=f'r1b-eth{i+1}')
        r3b.setIP(f'192.168.{i+3*num_pairs}.1/24', intf=f'r3b-eth{i+1}')

        x1_subnet = f'192.168.{i+num_pairs}.0/24'
        c1_subnet = f'192.168.{i}.0/24'

        x2_subnet = f'192.168.{i+3*num_pairs}.0/24'
        c2_subnet = f'192.168.{i+2*num_pairs}.0/24'
        printDebug3(f"c1_1 subnet: {c1_subnet} x1_1 subnet: {x1_subnet} c2_1 subnet: {c2_subnet} x2_1 subnet: {x2_subnet}")
        
        # Dumbbell 1 
        r1a.cmd(f'ip route add {x1_subnet} via 10.0.1.2')
        r2a.cmd(f'ip route add {x1_subnet} via 10.0.2.2')
        r2a.cmd(f'ip route add {c1_subnet} via 10.0.1.1')
        r3a.cmd(f'ip route add {c1_subnet} via 10.0.2.1')


        # Dumbbell 2
        r1b.cmd(f'ip route add {x2_subnet} via 10.0.3.2')
        r2b.cmd(f'ip route add {x2_subnet} via 10.0.4.2')
        r2b.cmd(f'ip route add {c2_subnet} via 10.0.3.1')
        r3b.cmd(f'ip route add {c2_subnet} via 10.0.4.1')
        

        # CROSS-LINKS BETWEEN DUMBBELLS
        r1a.cmd(f'ip route add {x2_subnet} via 10.0.1.2')
        r3a.cmd(f'ip route add {x2_subnet} via 10.0.6.2')

        r3a.cmd(f'ip route add {c2_subnet} via 10.0.2.1')
        r1a.cmd(f'ip route add {c2_subnet} via 10.0.5.2')

        r2a.cmd(f'ip route add {x2_subnet} via 10.0.2.2')
        r2a.cmd(f'ip route add {c2_subnet} via 10.0.1.1')

def kill_iperf3():
    os.system('killall iperf3')

def reroute_traffic(net, num_pairs):
    info("Rerouting traffic from Dumbbell 2 to Dumbbell 1...\n")
    
    r1a, r2a, r3a = net.get('r1a', 'r2a', 'r3a')
    r1b, r2b, r3b = net.get('r1b', 'r2b', 'r3b')
    # thsi is for the case of HARD handover  ??
    #r2b.cmd('ifconfig r2b-eth1 down')

    for i in range(1, num_pairs + 1):
        x2_subnet = f'192.168.{i+3*num_pairs}.0/24'
        c2_subnet = f'192.168.{i+2*num_pairs}.0/24'
        r1b.cmd(f'ip route replace {x2_subnet} via 10.0.5.1')
        r3b.cmd(f'ip route replace {c2_subnet} via 10.0.6.1')
    



def run_iperf_test(net, num_pairs):
    "Run iperf test between client and server pairs"

    # Run iperf tests for the first dumbbell
    for i in range(1, num_pairs + 1):
        c = net.get(f'c1_{i}')
        x = net.get(f'x1_{i}')
        x.cmd(f'iperf3 -s -p 500{i} -1 -i 1 -J > iperf_result_1_x{i}.json &')
        c.cmd(f'iperf3 -c {x.IP()} -p 500{i} -J -t 10 -C bbr -i 0.1 > iperf_result_1_c{i}.json &')

    # Run iperf tests for the second dumbbell
    for i in range(1, num_pairs + 1):
        c = net.get(f'c2_{i}')
        x = net.get(f'x2_{i}')
        x.cmd(f'iperf3 -s -p 600{i} -1 -i 1 -J > iperf_result_2_x{i}.json &')
        c.cmd(f'iperf3 -c {x.IP()} -p 600{i} -J -t 10 -C bbr -i 0.1 > iperf_result_2_c{i}.json &')


def run(num_pairs=1, delay1='10ms', delay2='10ms'):
    "Test double dumbbell network with multiple routers"
    topo = DoubleDumbbellTopo(num_pairs=num_pairs, delay1=delay1, delay2=delay2)
    net = Mininet(topo=topo, waitConnected=True, link=TCLink)   
    net.start()
    os.system('sudo rm -f iperf_result_*')
    configure_routing(net, num_pairs)

    # Schedule reroute_traffic to run after 3 seconds using Timer
    reroute_timer = Timer(3, reroute_traffic, [net, num_pairs])
    end_timer = Timer(11, kill_iperf3)
    end_timer.start()   
    reroute_timer.start()

    # # Run iperf test between client-server pairs
    run_iperf_test(net, num_pairs)

    # # Wait for the reroute_timer to finish
    reroute_timer.join()
    end_timer.join()
    # Start CLI for manual inspection if needed
    #CLI(net)
    #net.pingAll()
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    os.system('sudo bash set*')
    if len(sys.argv) < 3:
        print("Usage: sudo python3 script_name.py <num_pairs> <delay>")
        sys.exit(1)

    num_pairs = int(sys.argv[1])
    delay1 = sys.argv[2]  # Delay for the first dumbbell, e.g., '20ms'
    delay2 = sys.argv[2]   # Delay for the second dumbbell, e.g., '30ms'
    try:
        run(num_pairs=num_pairs, delay1=delay1, delay2=delay2)
    except KeyboardInterrupt:
        os.system('sudo mn -c')
    os.system(f'sudo python3 plot.py {num_pairs}')