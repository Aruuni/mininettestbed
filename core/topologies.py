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
    def build(self, n=3):
        # First Dumbbell Topology
        assert n >= 3, "Number of flows must be at least 3 for the parking lot topology, otherwise it is effectively a dumbbell topology."
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
    """
    """
    def build(self, n=3):
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

        self.addLink(clients[0], switches[0])
        self.addLink(servers[0], switches[n-1])

        for i in range(1,n,1):
            print(f"({clients[i]} to {switches[i-1]})") 
            print(f"({servers[i]} to {switches[i]})")
            self.addLink(clients[i], switches[i-1])
            self.addLink(servers[i], switches[i])

        for i in range(1,n,1):
            self.addLink(switches[i-1], switches[i])    

    def __str__(self):
        return "ParkingLotTopo(n=%d)" % self.n


topos = { 'dumbell': DumbellTopo, 'double_dumbell': DoubleDumbellTopo }
