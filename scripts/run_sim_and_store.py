import subprocess
import re
import sqlite3
import sys
import os

DB_PATH = "/workspace/ns3_seguranca.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS simulacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            delay_config TEXT,
            datarate_config TEXT,
            throughput REAL,
            latency REAL,
            jitter REAL,
            packet_loss REAL
        )
    ''')
    conn.commit()
    conn.close()

def run_simulation(delay, banda):
    print(f"Executando NS-3 com Delay={delay} e Banda={banda}...")
    
    # Executa o comando do NS-3 unificando as saídas de log e erro
    cmd = f"/opt/ns-3/ns3 run 'scratch/simulacao-seguranca --delayGateway={delay} --dataRateGateway={banda}'"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd="/opt/ns-3")
    
    output = result.stdout
    print(output) # Log no terminal do docker
    
    # Regex para capturar os outputs gerados pelo nosso script C++
    try:
        throughput = float(re.search(r"Throughput Médio da Rede:\s*([\d.]+)", output).group(1))
        latency = float(re.search(r"Latencia \(Delay\) Media\s*:\s*([\d.]+)", output).group(1))
        jitter = float(re.search(r"Jitter Medio\s*:\s*([\d.]+)", output).group(1))
        packet_loss = float(re.search(r"Packet Loss \(Perda\)\s*:\s*([\d.]+)", output).group(1))
        
        # Salva no SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO simulacoes (delay_config, datarate_config, throughput, latency, jitter, packet_loss)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (delay, banda, throughput, latency, jitter, packet_loss))
        conn.commit()
        conn.close()
        print("Métricas salvas com sucesso no SQLite!")
    except AttributeError:
        print("Erro ao parsear as métricas do NS-3. Verifique o output do script C++.")

if __name__ == "__main__":
    init_db()
    if len(sys.argv) > 2:
        run_simulation(sys.argv[1], sys.argv[2])
    else:
        # Cenário padrão inicial
        run_simulation("20ms", "10Mbps")