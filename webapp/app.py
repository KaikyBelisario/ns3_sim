from flask import Flask, render_template, request, redirect
import sqlite3
import subprocess

app = Flask(__name__)
DB_PATH = "/workspace/ns3_seguranca.sqlite"

def get_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulacoes ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.route('/')
def index():
    historico = get_history()
    return render_template('index.html', historico=historico)

@app.route('/simular', methods=['POST'])
def simular():
    delay = request.form.get('delay')
    banda = request.form.get('banda')
    
    # Chama o script Python para rodar a simulação em background e salvar no banco
    subprocess.run(["python3", "/workspace/scripts/run_sim_and_store.py", delay, banda])
    
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)