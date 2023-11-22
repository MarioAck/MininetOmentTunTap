from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import dpid as dpid_lib
from ryu.lib import stplib
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4
from ryu.app import simple_switch_13
from ryu.ofproto import ofproto_v1_3_parser
import socket


class SimpleSwitch13(simple_switch_13.SimpleSwitch13):
    _CONTEXTS = {'stplib': stplib.Stp}

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.max_dpid_port = {}
        self.stp = kwargs['stplib']
        # Sample of stplib config.
        # please refer to stplib.Stp.set_config() for details.
        config = {dpid_lib.str_to_dpid('0000000000000001'):
        {'bridge': {'priority': 0x8000}},
        dpid_lib.str_to_dpid('0000000000000002'):
        {'bridge': {'priority': 0x8000}},
        dpid_lib.str_to_dpid('0000000000000003'):
        {'bridge': {'priority': 0x8000}}}
        self.stp.set_config(config)

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

    @set_ev_cls(stplib.EventPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        ip = pkt.get_protocols(ipv4.ipv4)
        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        isToBrdMltOf = dst == "ff:ff:ff:ff:ff:ff" or dst.startswith("33:33:00:00:")

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid].setdefault("host", {})
        self.logger. info("packet in %s %s %s %s", dpid, src, dst, in_port)

        if in_port == 1:
            self.mac_to_port[dpid]["host"] = src

        if in_port == 1:
            actions = [parser.OFPActionOutput(in_port, 0)]
            match = parser.OFPMatch(eth_dst=src)
            self.add_flow(datapath, 1, match, actions)
            actions = []
            match = parser.OFPMatch(in_port=4, ipv4_src='10.0.0.' + str(dpid), eth_type=0x800)
            self.add_flow(datapath, 1, match, actions)

        if self.mac_to_port[dpid]["host"] and dst != self.mac_to_port[dpid]["host"] and not isToBrdMltOf:
            out_port = ofproto.OFPP_FLOOD if in_port == 1 else ofproto.OFPP_IN_PORT
            actions = [parser.OFPActionOutput(out_port, 0)]
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)
        else:
            actions = [parser.OFPActionOutput(ofproto.OFPP_IN_PORT, 0)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port, 0)]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)

        self.logger. info("packet in %s %s %s %s", dpid, src, dst, out_port)
        datapath.send_msg(out)

        @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
        def _topology_change_handler(self, ev):
            dp = ev.dp
            dpid_str = dpid_lib.dpid_to_str(dp.id)
            msg = 'Receive topology change event. Flush MAC table.'
            self.logger.debug("[dpid=%s] %s", dpid_str, msg)
            if dp.id in self.mac_to_port:
                self.delete_flow(dp)
            del self.mac_to_port[dp.id]

        @set_ev_cls(stplib.EventPortStateChange, MAIN_DISPATCHER)
        def _port_state_change_handler(self, ev):
            dpid_str = dpid_lib.dpid_to_str(ev.dp.id)

            of_state = {stplib.PORT_STATE_DISABLE: 'DISABLE',
                        stplib.PORT_STATE_BLOCK: 'BLOCK',
                        stplib.PORT_STATE_LISTEN: 'LISTEN',
                        stplib.PORT_STATE_LEARN: 'LEARN',
                        stplib.PORT_STATE_FORWARD: 'FORWARD'}
            self.logger.debug("[dpid=%s][port=%d] state=%s",
                              dpid_str, ev.port_no, of_state[ev.port_state])
