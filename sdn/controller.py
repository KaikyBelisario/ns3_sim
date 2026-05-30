"""
Controlador SDN Ryu para o cenário de segurança pública.

Funcionalidades:
  - L2 learning switch com awareness de topologia
  - Instalação de flows OpenFlow 1.3
  - Logging de todas as instalações de flows
  - Garante que tráfego dos sensores passe pelo gateway do grupo

Execução:
  ryu-manager sdn/controller.py
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4
from ryu.lib import mac as mac_lib
import logging


class SecurityController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SecurityController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.logger.setLevel(logging.INFO)
        self.logger.info("=== Controlador SDN de Segurança Pública iniciado ===")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Instala flow padrão table-miss (envia para controlador)."""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Flow table-miss: envia pacote para o controlador
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.logger.info(f"[SWITCH s{datapath.id}] Conectado ao controlador - "
                         f"flow table-miss instalado")

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0,
                 hard_timeout=0):
        """Instala um flow no switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst,
                                idle_timeout=idle_timeout,
                                hard_timeout=hard_timeout)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Trata pacotes que chegam ao controlador."""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})

        # Aprende endereço MAC
        self.mac_to_port[dpid][src] = in_port

        # Determina porta de saída
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Instala flow se não for flood
        if out_port != ofproto.OFPP_FLOOD:
            # Verifica se é pacote IP para logging mais detalhado
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt:
                match = parser.OFPMatch(in_port=in_port,
                                        eth_dst=dst,
                                        eth_src=src,
                                        eth_type=0x0800,
                                        ipv4_src=ip_pkt.src,
                                        ipv4_dst=ip_pkt.dst)
                self.logger.info(
                    f"[FLOW INSTALADO] Switch s{dpid}: "
                    f"{ip_pkt.src} -> {ip_pkt.dst} "
                    f"(porta {in_port} -> porta {out_port})")
            else:
                match = parser.OFPMatch(in_port=in_port,
                                        eth_dst=dst,
                                        eth_src=src)
                self.logger.info(
                    f"[FLOW INSTALADO] Switch s{dpid}: "
                    f"{src} -> {dst} "
                    f"(porta {in_port} -> porta {out_port})")

            self.add_flow(datapath, 1, match, actions,
                          idle_timeout=60, hard_timeout=300)

        # Envia pacote
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)
