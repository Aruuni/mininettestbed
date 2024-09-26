#!/usr/bin/env python

import sys
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink
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

    def build(self, num_pairs=1, delay1='10ms', delay2='10ms'):
        # First Dumbbell Topology
        r1a = self.addNode('r1a', cls=LinuxRouter)
        r2a = self.addNode('r2a', cls=LinuxRouter)
        r3a = self.addNode('r3a', cls=LinuxRouter)

        for i in range(1, num_pairs + 1):
            c = self.addHost(f'c1_{i}', ip=f'192.168.{i}.100/24', defaultRoute=f'via 192.168.{i}.1')
            x = self.addHost(f'x1_{i}', ip=f'192.168.{i+num_pairs}.100/24', defaultRoute=f'via 192.168.{i+num_pairs}.1')

            # Links between hosts and routers
            self.addLink(c, r1a, intfName2=f'r1a-eth{i+1}')
            self.addLink(r3a, x, intfName1=f'r3a-eth{i+1}')

        # Links between routers with netem delay and tbf bandwidth limitation
        self.addLink(r1a, r2a, intfName1='r1a-eth0', intfName2='r2a-eth0', cls=TCLink, delay=delay1)
        self.addLink(r2a, r3a, intfName1='r2a-eth1', intfName2='r3a-eth0', cls=TCLink, bw=100)

        # Second Dumbbell Topology
        r1b = self.addNode('r1b', cls=LinuxRouter)
        r2b = self.addNode('r2b', cls=LinuxRouter)
        r3b = self.addNode('r3b', cls=LinuxRouter)

        for i in range(1, num_pairs + 1):
            c2 = self.addHost(f'c2_{i}', ip=f'192.168.{i+2*num_pairs}.100/24', defaultRoute=f'via 192.168.{i+2*num_pairs}.1')
            x2 = self.addHost(f'x2_{i}', ip=f'192.168.{i+3*num_pairs}.100/24', defaultRoute=f'via 192.168.{i+3*num_pairs}.1')

            # Links between hosts and routers
            self.addLink(c2, r1b, intfName2=f'r1b-eth{i+1}')
            self.addLink(r3b, x2, intfName1=f'r3b-eth{i+1}')


        # Links between routers with netem delay and tbf bandwidth limitation
        self.addLink(r1b, r2b, intfName1='r1b-eth0', intfName2='r2b-eth0', cls=TCLink, delay=delay2)
        self.addLink(r2b, r3b, intfName1='r2b-eth1', intfName2='r3b-eth0', cls=TCLink, bw=100)

        # Additional links between the two dumbbells
        self.addLink(r1a, r1b, intfName1='r1a-eth10', intfName2='r1b-eth10')
        self.addLink(r3a, r3b, intfName1='r3a-eth10', intfName2='r3b-eth10')

def configure_routing(net, num_pairs):
    "Configure static routing on routers"
    r1a, r2a, r3a = net.get('r1a', 'r2a', 'r3a')
    r1b, r2b, r3b = net.get('r1b', 'r2b', 'r3b')

    # Configure routing for the first dumbbell
    r1a.setIP('10.0.1.1/24', intf='r1a-eth0')
    r2a.setIP('10.0.1.2/24', intf='r2a-eth0')
    r2a.setIP('10.0.2.1/24', intf='r2a-eth1')
    r3a.setIP('10.0.2.2/24', intf='r3a-eth0')

    for i in range(1, num_pairs + 1):
        r1a.setIP(f'192.168.{i}.1/24', intf=f'r1a-eth{i+1}')
        r3a.setIP(f'192.168.{i+num_pairs}.1/24', intf=f'r3a-eth{i+1}')

        x_subnet = f'192.168.{i+num_pairs}.0/24'
        c_subnet = f'192.168.{i}.0/24'

        r1a.cmd(f'ip route add {x_subnet} via 10.0.1.2')
        r3a.cmd(f'ip route add {c_subnet} via 10.0.2.1')

        r2a.cmd(f'ip route add {x_subnet} via 10.0.2.2')
        r2a.cmd(f'ip route add {c_subnet} via 10.0.1.1')




    # Configure routing for the second dumbbell
    r1b.setIP('10.0.3.1/24', intf='r1b-eth0')
    r2b.setIP('10.0.3.2/24', intf='r2b-eth0')
    r2b.setIP('10.0.4.1/24', intf='r2b-eth1')
    r3b.setIP('10.0.4.2/24', intf='r3b-eth0')

    for i in range(1, num_pairs + 1):
        r1b.setIP(f'192.168.{i+2*num_pairs}.1/24', intf=f'r1b-eth{i+1}')
        r3b.setIP(f'192.168.{i+3*num_pairs}.1/24', intf=f'r3b-eth{i+1}')

        x_subnet = f'192.168.{i+3*num_pairs}.0/24'
        c_subnet = f'192.168.{i+2*num_pairs}.0/24'

        r1b.cmd(f'ip route add {x_subnet} via 10.0.3.2')
        r3b.cmd(f'ip route add {c_subnet} via 10.0.4.1')

        r2b.cmd(f'ip route add {x_subnet} via 10.0.4.2')
        r2b.cmd(f'ip route add {c_subnet} via 10.0.3.1')

    # Configure the connections between r1a and r1b, and r3a and r3b
    r1a.setIP('10.0.5.1/24', intf='r1a-eth10')
    r1b.setIP('10.0.5.2/24', intf='r1b-eth10')

    r3a.setIP('10.0.6.1/24', intf='r3a-eth10')
    r3b.setIP('10.0.6.2/24', intf='r3b-eth10')

    # Inter-Dumbbell routing
    r1a.cmd('ip route add 192.168.2.0/24 via 10.0.5.2')
    r1b.cmd('ip route add 192.168.1.0/24 via 10.0.5.1')
    r3a.cmd('ip route add 192.168.4.0/24 via 10.0.6.2')
    r3b.cmd('ip route add 192.168.3.0/24 via 10.0.6.1')


def kill_iperf3():
    os.system('killall iperf3')

def reroute_traffic(net, num_pairs):
    info("Rerouting traffic through the first dumbbell for the second dumbbell\n")
    r1a, r2a, r3a = net.get('r1a', 'r2a', 'r3a')
    r1b, r2b, r3b = net.get('r1b', 'r2b', 'r3b')

    # Set up routing in r1b to route traffic through r1a to the rest of the network
    for i in range(1, num_pairs + 1):
        # Route traffic from c2_1 (192.168.3.x) through r1a -> r2a -> r3a -> r3b -> x2_1
        r1b.cmd(f'ip route add 192.168.{i+3*num_pairs}.0/24 via 10.0.5.1 dev r1b-eth10')
        r3b.cmd(f'ip route add 192.168.{i+2*num_pairs}.0/24 via 10.0.6.1')

        # Set up routing in r1a to handle traffic from r1b
        r1a.cmd(f'ip route add 192.168.{i+3*num_pairs}.0/24 via 10.0.1.2')
        r2a.cmd(f'ip route add 192.168.{i+3*num_pairs}.0/24 via 10.0.2.2')
        r3a.cmd(f'ip route add 192.168.{i+3*num_pairs}.0/24 via 10.0.6.2')

    # Disable the direct path in the second dumbbell to force the rerouting
    info("Disabling direct paths in the second dumbbell\n")
    r2b.cmd('ifconfig r2b-eth0 down')
    r2b.cmd('ifconfig r2b-eth1 down')

    info("Traffic rerouted successfully\n")



def run_iperf_test(net, num_pairs):
    "Run iperf test between client and server pairs"

    # Run iperf tests for the first dumbbell
    for i in range(1, num_pairs + 1):
        c = net.get(f'c1_{i}')
        x = net.get(f'x1_{i}')
        x.cmd(f'iperf3 -s -p 500{i} -i 1 -J > iperf_result_1_x{i}.json &')
        c.cmd(f'iperf3 -c {x.IP()} -p 500{i} -J -t 10 -C bbr -i 0.1 > iperf_result_1_c{i}.json &')

    # Run iperf tests for the second dumbbell
    for i in range(1, num_pairs + 1):
        c = net.get(f'c2_{i}')
        x = net.get(f'x2_{i}')
        x.cmd(f'iperf3 -s -p 600{i} -i 1 -J > iperf_result_2_x{i}.json &')
        c.cmd(f'iperf3 -c {x.IP()} -p 600{i} -J -t 10 -C bbr -i 0.1 > iperf_result_2_c{i}.json &')


def run(num_pairs=1, delay1='10ms', delay2='10ms'):
    "Test double dumbbell network with multiple routers"
    topo = DoubleDumbbellTopo(num_pairs=num_pairs, delay1=delay1, delay2=delay2)
    net = Mininet(topo=topo, waitConnected=True, link=TCLink)
    net.start()
    os.system('sudo rm -f iperf_result_*.json')
    configure_routing(net, num_pairs)

    # Schedule reroute_traffic to run after 3 seconds using Timer
    #reroute_timer = Timer(3, reroute_traffic, [net, num_pairs])
    end_timer = Timer(10, kill_iperf3)
    end_timer.start()   
    #reroute_timer.start()

    # # Run iperf test between client-server pairs
    run_iperf_test(net, num_pairs)

    # # Wait for the reroute_timer to finish
    #reroute_timer.join()
    end_timer.join()
    # Start CLI for manual inspection if needed
    #CLI(net)
    #net.pingAll()
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')

    if len(sys.argv) < 3:
        print("Usage: sudo python3 script_name.py <num_pairs> <delay1> <delay2>")
        sys.exit(1)

    num_pairs = int(sys.argv[1])
    delay1 = sys.argv[2]  # Delay for the first dumbbell, e.g., '20ms'
    delay2 = sys.argv[2]   # Delay for the second dumbbell, e.g., '30ms'
    try:
        run(num_pairs=num_pairs, delay1=delay1, delay2=delay2)
    except KeyboardInterrupt:
        os.system('sudo mn -c')
    os.system(f'sudo python3 plot.py {num_pairs}')