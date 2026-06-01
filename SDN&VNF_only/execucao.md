## Passo 1: Iniciar o Controlador SDN (Ryu) via Docker
sudo docker run -it --rm -p 6633:6633 -p 8080:8080 osrg/ryu ryu-manager ryu.app.simple_switch_13

## Passo 2: Iniciar a Topologia Mininet
Em um **segundo terminal**, execute o script da topologia criado:
sudo python3 topologia_seguranca.py

## Passo 3: Comunicação Sensores -> Servidor (Passando pelo VNF)
No prompt do Mininet (`mininet>`), teste a comunicação de um sensor de cada grupo para o servidor central:
mininet> cam1 ping -c 2 server
mininet> fire1 ping -c 2 server
mininet> gps1 ping -c 2 server

## Passo 4: Exibição da Tabela de Fluxos (OpenFlow)
Em um **terceiro terminal** (fora do mininet), rode:
sudo ovs-ofctl -O OpenFlow13 dump-flows s99

## Passo 5: Funcionamento e Alteração de Comportamento do VNF

No prompt do Mininet:
1. Mostre que o gateway está sem bloqueios:
mininet> vnf1 iptables -L

2. Aplique a regra de bloqueio na VNF1 para a cam1 (IP 10.0.1.1):
mininet> vnf1 iptables -A FORWARD -s 10.0.1.1 -j DROP

3. Valide a alteração de comportamento:
mininet> cam1 ping -c 2 server

4. Mostre que a `cam2` continua funcionando perfeitamente:
mininet> cam2 ping -c 2 server