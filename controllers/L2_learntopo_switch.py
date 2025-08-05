__author__ = 'Ehsan'

# Obtained from https://github.com/Ehsan70/RyuApps/blob/master/TopoDiscoveryInRyu.md
# Includes extra comments for my own learning purposes

from ryu.base import app_manager
from ryu.controller import ofp_event # packet events
from ryu.topology import event # Topology change events
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

# Below is the library used for topo discovery
from ryu.topology.api import get_switch, get_link # This SOMEHOW causes some weird errors, just by importing it
import copy

# A slightly modified version of L2_learning_switch that maintains a list of switches and links, and is slightly more organized
class BasicTopoLearner(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(BasicTopoLearner, self).__init__(*args, **kwargs)
        # Used for learning switch functioning
        # Holds the topology data and structure (why store the topology as switches and links rather than a graph?)
        self.topo_raw_switches = []
        self.topo_raw_links = []
        self.mac_to_port = {}  # {dpid: {mac_addr: port}}


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        self.logger.info('OFPSwitchFeatures received: '
                         '\n\tdatapath_id=0x%016x n_buffers=%d '
                         '\n\tn_tables=%d auxiliary_id=%d '
                         '\n\tcapabilities=0x%08x',
                         msg.datapath_id, msg.n_buffers, msg.n_tables,
                         msg.auxiliary_id, msg.capabilities)

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    # We are not using this function
    def delete_flow(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

    # Just a utility method to make installing flow rules easier. Includes the necessary buffer checks and such.
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    """
    This is called when Ryu receives an OpenFlow packet_in message. The trick is set_ev_cls decorator. This decorator
    tells Ryu when the decorated function should be called.
    """
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len: # Does this trigger if the switch buffered the packet and sent an id? I'm surprised more isn't done with this information.
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        # Gather packet information
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        # get ethernet header and information
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src

        # Add default entry to learning table in case it doesn't exist
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("\tpacket in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        # Determine the correct port(s) to forward the packet
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst] # send the packet out the learned port
        else:
            out_port = ofproto.OFPP_FLOOD # flood the packet out of ALL ports to gather information
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    ###################################################################################
    """
    The event EventSwitchEnter will trigger the activation of get_topology_data().
    """
    # Ryu (presumably the app manager parent class) automatically maintains a list of switches of links found during topology discovery
    # This means you don't actually have to do anything yourself to get this information - this method just acts as a guide for how to reference this information
    # However, it may be useful to create copies like this as needed to avoid synchronization issues, especially when running graph algorithms that may take some time to complete
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev):
        # The Function get_switch(self, None) outputs the list of switches.
        self.topo_raw_switches = copy.copy(get_switch(self, None))
        # The Function get_link(self, None) outputs the list of links.
        self.topo_raw_links = copy.copy(get_link(self, None))

        """
        Now you have saved the links and switches of the topo. So you could do all sort of stuf with them. 
        """

        print(" \t" + "Current Links:")
        for l in self.topo_raw_links:
            print (" \t\t" + str(l))

        print(" \t" + "Current Switches:")
        for s in self.topo_raw_switches:
            print (" \t\t" + str(s))

    """
    This event is fired when a switch leaves the topo. i.e. fails.
    """
    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def handler_switch_leave(self, ev):
        self.logger.info("Not tracking Switches, switch leaved.")