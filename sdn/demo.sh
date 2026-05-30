#!/usr/bin/env bash
# Script de demonstração ao vivo do ambiente SDN/NFV
# Executa as validações exigidas na apresentação

WORKSPACE=${WORKSPACE:-/workspace}
SEPARATOR="============================================"

echo "$SEPARATOR"
echo "  DEMONSTRAÇÃO SDN/NFV - Segurança Pública"
echo "$SEPARATOR"
echo ""

# 1. Verifica controlador SDN ativo
echo ">>> [1/5] Controlador SDN ativo"
echo "$SEPARATOR"
if pgrep -f "ryu-manager" > /dev/null; then
    echo "STATUS: Ryu controller ATIVO"
    echo "PID: $(pgrep -f ryu-manager)"
    echo ""
    echo "Últimas linhas do log (instalação de flows):"
    tail -20 /var/log/ryu.log 2>/dev/null | grep -i "flow\|conectado\|switch" || echo "(aguardando flows)"
else
    echo "ERRO: Controlador Ryu não está rodando!"
fi
echo ""

# 2. Comunicação sensores <-> servidor
echo ">>> [2/5] Comunicação entre sensores e servidor"
echo "$SEPARATOR"
echo "Ping cam1 (Grupo 1) -> servidor:"
ip netns exec cam1 ping -c 3 10.0.0.100 2>/dev/null || echo "  [FALHA] cam1 -> servidor"
echo ""
echo "Ping gun1 (Grupo 2) -> servidor:"
ip netns exec gun1 ping -c 3 10.0.0.100 2>/dev/null || echo "  [FALHA] gun1 -> servidor"
echo ""
echo "Ping body1 (Grupo 3) -> servidor:"
ip netns exec body1 ping -c 3 10.0.0.100 2>/dev/null || echo "  [FALHA] body1 -> servidor"
echo ""

# 3. Tabela de fluxos OpenFlow
echo ">>> [3/5] Tabela de fluxos (ovs-ofctl dump-flows)"
echo "$SEPARATOR"
for sw in s1 s2 s3 s4; do
    echo "--- Switch $sw ---"
    ovs-ofctl -O OpenFlow13 dump-flows $sw 2>/dev/null || echo "  [ERRO] Não foi possível ler flows de $sw"
    echo ""
done

# 4. Funcionamento das VNFs
echo ">>> [4/5] Funcionamento das VNFs (regras iptables nos gateways)"
echo "$SEPARATOR"
for i in 1 2 3; do
    echo "--- Gateway gw${i} (Grupo ${i}) ---"
    ip netns exec "gw${i}" iptables -L FORWARD -v -n 2>/dev/null || echo "  [ERRO] Não foi possível ler iptables de gw${i}"
    echo ""
done

# 5. Alteração de comportamento - Bloqueio do Grupo 2
echo ">>> [5/5] Alteração de comportamento - Bloqueio do Grupo 2"
echo "$SEPARATOR"
echo ""
echo "--- ANTES do bloqueio: ping gun1 -> servidor ---"
ip netns exec gun1 ping -c 2 10.0.0.100 2>/dev/null || echo "  [FALHA]"
echo ""

echo "Aplicando BLOQUEIO no gateway gw2 (DROP todo tráfego do Grupo 2)..."
ip netns exec gw2 iptables -I FORWARD 1 -s 10.0.2.0/24 -j DROP
ip netns exec gw2 iptables -I FORWARD 1 -d 10.0.2.0/24 -j DROP
echo "[OK] Regras DROP inseridas em gw2"
echo ""

echo "--- DEPOIS do bloqueio: ping gun1 -> servidor ---"
ip netns exec gun1 ping -c 3 -W 2 10.0.0.100 2>/dev/null || echo "  [BLOQUEADO] gun1 não consegue alcançar o servidor"
echo ""

echo "--- Verificando que outros grupos continuam funcionando ---"
echo "Ping cam1 (Grupo 1) -> servidor:"
ip netns exec cam1 ping -c 2 10.0.0.100 2>/dev/null || echo "  [FALHA]"
echo ""

echo "--- Removendo bloqueio ---"
ip netns exec gw2 iptables -D FORWARD -s 10.0.2.0/24 -j DROP
ip netns exec gw2 iptables -D FORWARD -d 10.0.2.0/24 -j DROP
echo "[OK] Bloqueio removido"
echo ""

echo "--- APÓS remoção: ping gun1 -> servidor ---"
ip netns exec gun1 ping -c 2 10.0.0.100 2>/dev/null || echo "  [FALHA]"
echo ""

echo "$SEPARATOR"
echo "  DEMONSTRAÇÃO CONCLUÍDA"
echo "$SEPARATOR"
