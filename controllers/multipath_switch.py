from ryu.base import app_manager
from ryu.controller.controller import Datapath # why
from ryu.controller import ofp_event
from ryu.controller.handler import HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER # in order: during handshake, during config (features requests), any time after initialization, once connection determined dead
from ryu.controller.handler import set_ev_cls
from ryu.controller.ofp_event import EventOFPMsgBase
from ryu.topology import event # Topology change events
from ryu.topology.event import EventSwitchEnter, EventSwitchLeave, EventLinkAdd, EventLinkDelete
from ryu.topology import switches
from ryu.topology.switches import Link
from ryu.topology.api import get_switch, get_link 
from ryu.ofproto import ofproto_v1_3, ofproto_v1_3_parser, ether, inet
from ryu.ofproto.ofproto_v1_3_parser import OFPPacketIn, OFPAction, OFPActionOutput, OFPInstructionActions, OFPFlowMod, OFPMatch
from ryu.lib.packet import packet
from ryu.lib.packet.packet import Packet # again, why
from ryu.lib.packet import ipv4, ethernet, arp, tcp
import networkx as nx
from networkx import DiGraph, Graph
import matplotlib.pyplot as plt # used for displaying the graph in debug
from matplotlib.backends.backend_pdf import PdfPages
import signal
import os
import sys
from path_selectors import get_paths
from path_selectors import PATH_SELECTORS # dict of str:function mappings, represents all available path selector functions
import math

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../')
sys.path.append( mymodule_dir )

"""
Builds a graph representation of the network and uses it to assign multiple paths between hosts
Subflows are assigned unique paths (if available) based on dst ports
Several path acquisition schemes are available (k-shortest, k-shortest-disjoint, k-shortest-pseduo-disjoint, k-equal-cost)
"""
class MultipathSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MultipathSwitch, self).__init__(*args, **kwargs)
        """
        Initializes important constants, objects, and signals.
        Priority levels and table IDs are stored as constants for convenience and more readable code.
        Network topology is stored across several graphs, each used for different purposes
        """
        self.PRIORITY_DEFAULT = 0
        self.PRIORITY_LOW = 5
        self.PRIORITY_HIGH = 10

        self.DEFAULT_TABLE = 0 # ID of the defalt rule table in each switch
        self.TCP_TABLE = 1 # ID of the TCP rule table in each switch

        self.DEBUG = True if "True" in os.getenv("DEBUG_PRINTS") else False
        self.OUTPUT_PATH = os.getenv("OUTPUT_PATH")
        self.PATH_SELECTOR_PRESET:str = os.getenv("PATH_SELECTOR_PRESET")

        # Create ip-hostname dict for better graph output and prints
        self.HOST_IPS = os.getenv("HOST_IPS")
        self.ip_to_host = {}
        for mapping in self.HOST_IPS.split(' '):
            ip, host = mapping.split(':')
            self.ip_to_host[ip] = host
        # Custom path selector parameters from experiment (deprecated)
        self.NUM_PATHS = int(os.getenv("NUM_PATHS")) # Max num of paths to generate per connection (anything over 8 is overkill. No limit will slow the controller to halt in large topologies.)
        # self.PATH_SELECTOR_NAME = os.getenv("PATH_SELECTOR") # which path selector to use
        # self.PATH_PENALTY = float(os.getenv("PATH_PENALTY")) # What penalty multipier to apply to used paths
        # # try to grab the function with name PATH_SELECTOR_NAME from path_selectors.py
        # try:
        #     self.PATH_SELECTOR:function = PATH_SELECTORS[self.PATH_SELECTOR_NAME] 
        # except KeyError:
        #     raise ValueError(f"Invalid path selector: {self.PATH_SELECTOR_NAME}")
        
        self.switches = []
        self.links = []
        self.graph: DiGraph = nx.DiGraph() # graph of the entire network, including hosts
        self.mesh_graph: Graph = nx.Graph() # Graph only of the mesh itself
        self.complete_graph:DiGraph = nx.DiGraph() # Complete graph of network. Link/switch removals don't apply to this. Only use for plotting.
        #self.switch_mst: DiGraph = nx.DiGraph() # minimum spanning tree of the switch graph, used for flooding and host discovery
        self.ip_to_port: dict[str, dict[str, dict[int]]] = {} # dpids[ips[in_ports]]
        self.paths: dict[str, dict[str, dict[tuple : list[int]]]] = {} # src[dst[path[subflows_on_path]]], for every src-dst pair there exists a dict of path tuples, and for every path tuple there exists a list of subflows (dst_ports) on it
        self.hosts = {}
        self.clients = []
        self.servers = []
        
        signal.signal(signal.SIGTERM, self._handle_sigterm) # call _handle_sigterm when the process is signalled to terminate
        signal.signal(signal.SIGINT, self._handle_sigterm) # call _handle_sigint when the process is signalled to interrupt (ctrl+c, end early)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev: EventOFPMsgBase):
        """
        Called when the switch first connects.
        Installs a high-priority flow entry to direct TCP packets to a secondary flow table.
        Installs a default (table-miss) flow entry to each table to send unknown packets to the controller.
        """
        datapath: Datapath = ev.msg.datapath
        parser: ofproto_v1_3_parser = datapath.ofproto_parser
        ofproto: ofproto_v1_3 = datapath.ofproto

        # default table-miss flow entry
        match: OFPMatch = parser.OFPMatch() # Wildcard, match all packets
        actions: list[OFPActionOutput] = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)] # Action: send to controller
        inst: list[OFPInstructionActions] = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # Instruction: install the action as a rule
        mod: OFPFlowMod = parser.OFPFlowMod(datapath=datapath, table_id=self.DEFAULT_TABLE, match=match, instructions=inst, priority=self.PRIORITY_DEFAULT) # Build the FlowMod Message
        datapath.send_msg(mod) # send FlowMod to the switch
        mod: OFPFlowMod = parser.OFPFlowMod(datapath=datapath, table_id=self.TCP_TABLE, match=match, instructions=inst, priority=self.PRIORITY_DEFAULT) # Build the FlowMod Message
        datapath.send_msg(mod) # send FlowMod to the switch

        # High-priority redirection from default table to TCP table
        match:OFPMatch = parser.OFPMatch(eth_type=0x0800, ip_proto=inet.IPPROTO_TCP) # Match all IP/TCP packets
        inst = [parser.OFPInstructionGotoTable(self.TCP_TABLE)] # Instruction: send packet to TCP table. Pipeline-related functionality doesn't require action objects
        mod: OFPFlowMod = parser.OFPFlowMod(datapath=datapath, table_id=self.DEFAULT_TABLE, match=match, instructions=inst, priority=self.PRIORITY_HIGH) # Build the FlowMod Message
        datapath.send_msg(mod) # send FlowMod to the switch

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev: EventOFPMsgBase):
        """
        Handles packets sent to controller via Dijkstra's shortest path
        Applies rules all along path before sending the packet through
        """
        msg:OFPPacketIn = ev.msg
        datapath:Datapath = msg.datapath
        parser:ofproto_v1_3_parser = datapath.ofproto_parser
        ofproto:ofproto_v1_3 = datapath.ofproto
        dpid:int = datapath.id
        pkt:Packet = packet.Packet(msg.data)
        in_port:int = msg.match['in_port']

        #printRed("found ANY packet")
        ip_headers:ipv4 = pkt.get_protocol(ipv4.ipv4)
        if ip_headers is None:
            return
        #printRed("found an IP packet")
        #printYellow(ip_headers)
        dst_ip:str = ip_headers.dst
        src_ip:str = ip_headers.src

        # learn the in_port of this IP at this datapath (currently not in use)
        self.ip_to_port.setdefault(dpid, {}).setdefault(dst_ip, []).append(in_port)

        # Learn the location of this host in the topology (if first sighting)
        if src_ip not in self.hosts:
            if self.DEBUG: 
                printYellow(f"Controller found host {src_ip}")
            self.hosts[src_ip] = dst_ip
            self.graph.add_node(src_ip)
            self.graph.add_edge(src_ip, dpid, src_port=0000, dst_port=in_port, weight=1)
            self.graph.add_edge(dpid, src_ip, src_port=in_port, dst_port=0000, weight=1)
            # self.output_graph() # only use for debug, causes issues if called frequently

        # ASSERT: dst exists, but a path has not been generated of this datapath
        # (split here)
        # Flood the MST for information if the dst has not yet been discovered
        
        # Flood if the dst has not yet been discovered
        if dst_ip not in self.hosts:
            if src_ip not in self.clients:
                self.clients.append(src_ip) # Trying to send to undiscovered host, this must be the initiating client
            if dst_ip not in self.servers:
                self.servers.append(dst_ip) # Trying to reach this server
            # printGreen(f"FOUND CLIENT {src_ip}")
            # printGreen(f"FOUND SERVER {dst_ip}")
            if self.DEBUG: printYellow(f'{dst_ip} not yet learned, flooding from {datapath.id}')
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(datapath=datapath,
                                    buffer_id=msg.buffer_id,
                                    in_port=in_port,
                                    actions=actions,
                                    data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None)
            datapath.send_msg(out)
            return

        if ip_headers.proto == inet.IPPROTO_TCP:
            self.handle_tcp_packets(ev)
        else:
            self.handle_default_packets(ev)

    def handle_default_packets(self, ev: EventOFPMsgBase):
        """
        Responsible for handling any packets that are not TCP (or any other protocols later specified)
        Usually handles these packets by quickly creating a shortest path to dst and following it
        Packets flood if dst has not been learned (causes broadcast storm if dst cannot be found. Be careful.)
        """

        msg:OFPPacketIn = ev.msg
        datapath:Datapath = msg.datapath
        parser:ofproto_v1_3_parser = datapath.ofproto_parser
        ofproto:ofproto_v1_3 = datapath.ofproto
        pkt:Packet = packet.Packet(msg.data)
        ip_headers:ipv4 = pkt.get_protocol(ipv4.ipv4)
        dst_ip:str = ip_headers.dst
        src_ip:str = ip_headers.src
        
        # Generate a shortest path from this datapath to dst
        shortest_path:tuple = (src_ip,) + tuple(nx.shortest_path(self.graph, datapath.id, dst_ip))
        forward_match:OFPMatch = parser.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip) # any IP packets headed to dst, regardless of port
        backward_match:OFPMatch = parser.OFPMatch(eth_type=0x0800, ipv4_dst=src_ip) # any IP packets headed to dst, regardless of port
        self.apply_rules_along_path(shortest_path, forward_match, backward_match, self.PRIORITY_LOW, parser, ofproto, self.DEFAULT_TABLE) # apply low-priority rule

        # Drop the packet (ideally should forward, figure it out later)

    def handle_tcp_packets(self, ev: EventOFPMsgBase):
        """
        Responsible for handling TCP packets
        Computes k-shortest paths from src to dst (if necessary) and assigns one of these paths to each src_port
        Packets are dropped if dst does not yet exist, as flooding TCP packets will trigger too many path creations and broadcast storms
        """

        msg:OFPPacketIn = ev.msg
        datapath:Datapath = msg.datapath
        parser:ofproto_v1_3_parser = datapath.ofproto_parser
        ofproto:ofproto_v1_3 = datapath.ofproto
        pkt:Packet = packet.Packet(msg.data)
        ip_headers:ipv4 = pkt.get_protocol(ipv4.ipv4)
        dst_ip:str = ip_headers.dst
        src_ip:str = ip_headers.src
        tcp_headers:tcp = pkt.get_protocol(tcp.tcp)
        src_port:int = tcp_headers.src_port
        dst_port:int = tcp_headers.dst_port

        # Drop if packets from this dst port have already been assigned a path
        self.paths.setdefault(src_ip, {}).setdefault(dst_ip, {})
        self.paths.setdefault(dst_ip, {}).setdefault(src_ip, {})
        #printYellow(f"found a TCP packet - {src_ip}:{src_port} headed to {dst_ip}:{dst_port}")
        paths_dict = self.paths[src_ip][dst_ip]

        # Drop this packet if its parent subflow should already be on a path (sender or receiever. Needs two checks.)
        if any(dst_port in path for path in paths_dict.values()) or any(src_port in path for path in paths_dict.values()):
            #printRed(f"TCP packet {src_ip}:{src_port} should already be on a path. Dropping.")
            return
        
        # Compute the shortest simple paths list if it doesn't already exist (don't let servers generate the paths)
        if len(paths_dict) == 0 and src_ip not in self.servers:
            printRed(f"about to generate paths list: {(self.graph, src_ip, dst_ip, self.PATH_SELECTOR_PRESET, self.NUM_PATHS)}")
            paths:list[tuple] = get_paths(self.graph, src_ip, dst_ip, self.PATH_SELECTOR_PRESET, self.NUM_PATHS) # Generate list of paths according to the selected preset
            # paths = self.PATH_SELECTOR(self.graph, src_ip, dst_ip, self.NUM_PATHS, self.PATH_PENALTY) # Runs whatever path selector was requested by arguments
            for path in paths:
                self.paths.setdefault(src_ip, {}).setdefault(dst_ip, {}).setdefault(tuple(path), []) # Update paths list for this connection (no subflows assigned to paths yet!)
            if self.DEBUG: printYellow(f"Generated new paths list: {paths}")

        # Apply a high-priority rule along the kth-shortest path for this dst_port (subflow) ideally tokens should be used instead, but OpenFlow doesn't currently support MPTCP statistics. dst_port works better than src_port thanks to iperf control subflows stealing paths
        forward_match:OFPMatch = parser.OFPMatch(eth_type=0x0800, ip_proto=inet.IPPROTO_TCP, ipv4_src=src_ip, ipv4_dst=dst_ip, tcp_dst=dst_port) # Match packets sending as part of this subflow (sending from src_ip, sending to dst_ip, sending to dst_port)
        backward_match:OFPMatch = parser.OFPMatch(eth_type=0x0800, ip_proto=inet.IPPROTO_TCP, ipv4_src=dst_ip, ipv4_dst=src_ip, tcp_src=dst_port) # Match packets returning on this subflow (sending from dst_ip, sending to src_ip, sending from dst_port)
        if len(paths_dict.items()) != 0:
            min_length = min(len(subflow_count) for subflow_count in paths_dict.values())# lowest subflow count
            for path, subflows in paths_dict.items(): # find the (shortest) path with the least subflows
                if len(subflows) == min_length:
                    self.apply_rules_along_path(path, forward_match, backward_match, self.PRIORITY_HIGH, parser, ofproto, table_id=self.TCP_TABLE) # apply high-priority rule
                    paths_dict[path].append(dst_port) # record which path this subflow will use
                    break
    
    def apply_rules_along_path(self, path:tuple, forward_match, backward_match, priority:int, parser:ofproto_v1_3_parser, ofproto:ofproto_v1_3, table_id:int):
        """
        Takes as input a path and applies the specified flow rules along that path.
        Updated to apply rules bidirectionally, preventing ACK packets (or any from dst) from generating their own new paths.
            forward_match: matches to packets sent from src on this subflow
            backward_match: matches to packet returning to src from dst on this subflow
        """
        if self.DEBUG: printYellow(f"\tapplying rules to path: {path}")
        found_client_overhead = False # Will be set to true when the the src's overhead satellite has been identified
        found_server_overhead = False
        # Install flow rules to each switch on the path
        for i, dpid in enumerate(path): 
            if i >= len(path)-1:
                continue

            next_hop = path[i+1]

            # Only apply forward rules to this dpid if it is a switch
            if '.' not in str(dpid):
                curr_datapath = get_switch(self, dpid)[0].dp
                # Update mesh nodes and edges with knowledge of this path (Only used for plotting)
                if dpid in self.mesh_graph.nodes():
                    # Tell the "first" switch that it is overhead of the host
                    if not found_client_overhead and dpid < 10000:     
                        found_client_overhead = True
                        if path[0] not in self.mesh_graph.nodes[dpid]['overhead']: 
                            self.mesh_graph.nodes[dpid]['overhead'].append(path[0]) # Tell the current switch it is directly overhead of the src_ip
                    if not found_server_overhead and dpid < 10000 and next_hop > 10000:
                        found_server_overhead = True
                        if path[0] not in self.mesh_graph.nodes[dpid]['overhead']: 
                            self.mesh_graph.nodes[dpid]['overhead'].append(path[-1]) # Tell the current switch it is directly overhead of the dst_ip
                    # Update mesh graph only with "forward" paths. Allow repeats to represents mutliple siblings subflows on shared edges.
                    if path[0] in self.clients:
                        # Tell the current switch that an IP passed through it
                        self.mesh_graph.nodes[dpid]['src_ips'].append(path[0])
                        # Tell the current edge that an IP was pathed through it
                        if next_hop in self.mesh_graph.nodes(): # Tell the current edge that the src_ip was pathed through it
                            self.mesh_graph[dpid][next_hop]['src_ips'].append(path[0]) 

                # Build and send the forward_match rule message
                out_port = self.graph[dpid][next_hop]['src_port'] # outgoing port connecting this datapath to the next on the path
                actions = [parser.OFPActionOutput(out_port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = parser.OFPFlowMod(datapath=curr_datapath,
                                        table_id=table_id,
                                        priority=priority,
                                        match=forward_match,
                                        instructions=inst)
                curr_datapath.send_msg(mod)
            
            # Only apply backward rules if the next dpid is a switch
            if '.' not in str(next_hop):
                next_datapath = get_switch(self, next_hop)[0].dp
                out_port = self.graph[dpid][next_hop]['dst_port'] # outgoing port connecting this datapath to the next on the path
                actions = [parser.OFPActionOutput(out_port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = parser.OFPFlowMod(datapath=next_datapath, # Apply the rule to the next switch on the path
                                        table_id=table_id,
                                        priority=priority,
                                        match=backward_match,
                                        instructions=inst)
                next_datapath.send_msg(mod)
    
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev:EventSwitchEnter):
        """
        Triggered when a switch connects to the controller.
        """
        datapath:Datapath = ev.switch.dp
        dpid:int = datapath.id
        self.graph.add_node(dpid)
        if dpid < 10000: self.mesh_graph.add_node(dpid, src_ips=[], subflows=[], overhead=[])
        self.complete_graph.add_node(dpid) # maybe map to switch/host name somehow?
        #self.switch_mst = nx.minimum_spanning_tree(self.mesh_graph.to_undirected())
        self.switches.append(dpid)
        if self.DEBUG: printYellow(f"{dpid} joined the network. Switch total: {len(self.switches)}")


    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def handler_switch_leave(self, ev:EventSwitchLeave):
        """
        Triggered when a switch disconnects from the controller.
        """
        datapath:Datapath = ev.switch.dp
        dpid:int = datapath.id
        self.graph.remove_node(dpid)
        #self.switch_mst = nx.minimum_spanning_tree(self.mesh_graph.to_undirected())
        self.switches.remove(dpid)
        if self.DEBUG: printYellow(f"{dpid} left the network. Switch total: {len(self.switches)}")

    @set_ev_cls(event.EventLinkAdd)
    def handler_link_add(self, ev:EventLinkAdd):
        """
        Triggered when a link is discovered.
        """
        link:Link = ev.link
        src_dpid:int = link.src.dpid
        dst_dpid:int = link.dst.dpid
        src_port:int = link.src.port_no
        dst_port:int = link.dst.port_no

        
        if src_dpid < 10000 and dst_dpid < 10000: 
            self.mesh_graph.add_edge(src_dpid, dst_dpid, src_port=src_port, dst_port=dst_port, weight=1, src_ips=[], subflows=[])
            
        self.graph.add_edge(src_dpid, dst_dpid, src_port=src_port, dst_port=dst_port, weight=1)
        self.complete_graph.add_edge(src_dpid, dst_dpid, src_port=src_port, dst_port=dst_port, weight=1)
        #self.switch_mst = nx.minimum_spanning_tree(self.mesh_graph.to_undirected())
        #self.output_graph()
        self.links.append(link)

        if self.DEBUG: printYellow(f"\t({src_dpid}->{dst_dpid})\t{self.graph[src_dpid][dst_dpid]} joined the network. Link total: {len(self.links)}")
        
    @set_ev_cls(event.EventLinkDelete)
    def handler_link_delete(self, ev:EventLinkDelete):
        """
        Triggered when a link is removed.
        """
        link:Link = ev.link
        src_dpid:int = link.src.dpid
        dst_dpid:int = link.dst.dpid

        if self.graph.has_edge(src_dpid, dst_dpid):
            self.graph.remove_edge(src_dpid, dst_dpid)
        #self.switch_mst = nx.minimum_spanning_tree(self.mesh_graph.to_undirected())
        self.links.remove(link)  
        if self.DEBUG: printYellow(f"\t({src_dpid}->{dst_dpid}) left the network. Link total: {len(self.links)}")

    def print_paths(self):
        for src in self.paths.values():
            for dst in src.values():
                for path, subflows in dst.items():
                    printYellow(f"{path} : \033[95m{subflows}\033[0m")
    
    def cleanup_and_output(self):
        if self.DEBUG: 
            printYellow("Final paths state: ")
            self.print_paths()
        # Ouput pdf to path that constantly overwrites itself - allows you to have graph pdf open on second monitor and it will update in real time as experiments complete
        easy_pdf_path = "/home/james/networkx_plots/plot.pdf"
        self.output_graph(self.mesh_graph, easy_pdf_path)

        # output graph to main experiment folder
        main_pdf_path = f"{self.OUTPUT_PATH}/graph.pdf"
        self.output_graph(self.mesh_graph, main_pdf_path)

    def _handle_sigterm(self, signum, frame):
        """
        Performs cleanup operations when execution completes
        """
        printYellowFill("TERMINATE signal received, controller closing")
        self.cleanup_and_output()
        os._exit(0)
    
    def _handle_sigint(self, signum, frame):
        """
        Performs cleanup operations when execution is stopped early
        """
        printYellowFill("SIGINT signal received, controller closing prematurely")
        self.cleanup_and_output()
        os._exit(0)




    # Plotting and other -------------------------------------------------------------------------------------------------

    def grid_pos(self, num_nodes, x_offset=0, y_offset=0):
        """
        Returns a grid of positions based on the input number of nodes
        """
        side = int(math.sqrt(num_nodes))
        pos = {}
        for i in range(0, num_nodes):
            row = i // side
            col = i % side
            pos[i+1] = (col + x_offset, row + y_offset)
        return pos

    def output_graph(self, out_graph, output_path:str):
        """
        Saves the given graph as a page in the output pdf.
        """
        printYellow(f"Clients: {self.clients}")
        printBlue(f'Servers: {self.servers}')
        # Assign colors to hosts based on their name (c1 gets 1st color, x2 second color, and so on)
        colors_list = ["#1f77bf", "#ff7f0e", "#2ca02c", "#d6272b", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
        host_colors = {}
        for src in self.hosts:
            host_colors[src] = colors_list[(int(self.ip_to_host[src][1:]) - 1) % len(colors_list)]
        if self.DEBUG: 
            printYellow("done assigning connection colors.")
            printYellow(f'\t{host_colors}')

        # Assign colors to edges (based on subflow paths)
        color_to_edges = {}
        edge_to_colors = {}
        for src, dst in out_graph.edges():
            for ip in out_graph[src][dst]['src_ips']:
                color_to_edges.setdefault(host_colors[ip], [])
                color_to_edges[host_colors[ip]].append((src, dst))
                edge_to_colors.setdefault((src, dst), [])
                edge_to_colors[(src, dst)].append(host_colors[ip])
            if len(out_graph[src][dst]['src_ips']) == 0:
                color_to_edges.setdefault("#888888", [])
                color_to_edges['#888888'].append((src, dst))
                edge_to_colors.setdefault((src, dst), [])
                edge_to_colors[(src, dst)].append("#888888")
        if self.DEBUG:
            printYellow("Done assigning edge colors.")
            printYellow(color_to_edges)

        # Assign colors and lables to nodes (Based on host the node is directly overhead of. Color is by connection, label maps IP to hostname)
        node_colors = []
        node_labels = {}
        for node in self.mesh_graph.nodes:
            if len(self.mesh_graph.nodes[node]['overhead']) > 0:
                overhead = self.mesh_graph.nodes[node]['overhead'][0]
                color = host_colors[overhead]
                overhead = self.ip_to_host[overhead]
            else:
                overhead = ''
                color = '#888888'
            node_colors.append(color)
            node_labels[node] = overhead
        if self.DEBUG:
            printYellow("done assigning node labels and colors")
            printYellow(f'\t{node_labels}')
            printYellow(f'\t{node_colors}')

        # Plot the thing
        pdf = PdfPages(output_path)
        fig, ax = plt.subplots(figsize=(7, 7))
        plt.tight_layout(rect=[0, 0, 1, 1], pad=1.0)
        pos = self.grid_pos(len(out_graph.nodes))
        printRed(pos)
        printRed(out_graph.nodes)
        
        nx.draw_networkx_nodes(out_graph, pos=pos, ax=ax, node_color=node_colors, node_size=2000)
        nx.draw_networkx_labels(out_graph, pos=pos, ax=ax, labels=node_labels, font_color='#FFFFFF', font_size=18)
        #nx.draw_networkx_edges(out_graph, pos=pos, ax=ax)

        
        subflow_line = {
            "line_width": 4,
            "line_spread": .013, # .14 creates very minimal gaps
            "global_line_offset": .01,
            "line_alpha": 1,
            "line_style": '-'
        }

        empty_line = {
            "line_width": 1.6,
            "line_spread": .019,
            "global_line_offset": .01,
            "line_alpha": .6,
            "line_style": '--'
        }


        for edge in edge_to_colors:
            for c, color in enumerate(sorted(edge_to_colors[edge])):
                # Assign line properties based on link utilization status
                if color == '#888888':
                    style = empty_line
                    connection_style = 'arc3'
                else:
                    style = subflow_line
                    spread = style['line_width'] * style['line_spread']
                    bar_fraction = spread*(c+1)-spread*len(edge_to_colors[edge])/2 - .01
                    connection_style = f'bar,fraction={bar_fraction}'

                # Make wrapped lines render differently
                graph_pos = pos.copy()
                node_a = edge[0]
                node_b = edge[1]

                # Edge wrapping horizontally, first node is on the right edge
                if pos[node_a][0] - pos[node_b][0] > 1:
                    right_node = node_a 
                    left_node = node_b
                    graph_pos[left_node] = (pos[right_node][0] + 1, pos[left_node][1])

                # Edge wrapping horizontally, first node is on the left edge
                if pos[node_a][0] - pos[node_b][0] < -1:
                    right_node = node_b 
                    left_node = node_a
                    graph_pos[left_node] = (pos[right_node][0] + 1, pos[left_node][1])

                # Edge wrapping vertically, first node is on the top edge
                if pos[node_a][1] - pos[node_b][1] > 1:
                    top_node = node_a 
                    bottom_node = node_b
                    graph_pos[bottom_node] = (pos[bottom_node][0], pos[top_node][1] + 1)

                # Edge wrapping vertically, first node is on the top edge
                if pos[node_a][1] - pos[node_b][1] < -1:
                    top_node = node_b
                    bottom_node = node_a
                    graph_pos[bottom_node] = (pos[bottom_node][0], pos[top_node][1] + 1)

                # TODO: when edge is wrapping, render it a second time on the opposite side.

                nx.draw_networkx_edges(
                    out_graph, 
                    pos=graph_pos,
                    edgelist=[edge],
                    edge_color=color,
                    width=style['line_width'],
                    alpha=style['line_alpha'],
                    style=style['line_style'],
                    arrows=True,
                    arrowstyle='-',
                    arrowsize=.001,
                    connectionstyle=connection_style
                )
        
        pdf.savefig(fig, dpi=1080)
        plt.close(fig)
        pdf.close()
        printYellow(f"Graph saved to {output_path}")
    
RESET = "\033[0m"

def printDebug(string):
    COLOR="\033[95m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")
def printDebug2(string):
    COLOR="\033[103m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")
def printDebug3(string):
    COLOR="\033[42m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")
def printBlue(string):
    COLOR = "\033[94m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printBlueFill(string):
    COLOR = "\033[104m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printGreen(string):
    COLOR = "\033[32m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printGreenFill(string):
    COLOR = "\033[102m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printYellow(string):
    COLOR = "\033[33m" 
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printYellowFill(string):
    COLOR = "\033[103m" 
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printRed(string):
    COLOR = "\033[31m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printSS(string):
    COLOR = "\033[33m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printTC(string):
    COLOR = "\033[90m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")

def printPink(string):
    COLOR = "\033[95m"
    print("\r\033[K", end='', flush=True) 
    print(f"{COLOR}{string}{RESET}")

def printPinkFill(string):
    COLOR = "\033[105m"
    print("\r\033[K", end='', flush=True)
    print(f"{COLOR}{string}{RESET}")