from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet

# This script has as detailed comments as I could managed. Just meant as a reference for later.

# Note to self - Ryu is currently only compatible with evenlet 29 or older. Also try Python 2.7 if you run into issues

# Basic learning switch, just from ChatGPT
# The Ryu tutorial script does not work on my setup, but does this. Use this as a base and use the tutorial script as a learning tool.

# Controller perspective - 
# Initialization: tell all switches to send all packets to me!
# Packet recieved: If I have seen this MAC on this switch before on a port (X), send a rule to the switch to always send packets with that in_port and Mac out of port X, then tell the switch to send this packet out port X
#                   If I haven't seen it before, update my table and tell the switch to flood the ports with the packet
# Thought process: If I do this, my table will grow over time as I build up state, and all the switches will slowly accumluate rules.
#                   Eventually, almost all in_port/dst_mac pairs will have a rule on each switch, and I will barely receive any messages

# Switch perspective -
# Initialization: The controller gave me a rule that says to send it any packet to match to any other rules, I'll do that
# Packet recieved: If I have a rule saying where to send it, I'll send it out that port
#                   If I don't, then I will follow the original rule and send it to the controller
# Controller message received: The controller doesn't know anything about this destination, it told me to flood the ports
#                               OR the controller knows about this packet, it sent me a new rule telling me where to send packets like this in the future. AND it told me to send this packet out of port X.

# So here is an example situation, in a new network
# ---------------------------------------------------------------------------------------------------------------------
# switch_features_handler is called to initialize each switch, adding a default rule to send packets to the controller (if no other rule matches exist)
# a new packet is sent, and the packet reaches a switch on a particular port. 
# The switch checks its flow rule table and finds no matches (other than the default priority=0 rule that matches all packets), so the switch sends a packet_in message to the controller for guidance.
# The controller recieves the packet_in, calling packet_in_handler. It checks the table to see if it knows where to send it. It doesn't.
# So, the controller updates its table with this new information (MAC address ABCDE is somewhere in the direction of the port/switch this packet was received from) 
# The controller sends a rule to flood the ports with the packet (ignoring in_port) because it doesn't kno where else to send it.
# ...some time passes
# later, a another packet is sent to the same destination MAC, and it encounters the same router
# The packet matches no rule (other than the default), so a packet_in message is sent to the controller
# The controller recieves packet_in, and checks its table to see if it recognizes the dst MAC. It does!
# so, the controller send a message that applies a rule to the switch: "from now on, if you recieve a packet on that port with that MAC, send it out of port X"
# the rule alone is not enough. The switch is still waiting on instructions for THIS PARTICULAR packet
# so, the controller sends one last message, saying to send the packet out port X

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {} # dictionary that maps mac adresses to their known ingress ports. Builds over time.

    # An "initialization" method for each switch. Installs a default rule to send packets to the controller, if no better rule matches exist
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        # Gather data from the switch
        datapath = ev.msg.datapath # represents the switch itself
        ofproto = datapath.ofproto # represents the protocol the switch speaks
        parser = datapath.ofproto_parser # A object filled with functions used to build messages for the correct protocol. Notice this is used to build any responses.

        # Default rule: send unmatched packets to controller
        match = parser.OFPMatch() # A wildcard that matches ALL packets
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)] # Create an action to send to the controller without a buffer. OFPP_CONTROLLER means send to controller, OFPCML_NO_BUFFER means complete packet should be sent without a buffer
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # Apply the list of actions immediately? 
        mod = parser.OFPFlowMod(datapath=datapath, priority=0, match=match, instructions=inst) # mod is modify. Datapacket tells Ryu which switch to send the message to. This says "add or modify a rule that says to: follow the given instructions for any packets that meet the given match." If there are multiple matches, highest priority wins.
        datapath.send_msg(mod) # Send the message to the correct datapath (switch)
        
        #in short, we installed a flow rule to every switch that gives a default, minimum priority match to ALL packets that says to send them to the controller.
        # This essentially means if a switch receives a packet and finds no matches (other than this one) send the packet to the controller for guidance

    # Called when a switch sends a packet to the controller (asking for guidance)
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        # Gather data from the packet_in
        msg = ev.msg # ev is the event object, and this method is called when OFP_PacketIn events occur. So ev.msg is an instance of OFP_PacketIn
        datapath = msg.datapath # Switch the packet came from
        ofproto = datapath.ofproto # what protocol the switch speaks
        parser = datapath.ofproto_parser # A object filled with functions used to build messages for the correct protocol. Notice this is used to build any responses.
        in_port = msg.match['in_port'] # What switch port the packet arrived at

        pkt = packet.Packet(msg.data) # parses the raw bytes of the packet_in event message into into a high-level Packet object with all the relevant headers
        eth = pkt.get_protocol(ethernet.ethernet) # Returns an ethernet header object (parsed from the first instance of an ethernet header found in the packet object)
        dst = eth.dst # destination MAC (not IP bc this is an ethernet header)
        src = eth.src # source MAC

        dpid = datapath.id # A unique switch identifier (64-bit int) provided by OpenFlow
        self.mac_to_port.setdefault(dpid, {}) # If no dict entry exists for switch dpid, create an empty one
        self.mac_to_port[dpid][src] = in_port # (nested dictionary) within the dict's dpid entry, create an entry with key source and value in_port. This tracks, at a particular switch, the last port we saw a certain mac arrive from

        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD) # Set the outgoing port to the learned port. If there is no learned port, flood the packet out all ports except in_port
        actions = [parser.OFPActionOutput(out_port)] # create an action based on the out_port value we generated and add it to the actions array (to be sent later)

        # If we recognize the dst MAC, we know where to send it. Create a rule for this switch to always send packets with this MAC out that port. 
        # We do not need to check if a rule already exists, as this method is only called if the switch didn't know what to do with the packet
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst) # Match any packets with the same in_port and destination to the learned port. in_port is included to prevent flooding in weird edge cases like MAC spoofing.
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # Create an instruction object that says to apply the given actions immediately 
            mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=inst) # create the modify rule (priority 1 is higher than the default from above)
            datapath.send_msg(mod) # send the modify rule message

        # Build the outgoing message, saying where to send this packet (actions), 
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id, # the switch may have buffered the packet and send you an ID for that buffer, rather than the packet itself. This specifies the buffer so the switch knows which packet to send, if necessary.
                                  in_port=in_port, # The port the packet came from. Some actions, like FLOOD, need to omit the in_port.
                                  actions=actions, # The action to take (etiher flood or send to the known port)
                                  data=msg.data) # Only necessary if the switch didn't buffer the packet data. Ignored otherwise.
        datapath.send_msg(out) # Send out the packet