from mininet.topo import Topo
from mininet.node import OVSKernelSwitch, Host, Node
from mininet.net import Mininet
from core.utils import *
import random

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

# The simplest possible setup for testing MPTCP. A source/destination pair with 2 independent paths between them.
# This might just be a double dumbell. But this is simpler and uses switches I know work with MPTCP. I can advance to double dumbell later.
class MinimalMP(Topo):
    def build(self, n=3):
        self.n = n

        s1a = self.addSwitch('s1a', cls=OVSKernelSwitch)
        s1b = self.addSwitch('s1b', cls=OVSKernelSwitch)
        s1c = self.addSwitch('s1c', cls=OVSKernelSwitch)

        self.addLink('s1a', 's1b')
        self.addLink('s1b', 's1c')

        s2a = self.addSwitch('s2a', cls=OVSKernelSwitch)
        s2b = self.addSwitch('s2b', cls=OVSKernelSwitch)
        s2c = self.addSwitch('s2c', cls=OVSKernelSwitch)

        self.addLink('s2a', 's2b')
        self.addLink('s2b', 's2c')

        c1 = self.addHost('c1', cls=Host)
        self.addLink('c1', 's1a')
        self.addLink('c1', 's2a')

        x1 = self.addHost('x1', cls=Host)
        self.addLink('x1', 's1c')
        self.addLink('x1', 's2c')

    def __str__(self):
        return "MinimalMP(n=%d)" % self.n


# basic topology with multiple independent paths from client to server
class MultiTopo(Topo):
    def build(self, n=3):
        self.n = n
        c1 = self.addHost('c1', cls=Host)
        x1 = self.addHost('x1', cls=Host)


        pathLen = 3
        last_switch = None
        for path in range(1, n+1): # for every path (n)
            for sw in range(1, pathLen+1): # for every switch (per path, pathLen=3)
                curr_switch = None
                if sw ==1:
                    # START SWITCH
                    curr_switch = self.addSwitch('s' + str(path) + "." + str(sw), cls=OVSKernelSwitch)
                    self.addLink(c1, curr_switch)
                elif sw < pathLen:
                    # MIDDLE SWITCH
                    curr_switch = self.addSwitch('s' + str(path) + "." + str(sw), cls=OVSKernelSwitch)
                    self.addLink(curr_switch, last_switch)
                else:
                    # END SWITCH
                    curr_switch = self.addSwitch('s' + str(path) + "." + str(sw), cls=OVSKernelSwitch)
                    self.addLink(x1, curr_switch)
                    self.addLink(curr_switch, last_switch)
                last_switch = curr_switch
    def __str__(self):
        return "MultiTopo(n=%d)" % self.n

# Topology with n independent paths from c1 to x1
# c2 and x2 are connected over a single one of these paths, intended as a competing flow
class MultiCompetitionTopo(Topo):
    def build(self, n=3):
        self.n = n
        # Main client/server pair
        c1 = self.addHost('c1', cls=Host)
        x1 = self.addHost('x1', cls=Host)

        # Competing client/server pair to generate traffic for
        c2 = self.addHost('c2', cls=Host)
        x2 = self.addHost('x2', cls=Host)

        pathLen = 3
        last_switch = None
        for path in range(1, n+1): # for every path (n)
            for sw in range(1, pathLen+1): # for every switch (per path, pathLen=3)
                curr_switch = None
                if sw ==1:
                    # START SWITCH
                    curr_switch = self.addSwitch('s' + str(path) + "." + str(sw), cls=OVSKernelSwitch)
                    self.addLink(c1, curr_switch)
                    if path == 1: 
                        self.addLink(c2, curr_switch) 
                elif sw < pathLen:
                    # MIDDLE SWITCH
                    curr_switch = self.addSwitch('s' + str(path) + "." + str(sw), cls=OVSKernelSwitch)
                    self.addLink(last_switch, curr_switch)
                else:
                    # END SWITCH
                    curr_switch = self.addSwitch('s' + str(path) + "." + str(sw), cls=OVSKernelSwitch)
                    self.addLink(curr_switch, x1)
                    self.addLink(last_switch, curr_switch)
                    if path == 1: 
                        self.addLink(curr_switch, x2) 
                last_switch = curr_switch
    def __str__(self):
        return "MultiCompetitionTopo(n=%d)" % self.n

# A basic MPTCP ndiffports fairness test
# Creates a shared bottleneck router with ECMP, which will independently route subflows across both paths if configured correctly
# An optional competing client/server pair shares a bottleneck with the main connection at router r2a
class NdiffportsTest(Topo):
    def build(self, n=3):
        self.n = n

        # MAIN --------------------------------------------------------
        # Main MPTCP Connection
        c1 = self.addHost('c1', cls=Host)
        x1 = self.addHost('x1', cls=Host)

        # Bottleneck router with ECMP
        r1 = self.addHost('r1', cls=LinuxRouter) # This may be incorrect. Does this have ECMP?
    
        # Router pair (alternate paths)
        r2a = self.addHost('r2a', cls=LinuxRouter)
        r2b = self.addHost('r2b', cls=LinuxRouter)

        # Server connection switch
        r3 = self.addHost('r3', cls=LinuxRouter)

        # Switch connections
        self.addLink(r1, r2a)
        self.addLink(r1, r2b)
        self.addLink(r2a, r3)
        self.addLink(r2b, r3)

        # Main connection links
        self.addLink(c1, r1)
        self.addLink(r3, x1)

        # COMPETING ----------------------------------------------
        
        # Hosts
        c2 = self.addHost('c2', cls=Host)
        x2 = self.addHost('x2', cls=Host)

        # Buffer routers
        r4 = self.addHost('r4', cls=LinuxRouter)
        r5 = self.addHost('r5', cls=LinuxRouter)

        # Competing Flow Links (this links are going to contain some wonky routing tables, but it shouldn't matter as long as c1/x2 and c2/x2 don't try to communicate, which is currently impossible anyway)
        self.addLink(c2, r4)
        self.addLink(r4, r2a)
        self.addLink(r2a, r5)
        self.addLink(r5, x2)

    def __str__(self):
        return "NdiffportsTest(n=%d)" % self.n


# Similar to multicompetitionTopo but designed for ndiffports and ECMP
# Generates n paths interconnected with their direct neighbours
# The "highest" path (n) will have access to a single path between its client/server pair, all other paths will have 2
class Ndiffports2(Topo):
    def build(self, n=2):
        self.n = n

        # Intra-path nodes and links
        for path in range(1, n+1):
            # Path nodes
            self.addHost(f'c{path}', cls=Host)
            self.addHost(f'r{path}q', cls=LinuxRouter)
            self.addHost(f'r{path}a', cls=LinuxRouter)
            self.addHost(f'r{path}b', cls=LinuxRouter)
            self.addHost(f'r{path}c', cls=LinuxRouter)
            self.addHost(f'r{path}d', cls=LinuxRouter)
            self.addHost(f'x{path}', cls=Host)

            # Path links
            self.addLink(f'c{path}', f'r{path}q')
            self.addLink(f'r{path}q', f'r{path}a')
            self.addLink(f'r{path}a', f'r{path}b')
            self.addLink(f'r{path}b', f'r{path}c')
            self.addLink(f'r{path}c', f'r{path}d')
            self.addLink(f'r{path}d', f'x{path}')

        # Inter-path links
        for path in range(1, n):
            self.addLink(f'r{path}a', f'r{path+1}b')
            self.addLink(f'r{path+1}c', f'r{path}d')

# A perfect grid of routers interconnected with their adjacent neighbours. Intended to (roughly) mimic an LEO satellite network mesh
# A router name alone should be enough to describe its relative position in the topology
# Routing has to be done manually!
class ManhattanTopo(Topo):

    host_coords = []

    def build(self, n=2, mesh_size=10):
        self.n = n # Number of random host-pairs (client c and server x)
        self.mesh_size = mesh_size # Number of rows/columns (square)

        satellites = []
        # Routers
        for y in range(1, mesh_size+1):
            for x in range(1, mesh_size+1):
                r = self.addHost(f'r{x}_{y}', cls=LinuxRouter)
                satellites.append(r)
        
        # client-server pairs. User terminals are connected to satellites via their eth-0's
        for h in range(1, n+1):
            for name in ['c', 'x']:
                x, y = self.get_unique_position()

                host = self.addHost(f'{name}{h}', cls=Host) # Client or server
                sw = self.addHost(f'r_{host}', cls=LinuxRouter)  # "Home" switch, used to police delay
                ut = self.addHost(f'UT_{host}', cls=LinuxRouter) # User terminal router, connects to the mesh

                self.addLink(host, sw) # Host to switch
                self.addLink(sw, ut) # Switch to user terminal
                for router in satellites:   
                    self.addLink(ut, router) # UT to all satellites. Default gateway should change based on experiment parameters.

        # Router Links ^>
        for y in range(1, mesh_size+1):
            for x in range(1, mesh_size+1):
                if x != mesh_size:
                    self.addLink(f'r{x}_{y}', f'r{x+1}_{y}') # East
                if y != mesh_size:
                    self.addLink(f'r{x}_{y}', f'r{x}_{y+1}') # North
        
    def get_unique_position(self):
        #random.seed(24601) # Will this seed make each integer the same?
        while True:
            pos = (random.randint(1, self.mesh_size), random.randint(1, self.mesh_size))
            if pos not in self.host_coords:
                self.host_coords.append(pos)
                break
        return pos

# A simple two-path topology with OVSKernelSwitches. Alternate paths to be switched between with custom controller code
# Remember - loops will make the default learning switch fail. You will need a custom controller for this to topology to function.
class OpenFlowTest(Topo):
    # Returns a unique DPID. Intended to override the default dpid generation based on name (s1a = 1, and s1b = 1. Collisions are bad.)
    def get_dpid(self):
        self.curr_dpid += 1
        return "%016x" % self.curr_dpid  # Return zero-padded hex string for DPID
    
    def build(self, n=3):
        self.n = n
        self.curr_dpid = 0

        # Hosts/switches
        c1 = self.addHost('c1', cls=Host)
        s_c1 = self.addSwitch('s_c1', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid())
        s1a = self.addSwitch('s1a', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid())
        for i in range(1, n+1):
            alt_switch = self.addSwitch(f's{i}b', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid())
        s1c = self.addSwitch('s1c', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid())
        s_x1 = self.addSwitch('s_x1', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid())
        x1 = self.addHost('x1', cls=Host)

        # Links
        self.addLink('c1', 's_c1')
        self.addLink('s_c1', 's1a')
        for i in range(1, n+1):
            self.addLink('s1a', f's{i}b')
            self.addLink(f's{i}b', 's1c')
        self.addLink('s1c', 's_x1')
        self.addLink('s_x1', 'x1')

    def __str__(self):
        return "OpenFlowTest(n=%d)" % self.n

# A perfect grid of routers interconnected with their adjacent neighbours. Intended to (roughly) mimic an LEO satellite network mesh
# Created with switches - routing must be done through a custom openflow controller (one that can handle loops - basic learning switches won't do)
# Routing has to be done manually!
class ManhattanOpenflow(Topo):
    # Returns a unique DPID. Intended to override the default dpid generation based on name (s1a = 1, and s1b = 1. Collisions are bad.)
    def get_dpid_from_pos(self, x: int, y: int) -> str:
        printGreen(x)
        printGreen(y)
        printGreen(f"{0:011x}{x:02d}0{y:02d}")
        return f"{0:011x}{x:02d}0{y:02d}"

    def get_dpid(self, type="none"):
        if type == "sat":
            self.curr_sat_dpid += 1
            return "%016x" % self.curr_sat_dpid
        elif type == "ground":
            self.curr_ground_dpid += 1
            return "%016x" % self.curr_ground_dpid
        else:
            printRed("ERROR: DPID type must be specified")
            return None
            

    def build(self, n=2, mesh_size=10):
        self.n = n # Number of random host-pairs (client c and server x)
        self.mesh_size = mesh_size # Number of rows/columns (square)
        self.curr_sat_dpid = 0 
        self.curr_ground_dpid = 10000 # Start at 100k, allow anything <100k for mesh switches
        self.host_coords = []
        self.satellites = []

        # Routers
        for y in range(1, mesh_size+1):
            for x in range(1, mesh_size+1):
                s = self.addSwitch(f's{x}_{y}', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid(type='sat'))
                self.satellites.append(s)
        
        # client-server pairs. User terminals are connected to satellites via their eth-0's
        for h in range(1, n+1):
            for name in ['c', 'x']:
                x, y = self.get_unique_position()

                host = self.addHost(f'{name}{h}', cls=Host) # Client or server
                sw = self.addSwitch(f's_{host}', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid(type='ground')) # give non-mesh switches unique DPIDs for easy identification
                ut = self.addSwitch(f'UT_{host}', cls=OVSKernelSwitch, protocols='OpenFlow13', dpid=self.get_dpid(type='ground'))

                self.addLink(host, sw) # Host to switch
                self.addLink(sw, ut) # Switch to user terminal
                #self.addLink(ut, f's{x}_{y}') # UT to some random satellie. Maybe delete this and create/break UT links via the experiment or animation.

        # Switch Links ^>
        for y in range(1, mesh_size+1):
            for x in range(1, mesh_size+1):
                if x != mesh_size:
                    self.addLink(f's{x}_{y}', f's{x+1}_{y}') # East
                if y != mesh_size:
                    self.addLink(f's{x}_{y}', f's{x}_{y+1}') # North
        
    def get_unique_position(self):
        #random.seed(24601) # Will this seed make each integer the same?
        while True:
            pos = (random.randint(1, self.mesh_size), random.randint(1, self.mesh_size))
            if pos not in self.host_coords:
                self.host_coords.append(pos)
                break
        return pos

topos = { 'dumbell': DumbellTopo,
          'double_dumbell': DoubleDumbbellTopo,
          'parking_lot': ParkingLot,
          'multi_topo': MultiTopo,
          "multi_competition_topo" : MultiCompetitionTopo,
          "minimal_mp" : MinimalMP,
          "ndiffports_test" : NdiffportsTest,
          "ndiffports2" : Ndiffports2,
          "manhattan" : ManhattanTopo,
          'openflowtest' : OpenFlowTest,
            "manhattan_openflow" : ManhattanOpenflow,
        }
