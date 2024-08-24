from mininet.topo import Topo
from mininet.node import OVSKernelSwitch, Host

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
    
class DoubleDumbellTopo(Topo):
    "Two dumbbell topologies with n pairs of client/servers interconnected by four switches."
    def build(self, n=2):
        # First Dumbbell Topology
        switch1a = self.addSwitch('s1a', cls=OVSKernelSwitch, failMode='standalone')
        switch2a = self.addSwitch('s2a', cls=OVSKernelSwitch, failMode='standalone')
        switch3a = self.addSwitch('s3a', cls=OVSKernelSwitch, failMode='standalone')

        self.addLink(switch1a, switch2a)
        self.addLink(switch2a, switch3a)

        # Second Dumbbell Topology
        switch1b = self.addSwitch('s1b', cls=OVSKernelSwitch, failMode='standalone')
        switch2b = self.addSwitch('s2b', cls=OVSKernelSwitch, failMode='standalone')
        switch3b = self.addSwitch('s3b', cls=OVSKernelSwitch, failMode='standalone')

        self.addLink(switch1b, switch2b)
        self.addLink(switch2b, switch3b)
        
         # Cross Traffic Links
        self.addLink(switch1a, switch1b)
        self.addLink(switch3a, switch3b)

        self.n = n


        # Clients and Servers for First Dumbbell Topology
        for h in range(n//2):
            client = self.addHost('c1%s' % (h + 1), cls=Host)
            self.addLink(client, switch1a)
        for h in range(n//2):
            server = self.addHost('x1%s' % (h + 1), cls=Host)
            self.addLink(server, switch3a)

        # Clients and Servers for Second Dumbbell Topology
        for h in range(n//2, n):
            client = self.addHost('c2%s' % (h + 1 - n//2), cls=Host)
            self.addLink(client, switch1b)
        for h in range(n//2, n):
            server = self.addHost('x2%s' % (h + 1 - n//2), cls=Host)
            self.addLink(server, switch3b)

    def __str__(self):
        return "DoubleDumbellTopo(n=%d)" % self.n


class ParkingLot(Topo):
    "Single bottleneck topology with n pairs of client/servers interconnected by two switches."
    def build(self):
        switch1 = self.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')
        switch2 = self.addSwitch('s2', cls=OVSKernelSwitch, failMode='standalone')
        switch3 = self.addSwitch('s3', cls=OVSKernelSwitch, failMode='standalone')
        switch4 = self.addSwitch('s4', cls=OVSKernelSwitch, failMode='standalone')
        switch5 = self.addSwitch('s5', cls=OVSKernelSwitch, failMode='standalone')

        self.addLink(switch1, switch2) #s1-eth1 is netem
        self.addLink(switch2, switch3) #s2-eth2 is first bottleneck (tbf)
        self.addLink(switch3, switch5) #s3-eth2 is second bottleneck (tbf)
        self.addLink(switch4, switch3) #s4-eth1 is netem

        client1 = self.addHost('c1', cls=Host)
        client2 = self.addHost('c2', cls=Host)
        client3 = self.addHost('c3', cls=Host)
        client4 = self.addHost('c4', cls=Host)
        client5 = self.addHost('c5', cls=Host)

        self.addLink(client1, switch1)
        self.addLink(client2, switch1)
        self.addLink(client3, switch4)
        self.addLink(client4, switch4)
        self.addLink(client5, switch4)


        server1 = self.addHost('x1', cls=Host)
        server2 = self.addHost('x2', cls=Host)
        server3 = self.addHost('x3', cls=Host)
        server4 = self.addHost('x4', cls=Host)
        server5 = self.addHost('x5', cls=Host)

        self.addLink(server1, switch3)
        self.addLink(server2, switch5)
        self.addLink(server3, switch5)
        self.addLink(server4, switch5)
        self.addLink(server5, switch5)

    def __str__(self):
        return "ParkingLot"


topos = { 'dumbell': DumbellTopo, 'double_dumbell': DoubleDumbellTopo }
