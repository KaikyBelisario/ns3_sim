# Projeto: Ambiente Integrado SDN/NFV com Simulação NS-3 — Segurança Pública

## Visão Geral

Este projeto implementa um ambiente integrado de redes contendo **SDN (Software-Defined Networking)**, **NFV (Network Functions Virtualization)** e **simulação de desempenho no NS-3**, aplicado ao cenário de **segurança pública urbana**.

## Cenário

Uma rede de sensores para segurança pública composta por:

| Grupo | Tipo de Sensor | Quantidade | Gateway |
|-------|---------------|------------|---------|
| 1 | Câmeras de vigilância | 3 | GW1 (VNF) |
| 2 | Sensores de tiros/incêndio | 3 | GW2 (VNF) |
| 3 | Bodycams policiais | 3 | GW3 (VNF) |

Todo tráfego dos sensores passa obrigatoriamente pelo gateway (VNF) do seu respectivo grupo antes de chegar ao **servidor central**.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTROLADOR SDN (Ryu)                         │
│                      porta 6633                                  │
└──────────┬──────────────┬──────────────┬──────────────┬─────────┘
           │              │              │              │
      ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
      │ Switch  │   │ Switch  │   │ Switch  │   │ Switch  │
      │ s1 (G1) │   │ s2 (G2) │   │ s3 (G3) │   │ s4 Core │
      └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
           │              │              │              │
     ┌─────┴─────┐  ┌────┴─────┐  ┌────┴─────┐       │
     │ cam1,2,3  │  │ gun1,2,3 │  │body1,2,3 │       │
     │10.0.1.1-3 │  │10.0.2.1-3│  │10.0.3.1-3│       │
     └─────┬─────┘  └────┬─────┘  └────┬─────┘       │
           │              │              │              │
      ┌────▼────┐   ┌────▼────┐   ┌────▼────┐        │
      │  GW1    │   │  GW2    │   │  GW3    │        │
      │  VNF    │───│  VNF    │───│  VNF    │────────┤
      │iptables │   │iptables │   │iptables │        │
      └─────────┘   └─────────┘   └─────────┘        │
                                                 ┌────▼────┐
                                                 │ Servidor│
                                                 │10.0.0.100│
                                                 └─────────┘
```

## Componentes

### 1. Simulação NS-3 (Desempenho)

- Simulação em C++ modelando o cenário com métricas de throughput, delay, jitter e perda de pacotes
- Interface web Flask para executar simulações com diferentes parâmetros
- Resultados armazenados em SQLite

### 2. SDN — Controlador Ryu

- Controlador OpenFlow 1.3 em Python
- Gerencia 4 switches OpenFlow (Mininet/OVS)
- Instala flows dinamicamente com logging
- Garante encaminhamento correto do tráfego através dos gateways

### 3. NFV — Gateways Virtualizados (VNFs)

- 3 gateways implementados como hosts Mininet com IP forwarding
- Cada gateway executa **iptables** como função de rede virtualizada:
  - **LOG**: Registra todo tráfego que transita pelo gateway
  - **FORWARD**: Encaminha pacotes entre sensor e servidor
  - **DROP**: Capacidade de bloquear tráfego de um grupo inteiro
- Demonstra o conceito de NFV com funções de firewall/logging virtualizadas

### 4. Emulação de Rede — Mininet + Open vSwitch

- Topologia emulada com Mininet usando switches OVS reais
- Permite uso de ferramentas padrão: `ping`, `iperf`, `ovs-ofctl`, `iptables`
- Ideal para demonstrações ao vivo

## Endereçamento IP

| Rede | Subnet | Hosts |
|------|--------|-------|
| Grupo 1 (Câmeras) | 10.0.1.0/24 | cam1-3: .1-.3, gw1: .10 |
| Grupo 2 (Tiros) | 10.0.2.0/24 | gun1-3: .1-.3, gw2: .10 |
| Grupo 3 (Bodycams) | 10.0.3.0/24 | body1-3: .1-.3, gw3: .10 |
| Core | 10.0.0.0/24 | gw1: .1, gw2: .2, gw3: .3, server: .100 |

## Tecnologias Utilizadas

- **NS-3 3.47** — Simulação de desempenho de rede
- **Mininet** — Emulação de rede com namespaces Linux
- **Open vSwitch** — Switches OpenFlow virtuais
- **Ryu** — Controlador SDN (Python)
- **iptables** — VNF de firewall/logging
- **Flask** — Dashboard web para simulações
- **Docker** — Containerização do ambiente completo
- **SQLite** — Armazenamento de resultados
