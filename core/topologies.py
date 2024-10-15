from mininet.topo import Topo
from mininet.node import OVSKernelSwitch, Host, Node

class DumbellTopo(Topo):
    "Single bottleneck topology with n pairs of client/servers interconnected by two switches."
    def build(self, n=2):
        switch1 = self.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')
        switch2 = self.addSwitch('s2', cls=OVSKernelSwitch, failMode='standalone')
        switch3 = self.addSwitch('s3', cls=OVSKernelSwitch, failMode='standalone')

        self.addLink(switch1, switch2)
        self.addLink(switch2, switch3)

        self.n = n

        for h in range(n):
            client = self.addHost('c%s' % (h + 1), cls=Host)
            self.addLink(client, switch1)
        for h in range(n):
            server = self.addHost('x%s' % (h + 1), cls=Host)
            self.addLink(server, switch3)

    def __str__(self):
        return "DumbellTopo(n=%d)" % self.n
    
class LinuxRouter(Node):
    "A Node with IP forwarding enabled."
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

class DoubleDumbbellTopo(Topo):
    "Two isolated dumbbell topologies with dynamic client-server pairs. Interconencted usign routers"
          

    def build(self, n=1):
        self.n = n
        # First Dumbbell Topology
        r1a = self.addNode('r1a', cls=LinuxRouter)
        r2a = self.addNode('r2a', cls=LinuxRouter)
        r3a = self.addNode('r3a', cls=LinuxRouter)

        # Second Dumbbell Topology
        r1b = self.addNode('r1b', cls=LinuxRouter)
        r2b = self.addNode('r2b', cls=LinuxRouter)
        r3b = self.addNode('r3b', cls=LinuxRouter)

        # Spine links
        self.addLink(r1a, r2a, intfName1='r1a-eth0', intfName2='r2a-eth0')
        self.addLink(r2a, r3a, intfName1='r2a-eth1', intfName2='r3a-eth0')

        self.addLink(r1b, r2b, intfName1='r1b-eth0', intfName2='r2b-eth0')
        self.addLink(r2b, r3b, intfName1='r2b-eth1', intfName2='r3b-eth0')

        self.addLink(r1a, r1b, intfName1='r1a-eth1', intfName2='r1b-eth1')
        self.addLink(r3a, r3b, intfName1='r3a-eth1', intfName2='r3b-eth1')


        for i in range(1, n + 1):
            c = self.addHost(f'c1_{i}', ip=f'192.168.{i}.100/24', defaultRoute=f'via 192.168.{i}.1')
            x = self.addHost(f'x1_{i}', ip=f'192.168.{i+n}.100/24', defaultRoute=f'via 192.168.{i+n}.1')
            
            c2 = self.addHost(f'c2_{i}', ip=f'192.168.{i+2*n}.100/24', defaultRoute=f'via 192.168.{i+2*n}.1')
            x2 = self.addHost(f'x2_{i}', ip=f'192.168.{i+3*n}.100/24', defaultRoute=f'via 192.168.{i+3*n}.1')

            # Links between hosts and routers
            self.addLink(c, r1a, intfName2=f'r1a-eth{i+1}')
            self.addLink(r3a, x, intfName1=f'r3a-eth{i+1}')

            # Links between hosts and routers
            self.addLink(c2, r1b, intfName2=f'r1b-eth{i+1}')
            self.addLink(r3b, x2, intfName1=f'r3b-eth{i+1}')

    def __str__(self):
        return "DoubleDumbellTopo(n=%d)" % self.n


class ParkingLot(Topo):
    """
    """
    def build(self, n=3):
        assert n >= 3, "Number of flows must be at least 3 for the parking lot topology. At one node there is no bw policing as the middle links dont exist, and at 2 is is effectively a dumbbell topology."
        switches = []
        
        for i in range(1,n+1,1):
            switches.append(self.addSwitch('s%s' % i, cls=OVSKernelSwitch, failMode='standalone'))
        clients = []
        for i in range(1,n+1,1):
            clients.append(self.addHost('c%s' % i, cls=Host))
        servers = []
        for i in range(1,n+1,1):
            servers.append(self.addHost('x%s' % i, cls=Host))
        self.n = n

        for i in range(1,n,1):
            self.addLink(switches[i-1], switches[i])    

        self.addLink(clients[0], switches[0])
        self.addLink(servers[0], switches[n-1])

        for i in range(1,n,1):
            self.addLink(clients[i], switches[i-1])
            self.addLink(servers[i], switches[i])

    def __str__(self):
        return "ParkingLotTopo(n=%d)" % self.n


topos = { 'dumbell': DumbellTopo, 'double_dumbell': DoubleDumbbellTopo, 'parking_lot': ParkingLot }
