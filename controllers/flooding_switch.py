from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

# EDITED FROM Ryu tutorial docs: https://ryu.readthedocs.io/en/latest/writing_ryu_app.html

# Basic swich that always installs a default rule to flood packets out all outgoing ports
class L2FloodingSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(L2FloodingSwitch, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Called when the switch first connects.
        Installs a default rule to flood packets out all outgoing ports
        """
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # Match all packets (wildcard match)
        match = parser.OFPMatch()

        # Action: send to controller
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

        # Instruction: apply the above action
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        # Priority 0 = lowest (catch-all rule)
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=0,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)