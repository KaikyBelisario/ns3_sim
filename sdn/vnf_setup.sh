#!/usr/bin/env bash
# Configuração das VNFs (iptables) nos gateways
# Uso: vnf_setup.sh <gateway_name> <group_number>
# Exemplo: vnf_setup.sh gw1 1

set -e

GW_NAME=$1
GROUP_NUM=$2
SUBNET="10.0.${GROUP_NUM}.0/24"

echo "=== Configurando VNF no gateway ${GW_NAME} (Grupo ${GROUP_NUM}) ==="

# Habilita IP forwarding
ip netns exec $GW_NAME sysctl -w net.ipv4.ip_forward=1 2>/dev/null || true

# Limpa regras anteriores
ip netns exec $GW_NAME iptables -F FORWARD 2>/dev/null || true
ip netns exec $GW_NAME iptables -F INPUT 2>/dev/null || true

# Regra de LOG: registra todo tráfego que passa pelo gateway
ip netns exec $GW_NAME iptables -A FORWARD \
    -s $SUBNET \
    -j LOG --log-prefix "[VNF-${GW_NAME}-FWD] " --log-level 4

ip netns exec $GW_NAME iptables -A FORWARD \
    -d $SUBNET \
    -j LOG --log-prefix "[VNF-${GW_NAME}-RET] " --log-level 4

# Regra ACCEPT: permite tráfego normalmente
ip netns exec $GW_NAME iptables -A FORWARD -j ACCEPT

echo "[OK] VNF ${GW_NAME}: LOG + FORWARD ativo para subnet ${SUBNET}"
