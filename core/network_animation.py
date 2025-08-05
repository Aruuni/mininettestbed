from core.topologies import *
from core.analysis import *
from core.utils import *
from core.emulation import *
from core.config import *
from mininet.link import TCLink
from mininet.node import OVSKernelSwitch, Host, Node, Link, Intf
import math
import time
import threading
import numpy as np

# A class that virtually animates positions between nodes in a topology. 
# Behaviour is different per topology, but this will typically be used to update routing tables over time.
class TopoAnimator():
    # Not sure a parent class is even necessary, but all of these classes will certainly be similar
    pass

# This class defines how a Manhattan topology should be animated
# Absolute makes host positions absolute, rather than 0-1 spanning across the entire mesh area
class ManhattanTopoAnimator(TopoAnimator):
    def __init__(self, net, topo, direction=(-1, 0), speed=1, host_positions={}, relative=True):
        self.net: Mininet = net
        x = direction[0]
        y = direction[1]
        self.direction = np.asarray([x, y, 0.0], dtype=float) # Satellite movement vector
        self.speed = float(speed) # Constant to multiply movement vector by
        self.animated_nodes = [] # List of nodes that will move with each timestep
        self.user_terminals = [] # List of user terminals that directly connect to the satellite mesh
        self.hosts = [] # lists of hosts (clients and servers)
        self.topo: ManhattanTopo = topo # Instance of the Manhattan topo 
        self.last_update = -1 # Will hold the timestamp of the last animation update
        self.start_time = -1 # Will hold the timestamp of the animation start time (different from initialization!)
        self.initialize_animation(host_positions, relative)
        self.update_network_routing_tables() # Configure initial routing tables to prevent iperf from hanging

    
    # Creates a list of default positions (this is going to look very different depending on the topology)
    # host positions not defined by the caller will be configured automatically or throw an error
    def initialize_animation(self, host_positions, relative):
        satellite_height = 3500 # Estimated height in km
        node_name : Node
        for node_name in self.topo.hosts():
            # Configure router virtual positions
            if node_name.startswith('r') and not node_name.startswith('r_'):
                match = re.search(r'(\d+)\_(\d+)', node_name)
                pos = np.array([float(match.group(1)), float(match.group(2)), float(satellite_height)]) # x, y, altitude
                anim_node = AnimationNode(node_name, pos, moving=True)
                anim_node.SAT_POS = (int(match.group(1)), int(match.group(2))) # constant position within the satellite array
                self.animated_nodes.append(anim_node) # Assign this node to the animated list for easy access
                #printGreen(anim_node)

            # Configure client and server virtual positions
            elif node_name.startswith('c') or node_name.startswith('x'):
                if node_name not in host_positions:
                    printRed(f"ERROR: host {node_name} was not given a position!")
                else:
                    pos = np.asarray(host_positions.get(node_name))
                    if relative:
                        pos *= self.topo.mesh_size
                        #print(f'{node_name} pos: {pos}')
                    host = AnimationNode(node_name, pos, moving=False)
                    host.overhead = ''
                    sw = AnimationNode(f'r_{node_name}', pos, moving=False)
                    user_terminal = AnimationNode(f'UT_{node_name}', pos, moving=False)
                    # printGreen(host)
                    # printGreen(sw)
                    # printGreen(user_terminal)
                    self.hosts.append(host)
                    self.user_terminals.append(user_terminal)

    # Updates the animation state based on the amount of time elapsed (only updates positions, not routing tables!)
    def update_animation(self):
        if self.start_time == -1:
            printRed("ERROR: animation must be started before updates can be requested!")
            return -1
        call_time = time.time() # Update time of function call
        time_elapsed = call_time - self.last_update # Seconds elapsed since last update

        # Move every satellite the specified direction and speed based on the time elapsed since last update
        for node in self.animated_nodes:
            movement = self.direction * self.speed * time_elapsed
            node.pos += movement

        self.last_update = call_time # Update the last update timestamp
        return time.time() - call_time # Return function run time in seconds

    # Updates network routing tables based on the current state of the animation
    def update_network_routing_tables(self):
        for host in self.hosts:
            old_overhead = host.overhead
            host.overhead = self.find_closest_satellite(host)
            if old_overhead != host.overhead:
                printTC(f'Handover occuring for {host.name}')
                add_default_gateway(self.net, f'UT_{host.name}', [f'{host.overhead.name}'], debug=True)
                # printPink(f'{host} overhead: {host.overhead}')
                for sat in self.animated_nodes:
                    next_hops = []
                    if sat is host.overhead:
                        # Route directly through UT if you are the current overhead satellite
                        next_hops.append(f'UT_{host.name}') 
                    else:
                        # Route through the left/right satellite
                        if sat.SAT_POS[0] < host.overhead.SAT_POS[0]:
                            next_hops.append(f'r{sat.SAT_POS[0] + 1}_{sat.SAT_POS[1]}')
                        elif sat.SAT_POS[0] > host.overhead.SAT_POS[0]:
                            next_hops.append(f'r{sat.SAT_POS[0] - 1}_{sat.SAT_POS[1]}')

                        # Route through the above/below satellite
                        if sat.SAT_POS[1] < host.overhead.SAT_POS[1]:
                            next_hops.append(f'r{sat.SAT_POS[0]}_{sat.SAT_POS[1] + 1}')
                        elif sat.SAT_POS[1] > host.overhead.SAT_POS[1]:
                            next_hops.append(f'r{sat.SAT_POS[0]}_{sat.SAT_POS[1] - 1}')
                    
                    add_route(self.net, sat.name, next_hops, self.net.get(host.name).IP(), directional=False, debug=False)

    
    
    # Update the animation state and routing tables at a regular interval for the specified duration
    def run(self, duration, interval): 
        if self.start_time != -1:
            printRed("ERROR: animation has already been started!")
            return
        
        def animate_for_duration(duration, interval=1):
            while time.time() - self.start_time < duration:
                printGreen("Animation updating...")
                #print("...", end='\r')
                self.update_animation() # update animation state
                self.update_network_routing_tables() # update routing tables based on animation state
                time.sleep(interval)

        printGreen("Starting animation... ")
        self.start_time = time.time()
        self.last_update = self.start_time

        animate_for_duration(duration, interval=interval)

        printGreen("Animation complete!")

    # Finds the closest satellite to the given host (one squared distance check per satellite, could slow down as experiments get larger)
    def find_closest_satellite(self, host):
        # if host.overhead:
        #     pass
        #     #TODO: fast version, only check adjacent satellites
        # else:
        curr_overhead = min(
            self.animated_nodes,
            key=lambda sat: sum((a - b) ** 2 for a, b in zip(host.pos, sat.pos)), # Squared distance is faster to calculate than euclidian distance
            default=None
        )
        return curr_overhead

class AnimationNode():
    def __init__(self, name, pos, moving=True):
        self.moving = moving
        self.pos = pos
        self.name = name

    def __str__(self):
        np.set_printoptions(suppress=True, formatter={'float': '{: 0.2f}'.format})
        return(f'{self.name}: {self.pos}')
