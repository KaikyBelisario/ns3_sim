#!/usr/bin/env python3
"""
Topologia Mininet para o cenário de segurança pública com SDN/NFV.

Arquitetura:
  - 3 grupos de sensores (3 sensores cada)
  - 3 gateways VNF (um por grupo)
  - 1 servidor central
  - 4 switches OpenFlow (1 por grupo + 1 core)
  - 1 controlador Ryu remoto

Endereçamento:
  Grupo 1 (Câmeras):       10.0.1.0/24 (sensores .1-.3, gateway .10)
  Grupo 2 (Tiros/Incêndio): 10.0.2.0/24 (sensores .1-.3, gateway .10)
  Grupo 3 (Bodycams):       10.0.3.0/24 (sensores .1-.3, gateway .10)
  Rede Core:                 10.0.0.0/24 (gateways .1-.3, servidor .100)
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
import sys
import os


def create_topology():
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True
    )

    # Controlador SDN Ryu
    c0 = net.addController('c0', controller=RemoteController,
                           ip='127.0.0.1', port=6633)

    # Switches OpenFlow (1 por grupo + 1 core)
    s1 = net.addSwitch('s1', protocols='OpenFlow13')  # Grupo 1
    s2 = net.addSwitch('s2', protocols='OpenFlow13')  # Grupo 2
    s3 = net.addSwitch('s3', protocols='OpenFlow13')  # Grupo 3
    s4 = net.addSwitch('s4', protocols='OpenFlow13')  # Core

    # Servidor central
    server = net.addHost('server', ip='10.0.0.100/24')
    net.addLink(server, s4, bw=100, delay='1ms')

    # Definição dos grupos
    groups = [
        {'name': 'cam', 'switch': s1, 'gw_name': 'gw1',
         'subnet': '10.0.1', 'gw_core_ip': '10.0.0.1'},
        {'name': 'gun', 'switch': s2, 'gw_name': 'gw2',
         'subnet': '10.0.2', 'gw_core_ip': '10.0.0.2'},
        {'name': 'body', 'switch': s3, 'gw_name': 'gw3',
         'subnet': '10.0.3', 'gw_core_ip': '10.0.0.3'},
    ]

    gateways = []
    sensors = []

    for i, group in enumerate(groups):
        # Gateway (dual-homed: conectado ao switch do grupo e ao switch core)
        gw = net.addHost(group['gw_name'],
                         ip=f"{group['subnet']}.10/24")
        # Link gateway <-> switch do grupo
        net.addLink(gw, group['switch'], bw=10, delay='2ms')
        # Link gateway <-> switch core
        net.addLink(gw, s4, bw=10, delay='5ms')
        gateways.append(gw)

        # 3 sensores por grupo
        for j in range(1, 4):
            sensor_name = f"{group['name']}{j}"
            sensor_ip = f"{group['subnet']}.{j}/24"
            sensor = net.addHost(sensor_name, ip=sensor_ip,
                                 defaultRoute=f"via {group['subnet']}.10")
            net.addLink(sensor, group['switch'], bw=5, delay='5ms')
            sensors.append(sensor)

    net.build()

    # Inicia controlador e switches
    c0.start()
    for sw in [s1, s2, s3, s4]:
        sw.start([c0])

    # Configura gateways (interface core e IP forwarding)
    for i, group in enumerate(groups):
        gw = gateways[i]
        # A segunda interface do gateway é a conexão com o switch core
        # Interface para grupo: gw1-eth0 (10.0.X.10)
        # Interface para core: gw1-eth1 (10.0.0.Y)
        gw.cmd(f"ip addr add {group['gw_core_ip']}/24 dev {gw.name}-eth1")
        gw.cmd("sysctl -w net.ipv4.ip_forward=1")
        # Rota default para o servidor via rede core
        gw.cmd(f"ip route add 10.0.0.0/24 dev {gw.name}-eth1")
        # Rotas para os outros grupos via core
        for j, other_group in enumerate(groups):
            if i != j:
                gw.cmd(f"ip route add {other_group['subnet']}.0/24 via {other_group['gw_core_ip']}")

    # Servidor: rota para cada grupo via gateway correspondente
    server.cmd("ip route add 10.0.1.0/24 via 10.0.0.1")
    server.cmd("ip route add 10.0.2.0/24 via 10.0.0.2")
    server.cmd("ip route add 10.0.3.0/24 via 10.0.0.3")

    # Configura VNFs (iptables) nos gateways
    for i, group in enumerate(groups):
        gw = gateways[i]
        subnet = f"{group['subnet']}.0/24"
        # LOG: registra tráfego que passa pelo gateway
        gw.cmd(f"iptables -A FORWARD -s {subnet} -j LOG --log-prefix '[VNF-{gw.name}-FWD] ' --log-level 4")
        gw.cmd(f"iptables -A FORWARD -d {subnet} -j LOG --log-prefix '[VNF-{gw.name}-RET] ' --log-level 4")
        # ACCEPT: permite tráfego normalmente
        gw.cmd("iptables -A FORWARD -j ACCEPT")
        print(f"[VNF] {gw.name}: iptables LOG+FORWARD configurado para {subnet}")

    # Cria symlinks em /var/run/netns para que 'ip netns exec <host>' funcione
    os.makedirs('/var/run/netns', exist_ok=True)
    for host in net.hosts:
        netns_path = f'/var/run/netns/{host.name}'
        if os.path.lexists(netns_path):
            os.remove(netns_path)
        os.symlink(f'/proc/{host.pid}/ns/net', netns_path)
    print("[VNF] Symlinks /var/run/netns criados para todos os hosts")

    return net


def main():
    setLogLevel('info')
    net = create_topology()

    if '--no-cli' in sys.argv:
        print("=== Topologia SDN/NFV iniciada (modo background) ===")
        print("Sensores: cam1-3, gun1-3, body1-3")
        print("Gateways: gw1, gw2, gw3")
        print("Servidor: server (10.0.0.100)")
        print("Switches: s1 (grupo1), s2 (grupo2), s3 (grupo3), s4 (core)")
        # Mantém rede ativa sem CLI
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            net.stop()
    else:
        print("=== Topologia SDN/NFV iniciada ===")
        print("Sensores: cam1-3, gun1-3, body1-3")
        print("Gateways: gw1, gw2, gw3")
        print("Servidor: server (10.0.0.100)")
        print("Switches: s1 (grupo1), s2 (grupo2), s3 (grupo3), s4 (core)")
        print("Digite 'help' para comandos Mininet")
        CLI(net)
        net.stop()


if __name__ == '__main__':
    main()
