#!/usr/bin/env bash
# Script de orquestração: inicia todo o ambiente SDN/NFV

WORKSPACE=${WORKSPACE:-/workspace}
SDN_DIR="${WORKSPACE}/sdn"

echo "============================================"
echo "  Iniciando ambiente SDN/NFV"
echo "============================================"

# 1. Inicia o Open vSwitch
echo "[1/4] Iniciando Open vSwitch..."
service openvswitch-switch start
sleep 2
ovs-vsctl --version
echo "[OK] OVS ativo"

# 2. Inicia o controlador Ryu em background
echo "[2/4] Iniciando controlador Ryu..."
ryu-manager "${SDN_DIR}/controller.py" \
    --ofp-tcp-listen-port 6633 \
    --verbose 2>&1 &
RYU_PID=$!
sleep 3

if kill -0 $RYU_PID 2>/dev/null; then
    echo "[OK] Ryu ativo (PID: $RYU_PID)"
else
    echo "[ERRO] Falha ao iniciar Ryu"
fi

# 3. Inicia topologia Mininet em background (já configura VNFs internamente)
echo "[3/3] Criando topologia Mininet e configurando VNFs..."
python3 "${SDN_DIR}/topology.py" --no-cli &
MN_PID=$!
sleep 5
echo "[OK] Topologia Mininet criada e VNFs configuradas"

echo ""
echo "============================================"
echo "  Ambiente SDN/NFV pronto!"
echo "============================================"
echo "  Controlador Ryu: PID $RYU_PID (log: /var/log/ryu.log)"
echo "  Topologia Mininet: PID $MN_PID"
echo "  Execute 'bash ${SDN_DIR}/demo.sh' para demonstração"
echo "============================================"
