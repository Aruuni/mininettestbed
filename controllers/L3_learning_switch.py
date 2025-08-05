from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ipv4


"""
Basic learning switch based on IP addresses
Maintains a dictionary of learned ingress ports of IP addresses for each switch, and uses them to route future packets
"""
class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)
        self.ip_to_port: dict[str, dict[str, int]] = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Called when the switch first connects.
        Installs a default (table-miss) flow entry to send unknown packets to the controller.
        """
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # Match all packets (wildcard match)
        match = parser.OFPMatch()

        # Action: send to controller
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        # Instruction: apply the above action
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        # Priority 0 = lowest (catch-all rule)
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=0,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Handles packets sent to controller via table-miss flow.
        Learns source IPs and installs forwarding rules.
        """
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # Unique ID for the switch
        dpid = datapath.id
        self.ip_to_port.setdefault(dpid, {})
        

        # Parse incoming packet
        pkt = packet.Packet(msg.data)
        ip_headers = pkt.get_protocol(ipv4.ipv4)

        # Drop LLDP or malformed packets
        if ip_headers is None:
            return
        dst = ip_headers.dst
        src = ip_headers.src
        in_port = msg.match['in_port']

        # Learn the ip-to-port mapping for this switch
        self.ip_to_port[dpid][src] = in_port

        # Decide where to send the packet
        if dst in self.ip_to_port[dpid]:
            out_port = self.ip_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # If destination is known, install a flow rule
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, ipv4_dst=dst) #eth_type=0x0800 specifies that we want to look INSIDE OF the ipv4 fields for ipv4 packets. Without this, every packet will be sent to the controller, be searched for ipv4 headers, and come up short.
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

            mod = parser.OFPFlowMod(datapath=datapath,
                                    priority=1,
                                    match=match,
                                    instructions=inst)
            datapath.send_msg(mod)

        # Send the current packet manually
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None)
        datapath.send_msg(out)


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