#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch, Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

class GatewayVNF(Node):
    """Nó atuando como VNF (Virtual Network Function) com IP Forwarding"""
    def config(self, **params):
        super(GatewayVNF, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(GatewayVNF, self).terminate()

def run_topology():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)
    
    info('*** [1] Adicionando Controlador SDN (Ryu)\n')
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    info('*** [2] Adicionando Switches OpenFlow\n')
    s1 = net.addSwitch('s1', dpid='1') # Switch das Câmeras
    s2 = net.addSwitch('s2', dpid='2') # Switch dos Sensores de Incêndio
    s3 = net.addSwitch('s3', dpid='3') # Switch dos GPS
    s_core = net.addSwitch('s99', dpid='99') # Switch Core (Central)

    info('*** [3] Adicionando VNFs (Gateways de cada Grupo)\n')
    vnf1 = net.addHost('vnf1', cls=GatewayVNF, ip='10.0.1.254/24')
    vnf2 = net.addHost('vnf2', cls=GatewayVNF, ip='10.0.2.254/24')
    vnf3 = net.addHost('vnf3', cls=GatewayVNF, ip='10.0.3.254/24')

    info('*** [4] Adicionando Servidor Central do COP\n')
    server = net.addHost('server', ip='10.0.99.100/24')

    info('*** [5] Adicionando Sensores (Grupos 1, 2 e 3)\n')
    cams = [net.addHost(f'cam{i}', ip=f'10.0.1.{i}/24', defaultRoute='via 10.0.1.254') for i in range(1, 4)]
    fires = [net.addHost(f'fire{i}', ip=f'10.0.2.{i}/24', defaultRoute='via 10.0.2.254') for i in range(1, 4)]
    bcam = [net.addHost(f'bcam{i}', ip=f'10.0.3.{i}/24', defaultRoute='via 10.0.3.254') for i in range(1, 4)]

    info('*** [6] Criando a Fiação (Links)\n')
    # Sensores -> Switches de Borda
    for cam in cams: net.addLink(cam, s1)
    for fire in fires: net.addLink(fire, s2)
    for bc in bcam: net.addLink(bc, s3)

    # Switches de Borda -> VNFs (Interface eth0)
    net.addLink(s1, vnf1, intfName2='vnf1-eth0', params2={'ip': '10.0.1.254/24'})
    net.addLink(s2, vnf2, intfName2='vnf2-eth0', params2={'ip': '10.0.2.254/24'})
    net.addLink(s3, vnf3, intfName2='vnf3-eth0', params2={'ip': '10.0.3.254/24'})

    # VNFs (Interface eth1) -> Switch Core
    net.addLink(vnf1, s_core, intfName1='vnf1-eth1', params1={'ip': '10.0.99.1/24'})
    net.addLink(vnf2, s_core, intfName1='vnf2-eth1', params1={'ip': '10.0.99.2/24'})
    net.addLink(vnf3, s_core, intfName1='vnf3-eth1', params1={'ip': '10.0.99.3/24'})

    # Switch Core -> Servidor
    net.addLink(s_core, server)

    info('*** [7] Iniciando a Rede\n')
    net.build()
    c0.start()
    for switch in [s1, s2, s3, s_core]:
        switch.start([c0])

    info('*** [8] Configurando Roteamento no Servidor Central\n')
    # O servidor precisa saber como devolver os pacotes para as subredes via interface do VNF no Core
    server.cmd('ip route add 10.0.1.0/24 via 10.0.99.1')
    server.cmd('ip route add 10.0.2.0/24 via 10.0.99.2')
    server.cmd('ip route add 10.0.3.0/24 via 10.0.99.3')

    info('*** [9] Ambiente SDN/NFV de Segurança Pública Pronto!\n')
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_topology()