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

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../')
sys.path.append( mymodule_dir )

"""
Builds a graph representation of the network and uses is to assign multiple shortest paths between hosts
Compares paths based only on the number of hops
Assigns subflows unique paths (when available) sequentially based on their source ports
"""
class KShortestPaths(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(KShortestPaths, self).__init__(*args, **kwargs)
        """
        Initializes important constants, objects, and signals.
        Priority levels and table IDs are stored as constants for convenience and more readable code.
        Network topology is stored across several graphs, each used for different purposes
        """
        self.PRIORITY_DEFAULT = 0
        self.PRIORITY_LOW = 5
        self.PRIORITY_HIGH = 10

        self.DEFAULT_TABLE = 0
        self.TCP_TABLE = 1

        self.graph: DiGraph = nx.DiGraph() # graph of the entire network, including hosts
        self.switch_graph: DiGraph = nx.DiGraph() # Graph of the network, excluding hosts
        self.switch_mst: DiGraph = nx.DiGraph() # minimum spanning tree of the switch graph, used for flooding and host discovery
        self.ip_to_port: dict[str, dict[str, dict[int]]] = {} # dpids[ips[in_ports]]
        self.paths: dict[str, dict[str, dict[tuple : list[int]]]] = {} # src[dst[path[subflows_on_path]]], for every src-dst pair there exists a dict of path tuples, and for every path tuple there exists a list of subflows (dst_ports) on it
        self.hosts = {}
        self.pdf = PdfPages("/home/james/networkx_plots/plot.pdf")
        signal.signal(signal.SIGTERM, self._handle_sigterm) # call _handle_sigterm when the process is signalled to terminate

    def _handle_sigterm(self, signum, frame):
        """
        Performs cleanup operations when execution completes
        """
        printYellow("Final paths state: ")
        for src in self.paths.values():
            for dst in src.values():
                for path, subflows in dst.items():
                    printYellow(f"{path} : \033[95m{subflows}\033[0m")
        printYellowFill("TERMINATE signal received, controller closing")
        self.pdf.close()
        os._exit(0)
        

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
        printRed("found an IP packet")
        #printYellow(ip_headers)
        dst_ip:str = ip_headers.dst
        src_ip:str = ip_headers.src

        # learn the in_port of this IP at this datapath (currently not in use)
        self.ip_to_port.setdefault(dpid, {}).setdefault(dst_ip, []).append(in_port)

        # Learn the location of this host in the topology (if first sighting)
        if src_ip not in self.hosts:
            printYellow(f"found host {src_ip}")
            self.hosts[src_ip] = dpid
            self.graph.add_node(src_ip)
            self.graph.add_edge(src_ip, dpid, src_port=0000, dst_port=in_port)
            self.graph.add_edge(dpid, src_ip, src_port=in_port, dst_port=0000)
            self.output_graph()

        # ASSERT: dst exists, but a path has not been generated of this datapath
        # (split here)
        # Flood the MST for information if the dst has not yet been discovered
        
        # Flood if the dst has not yet been discovered
        if dst_ip not in self.hosts:
            printYellow(f'{dst_ip} not yet learned, flooding from {datapath.id}')
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(datapath=datapath,
                                    buffer_id=msg.buffer_id,
                                    in_port=in_port,
                                    actions=actions,
                                    data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None)
            datapath.send_msg(out)
            return

        if ip_headers.proto == inet.IPPROTO_TCP:
            printYellow('Found tcp packet hooray')
            self.handle_tcp_packets(ev)
        else:
            printYellow('Found default packet hooray')
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
        match:OFPMatch = parser.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip) # any IP packets headed to dst, regardless of port
        self.apply_rules_along_path(shortest_path, match, self.PRIORITY_LOW, parser, ofproto, self.DEFAULT_TABLE) # apply low-priority rule

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
        printYellow(f"found a TCP packet - {src_ip}:{src_port} headed to {dst_ip}:{dst_port}")
        paths_dict = self.paths[src_ip][dst_ip]
        if any(dst_port in path for path in paths_dict.values()):
            printRed(f"TCP packet {src_ip}:{src_port} should already be on a path. Dropping.")
            return
        
        # Compute the shortest simple paths list if it doesn't already exist
        if len(paths_dict) == 0:
            k_shortest_paths:list[tuple] = [tuple(path) for path in nx.shortest_simple_paths(self.graph, src_ip, dst_ip)]
            for curr_path in k_shortest_paths:
                self.paths.setdefault(src_ip, {}).setdefault(dst_ip, {}).setdefault(curr_path, []) # apply shortest paths to dict they do not already exist
            printYellow(f"No existing paths found. Generated k_shortest_paths: {k_shortest_paths}")

        # Apply a high-priority rule along the kth-shortest path for this dst_port (subflow) ideally tokens should be used instead, but OpenFlow doesn't currently support MPTCP statistics. dst_port works better than src_port thanks to iperf control subflows stealing paths
        match:OFPMatch = parser.OFPMatch(eth_type=0x0800, ip_proto=inet.IPPROTO_TCP, ipv4_src=src_ip, ipv4_dst=dst_ip, tcp_dst=dst_port) # match TCP packets with the correct dst_port and dst_ip
        min_length = min(len(subflow_count) for subflow_count in paths_dict.values()) # lowest subflow count
        for path, subflows in paths_dict.items(): # find the (shortest) path with the least subflows
            if len(subflows) == min_length:
                self.apply_rules_along_path(path, match, self.PRIORITY_HIGH, parser, ofproto, table_id=self.TCP_TABLE) # apply high-priority rule
                paths_dict[path].append(dst_port) # record which path this subflow will use
                break
    
    def apply_rules_along_path(self, path:tuple, match, priority:int, parser:ofproto_v1_3_parser, ofproto:ofproto_v1_3, table_id:int):
        # Install flow rules to each switch on the path
        printYellow(f"applying rules to path: {path}")
        for i, dpid in enumerate(path): 
            if '.' in str(dpid): # ignore first and last entry (hosts)
                continue    
            curr_datapath = get_switch(self, dpid)[0].dp
            next_hop = path[i+1]
            out_port = self.graph[dpid][next_hop]['src_port'] # outgoing port connecting this datapath to the next on the path
            actions = [parser.OFPActionOutput(out_port)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=curr_datapath,
                                    table_id=table_id,
                                    priority=priority,
                                    match=match,
                                    instructions=inst)
            curr_datapath.send_msg(mod)
    
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev:EventSwitchEnter):
        """
        Triggered when a switch connects to the controller.
        """
        datapath:Datapath = ev.switch.dp
        dpid:int = datapath.id
        printYellow(f"{dpid} joined the network")
        self.switch_graph.add_node(dpid)
        self.graph.add_node(dpid)
        self.switch_mst = nx.minimum_spanning_tree(self.switch_graph.to_undirected())


    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def handler_switch_leave(self, ev:EventSwitchLeave):
        """
        Triggered when a switch disconnects from the controller.
        """
        datapath:Datapath = ev.switch.dp
        dpid:int = datapath.id
        printYellow(f"{dpid} left the network")
        self.switch_graph.remove_node(dpid)
        self.graph.remove_node(dpid)
        self.switch_mst = nx.minimum_spanning_tree(self.switch_graph.to_undirected())

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

        printYellow(f"({src_dpid}->{dst_dpid}) joined the network")
        self.switch_graph.add_edge(src_dpid, dst_dpid, src_port=src_port, dst_port=dst_port)
        self.graph.add_edge(src_dpid, dst_dpid, src_port=src_port, dst_port=dst_port)
        self.switch_mst = nx.minimum_spanning_tree(self.switch_graph.to_undirected())
        self.output_graph()
        
    @set_ev_cls(event.EventLinkDelete)
    def handler_link_delete(self, ev:EventLinkDelete):
        """
        Triggered when a link is removed.
        """
        link:Link = ev.link
        src_dpid:int = link.src.dpid
        dst_dpid:int = link.dst.dpid

        printYellow(f"({src_dpid}->{dst_dpid}) left the network")
        if self.switch_graph.has_edge(src_dpid, dst_dpid):
            self.switch_graph.remove_edge(src_dpid, dst_dpid)
        if self.graph.has_edge(src_dpid, dst_dpid):
            self.graph.remove_edge(src_dpid, dst_dpid)
        self.switch_mst = nx.minimum_spanning_tree(self.switch_graph.to_undirected())  

    def output_graph(self):
        """
        Saves the current graph as a page in the output pdf.
        Useful for debugging - make sure links have established correctly, in what order, if any are missing.
        """
        fig, ax = plt.subplots()
        nx.draw(self.graph, with_labels=True, ax=ax)
        self.pdf.savefig(fig)
        plt.close(fig)

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