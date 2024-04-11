from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, arp, mpls
from ryu.app import simple_switch_13
from ryu.ofproto import ether, ofproto_parser
from ryu import cfg
import socket

class SimpleSwitch13(simple_switch_13.SimpleSwitch13):
    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)

        CONF = cfg.CONF
        CONF.register_opts([cfg.IntOpt("switchNumber", default=0)])

        self.switchNumber = cfg.CONF.switchNumber
        self.dpid_host = {}
        self.arpToDelete = {}
        self.directionTtl = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        self.dpid_host.setdefault(dpid, {})
        self.dpid_host[dpid]["datapath"] = datapath

        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        match = parser.OFPMatch()
        self.mod_flow(datapath, 0, match, actions, True)

        actions = [parser.OFPActionDecMplsTtl(), parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_MPLS)
        self.mod_flow(datapath, 1, match, actions, True)

        actions = [parser.OFPActionDecNwTtl(), parser.OFPActionOutput(ofproto.OFPP_IN_PORT)]
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP, in_port=4)
        self.mod_flow(datapath, 2, match, actions, True)

        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_ARP, in_port=4)
        self.mod_flow(datapath, 4, match, actions, True)

        actions = [parser.OFPActionOutput(1)]
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP, in_port=4, ipv4_dst="10.0.0." + str(dpid))
        self.mod_flow(datapath, 4, match, actions, True)

        actions = []
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_ARP, in_port=4, arp_spa="10.0.0." + str(dpid))
        self.mod_flow(datapath, 5, match, actions, True)

        actions = []
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP, in_port=4, ipv4_src="10.0.0." + str(dpid))
        self.mod_flow(datapath, 5, match, actions, True)

    def mod_flow(self, datapath, priority, match, actions, add, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst, command=ofproto.OFPFC_ADD)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst, command=ofproto.OFPFC_ADD)
        datapath.send_msg(mod)

    def del_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        actions = [parser.OFPActionOutput(out_port, 0)]

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst,
                                command=ofproto.OFPFC_DELETE)

        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ipv = pkt.get_protocol(ipv4.ipv4)
        arp_pkt = pkt.get_protocol(arp.arp)

        dst = eth.dst
        src = eth.src

        dpid = datapath.id

        mplsH = pkt.get_protocols(mpls.mpls)

        mplsH.reverse()

        isToBrdMltOf = dst == "ff:ff:ff:ff:ff:ff" or dst.startswith("33:33:00:00:")

        self.dpid_host.setdefault(dpid, {})
        self.arpToDelete.setdefault(str(dpid), False)
        self.dpid_host[dpid].setdefault("host", {})

        #  print("packet in", dpid, src, dst, in_port)

        labels = list([k.label for k in mplsH])

        my_ip = "10.0.0." + str(dpid)

        found = False

        if arp_pkt:
            if (arp_pkt.src_ip in self.directionTtl and arp_pkt.dst_ip in self.directionTtl[arp_pkt.src_ip] or
                    arp_pkt.dst_ip in self.directionTtl and arp_pkt.src_ip in self.directionTtl[arp_pkt.dst_ip]):

                if my_ip in self.directionTtl:
                    found = any(i is True for i in [k == arp_pkt.dst_ip for k in self.directionTtl[my_ip]])
                elif arp_pkt.dst_ip in self.directionTtl:
                    found = any(i is True for i in [k == my_ip for k in self.directionTtl[arp_pkt.dst_ip]])

                if arp_pkt.opcode == arp.ARP_REQUEST and arp_pkt.src_ip == my_ip and in_port == 1:
                    self.directionTtl[arp_pkt.src_ip][arp_pkt.dst_ip]["arp"] += 1
                    self.directionTtl[arp_pkt.dst_ip][arp_pkt.src_ip]["arp"] += 1

                    if self.directionTtl[arp_pkt.src_ip][arp_pkt.dst_ip]["arp"] > 20:
                        print("redoo")
                        found = False
                        self.directionTtl[arp_pkt.src_ip][arp_pkt.dst_ip]["arp"] = 0
                        self.directionTtl[arp_pkt.dst_ip][arp_pkt.src_ip]["arp"] = 0

                if self.directionTtl[arp_pkt.src_ip][arp_pkt.dst_ip]["arp"] <= 0:
                    self.directionTtl[arp_pkt.src_ip][arp_pkt.dst_ip]["arp"] = 0
                    self.directionTtl[arp_pkt.dst_ip][arp_pkt.src_ip]["arp"] = 0
                    return
                if self.directionTtl[arp_pkt.dst_ip][arp_pkt.src_ip]["arp"] <= 0:
                    self.directionTtl[arp_pkt.src_ip][arp_pkt.dst_ip]["arp"] = 0
                    self.directionTtl[arp_pkt.dst_ip][arp_pkt.src_ip]["arp"] = 0
                    return

                if arp_pkt.opcode == arp.ARP_REPLY and arp_pkt.dst_ip == my_ip and in_port == 4:
                    self.directionTtl[arp_pkt.src_ip][arp_pkt.dst_ip]["arp"] -= 1
                    self.directionTtl[arp_pkt.dst_ip][arp_pkt.src_ip]["arp"] -= 1

        elif ipv:
            if my_ip in self.directionTtl:
                found = any(i is True for i in [k == ipv.dst for k in self.directionTtl[my_ip]])
            elif ipv.dst_ip in self.directionTtl:
                found = any(i is True for i in [k == my_ip for k in self.directionTtl[ipv.dst_ip]])

        #print(found, self.directionTtl)
        if mplsH:
            if in_port == 4:
                for label in labels:
                    src_ip = "10.0.0." + str(label)
                    calcTtl = len(labels) - labels.index(label)
                    mode = False

                    if src_ip not in self.directionTtl or my_ip not in self.directionTtl[src_ip]:
                        self.directionTtl.setdefault(src_ip, {})
                        self.directionTtl[src_ip].setdefault(my_ip, {})
                        self.directionTtl[src_ip][my_ip].setdefault("ttl", calcTtl)
                        self.directionTtl[src_ip][my_ip].setdefault("arp", 0)

                        self.directionTtl.setdefault(my_ip, {})
                        self.directionTtl[my_ip].setdefault(src_ip, {})
                        self.directionTtl[my_ip][src_ip].setdefault("ttl", calcTtl)
                        self.directionTtl[my_ip][src_ip].setdefault("arp", 0)
                        mode = True

                    if self.directionTtl[src_ip][my_ip]["ttl"] > calcTtl:
                        self.directionTtl[src_ip][my_ip]["ttl"] = calcTtl
                        self.directionTtl[my_ip][src_ip]["ttl"] = calcTtl
                        mode = True

                    if mode:
                        out_port = ofproto.OFPP_FLOOD
                        actions = [parser.OFPActionSetNwTtl(calcTtl), parser.OFPActionOutput(out_port, 0)]
                        match = parser.OFPMatch(in_port=1, ipv4_dst=my_ip, eth_type=ether.ETH_TYPE_IP)
                        self.mod_flow(self.dpid_host[label]["datapath"], 2, match, actions, True)

                        match = parser.OFPMatch(in_port=1, ipv4_dst=src_ip, eth_type=ether.ETH_TYPE_IP)
                        self.mod_flow(datapath, 2, match, actions, True)

                        tmpSwitch = [k for k in self.dpid_host if k not in labels]

                        for notIn in tmpSwitch:
                            actions = []
                            match = parser.OFPMatch(in_port=4, ipv4_src=my_ip, ipv4_dst=src_ip, eth_type=ether.ETH_TYPE_IP)
                            self.mod_flow(self.dpid_host[notIn]["datapath"], 3, match, actions, True)

                            match = parser.OFPMatch(in_port=4, ipv4_src=src_ip, ipv4_dst=my_ip, eth_type=ether.ETH_TYPE_IP)
                            self.mod_flow(self.dpid_host[notIn]["datapath"], 3, match, actions, True)

        if in_port == 1:
            self.dpid_host[dpid]["host"] = src

        '''if dst != self.dpid_host[dpid]["host"] and not isToBrdMltOf:
            if in_port == 1:
                out_port = ofproto.OFPP_FLOOD
            else:
                out_port = ofproto.OFPP_IN_PORT
        else :'''

        for out_port in [ofproto.OFPP_IN_PORT, ofproto.OFPP_FLOOD]:
            actions = [parser.OFPActionOutput(out_port, 0)]
            if not found:
                actions = [parser.OFPActionPushMpls(), parser.OFPActionSetField(mpls_label=dpid), parser.OFPActionOutput(out_port, 0)]

            if mplsH:
                actions = [parser.OFPActionPushMpls(), parser.OFPActionSetField(mpls_label=dpid), parser.OFPActionSetMplsTtl(len(self.dpid_host) + 1), parser.OFPActionOutput(out_port, 0)]

            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)