# Guia de Execução do Projeto

## Pré-requisitos

- Docker e Docker Compose instalados
- Sistema operacional Linux (recomendado) ou Docker Desktop (Windows/Mac)
- Pelo menos 4 GB de RAM disponível para o container

## Passo 1: Construir e Iniciar o Container

```bash
cd ns3-seguranca-docker
docker-compose up --build
```

O processo de build instala:
- NS-3.47 (compilação, pode levar alguns minutos)
- Mininet + Open vSwitch
- Controlador SDN Ryu
- Flask + SQLite

Ao finalizar o startup, o container:
1. Executa a simulação NS-3 padrão
2. Inicia o Open vSwitch
3. Inicia o controlador Ryu
4. Cria a topologia Mininet (9 sensores + 3 gateways + 1 servidor)
5. Configura as VNFs (iptables) nos gateways
6. Inicia o dashboard web Flask na porta 5000

## Passo 2: Acessar o Dashboard Web

Abra o navegador em:

```
http://localhost:5000
```

O dashboard permite:
- Visualizar resultados de simulações anteriores
- Executar novas simulações NS-3 com parâmetros customizados (delay, bandwidth)

## Passo 3: Acessar o Container para Demonstração

Em outro terminal, acesse o container:

```bash
docker exec -it ns3-seguranca-dashboard bash
```

## Passo 4: Executar a Demonstração ao Vivo

Dentro do container:

```bash
bash /workspace/sdn/demo.sh
```

Este script executa automaticamente as 5 validações:

### Validação 1 — Controlador SDN Ativo
- Verifica que o Ryu está rodando
- Mostra logs de instalação de flows

### Validação 2 — Comunicação Sensores ↔ Servidor
- Ping de um sensor de cada grupo até o servidor central
- Demonstra que a comunicação passa pelo gateway

### Validação 3 — Tabela de Fluxos OpenFlow
- Executa `ovs-ofctl dump-flows` em todos os switches (s1, s2, s3, s4)
- Mostra as regras instaladas pelo controlador

### Validação 4 — Funcionamento das VNFs
- Exibe regras `iptables` em cada gateway
- Mostra contadores de pacotes (LOG e FORWARD)

### Validação 5 — Alteração de Comportamento (Bloqueio)
- Demonstra ping funcionando para o Grupo 2
- Aplica regra DROP no gateway gw2 (bloqueio do grupo)
- Demonstra que o ping falha após bloqueio
- Verifica que outros grupos continuam funcionando
- Remove o bloqueio e verifica recuperação

## Comandos Úteis (dentro do container)

### Verificar controlador SDN

```bash
# Ver se Ryu está ativo
pgrep -f ryu-manager

# Ver logs do controlador
tail -f /var/log/ryu.log
```

### Verificar flows nos switches

```bash
# Dump de flows em um switch específico
ovs-ofctl -O OpenFlow13 dump-flows s1
ovs-ofctl -O OpenFlow13 dump-flows s4

# Ver todos os switches
ovs-vsctl show
```

### Testar conectividade

```bash
# Ping de sensor para servidor (via namespace)
ip netns exec cam1 ping 10.0.0.100
ip netns exec gun2 ping 10.0.0.100
ip netns exec body3 ping 10.0.0.100
```

### Verificar VNFs (iptables nos gateways)

```bash
# Ver regras do gateway 1
ip netns exec gw1 iptables -L FORWARD -v -n

# Ver logs de tráfego
dmesg | grep "VNF-gw1"
```

### Bloquear/Desbloquear um grupo manualmente

```bash
# Bloquear grupo 2 (sensores de tiros)
ip netns exec gw2 iptables -I FORWARD 1 -s 10.0.2.0/24 -j DROP
ip netns exec gw2 iptables -I FORWARD 1 -d 10.0.2.0/24 -j DROP

# Desbloquear grupo 2
ip netns exec gw2 iptables -D FORWARD -s 10.0.2.0/24 -j DROP
ip netns exec gw2 iptables -D FORWARD -d 10.0.2.0/24 -j DROP
```

### Acessar CLI interativa do Mininet

```bash
python3 /workspace/sdn/topology.py
```

No CLI do Mininet:
```
mininet> pingall
mininet> cam1 ping server
mininet> dump
mininet> links
```

## Passo 5: Simulação NS-3 (Dashboard)

Acesse `http://localhost:5000` e use o formulário para rodar simulações com parâmetros diferentes:
- **Delay do Gateway**: Latência da conexão gateway-servidor (ex: 20ms, 50ms)
- **Bandwidth do Gateway**: Largura de banda gateway-servidor (ex: 10Mbps, 5Mbps)

Os resultados mostram throughput, delay, jitter e perda de pacotes por grupo.

## Estrutura de Arquivos

```
ns3-seguranca-docker/
├── docker-compose.yml       # Orquestração do container
├── Dockerfile               # Build do ambiente (NS-3 + SDN/NFV)
├── scratch/
│   └── simulacao-seguranca.cc  # Simulação NS-3
├── scripts/
│   ├── start.sh             # Script de inicialização geral
│   └── run_sim_and_store.py # Executa simulação e armazena resultados
├── sdn/
│   ├── topology.py          # Topologia Mininet (sensores, gateways, servidor)
│   ├── controller.py        # Controlador SDN Ryu
│   ├── vnf_setup.sh         # Configuração das VNFs (iptables)
│   ├── start_sdn.sh         # Orquestração do ambiente SDN/NFV
│   └── demo.sh              # Script de demonstração ao vivo
├── webapp/
│   ├── app.py               # Dashboard Flask
│   └── templates/
│       └── index.html       # Interface web
└── docs/
    ├── descricao.md          # Descrição do projeto
    └── execucao.md           # Este arquivo
```

## Troubleshooting

| Problema | Solução |
|----------|---------|
| OVS não inicia | Verifique que o container está com `privileged: true` |
| Ryu falha ao conectar | Verifique `/var/log/ryu.log` e se a porta 6633 está livre |
| Ping falha entre hosts | Execute `ovs-ofctl dump-flows` para verificar se há flows instalados |
| Mininet erro "already running" | Execute `mn -c` para limpar estado anterior |
| Container sem permissão | Certifique-se que `privileged: true` está no docker-compose.yml |
