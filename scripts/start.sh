#!/usr/bin/env bash
set -e
# Executa uma simulação padrão na primeira vez
python3 /workspace/scripts/run_sim_and_store.py 20ms 10Mbps
# Inicia o servidor Flask
python3 /workspace/webapp/app.py