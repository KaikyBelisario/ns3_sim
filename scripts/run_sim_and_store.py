import subprocess
import re
import sqlite3
import sys

DB_PATH = "/workspace/ns3_seguranca.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS simulacoes_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            delay_config TEXT, datarate_config TEXT,
            t_geral REAL, l_geral REAL, j_geral REAL, p_geral REAL,
            t_c1 REAL, l_c1 REAL, j_c1 REAL, p_c1 REAL,
            t_c2 REAL, l_c2 REAL, j_c2 REAL, p_c2 REAL,
            t_c3 REAL, l_c3 REAL, j_c3 REAL, p_c3 REAL
        )
    ''')
    conn.commit()
    conn.close()

def parse_line(category, output):
    # Procura a linha específica da categoria e extrai os 4 valores numéricos
    pattern = rf"\[{category}\] Tput:\s*([\d.]+)\s*Mbps \| Delay:\s*([\d.]+)\s*ms \| Jitter:\s*([\d.]+)\s*ms \| Loss:\s*([\d.]+)\s*%"
    match = re.search(pattern, output)
    if match:
        return float(match.group(1)), float(match.group(2)), float(match.group(3)), float(match.group(4))
    return 0.0, 0.0, 0.0, 0.0

def run_simulation(delay, banda):
    print(f"Executando NS-3 com Delay={delay} e Banda={banda}...")
    cmd = f"/opt/ns-3/ns3 run 'scratch/simulacao-seguranca --delayGateway={delay} --dataRateGateway={banda}'"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd="/opt/ns-3")
    
    output = result.stdout
    print(output)
    
    try:
        tg, lg, jg, pg = parse_line("Geral", output)
        t1, l1, j1, p1 = parse_line("C1-Cameras", output)
        t2, l2, j2, p2 = parse_line("C2-Sensores", output)
        t3, l3, j3, p3 = parse_line("C3-Bodycams", output)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO simulacoes_v2 (
                delay_config, datarate_config,
                t_geral, l_geral, j_geral, p_geral,
                t_c1, l_c1, j_c1, p_c1,
                t_c2, l_c2, j_c2, p_c2,
                t_c3, l_c3, j_c3, p_c3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (delay, banda, tg, lg, jg, pg, t1, l1, j1, p1, t2, l2, j2, p2, t3, l3, j3, p3))
        conn.commit()
        conn.close()
        print("Métricas detalhadas salvas no SQLite!")
    except Exception as e:
        print(f"Erro ao parsear as métricas: {e}")

if __name__ == "__main__":
    init_db()
    if len(sys.argv) > 2:
        run_simulation(sys.argv[1], sys.argv[2])
    else:
        run_simulation("20ms", "10Mbps")