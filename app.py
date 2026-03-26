from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "banco_master3_secret"

# =========================
# 🔹 BANCO DE DADOS
# =========================
def conectar():
    return sqlite3.connect('banco.db')

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha TEXT,
        saldo REAL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        tipo TEXT,
        valor REAL,
        data_hora TEXT
    )
    ''')

    conn.commit()
    conn.close()

def criar_admin():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE usuario='admin'")
    if not cursor.fetchone():
        senha = generate_password_hash("123")
        cursor.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", ("admin", senha, 1000))
        conn.commit()

    conn.close()

criar_tabelas()
criar_admin()

# =========================
# 🔹 ROTAS
# =========================

@app.route('/')
def home():
    return redirect('/login')

# -------------------------
# LOGIN
# -------------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM usuarios WHERE usuario=?", (usuario,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado and check_password_hash(resultado[0], senha):
            session['usuario'] = usuario
            return redirect('/dashboard')
        else:
            flash("Usuário ou senha inválidos")

    return render_template('login.html')

# -------------------------
# CADASTRO
# -------------------------
@app.route('/cadastro', methods=['GET','POST'])
def cadastro():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = generate_password_hash(request.form['senha'])

        conn = conectar()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", (usuario, senha, 0))
            conn.commit()
        except:
            flash("Usuário já existe")

        conn.close()
        return redirect('/login')

    return render_template('cadastro.html')

# -------------------------
# DASHBOARD (COM GRÁFICO)
# -------------------------
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect('/login')

    usuario = session['usuario']

    conn = conectar()
    cursor = conn.cursor()

    # saldo
    cursor.execute("SELECT saldo FROM usuarios WHERE usuario=?", (usuario,))
    saldo = cursor.fetchone()[0]

    # depósitos
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE usuario=? AND tipo='Depósito'", (usuario,))
    total_depositos = cursor.fetchone()[0] or 0

    # saques
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE usuario=? AND tipo='Saque'", (usuario,))
    total_saques = cursor.fetchone()[0] or 0

    conn.close()

    return render_template(
        'dashboard.html',
        usuario=usuario,
        saldo=saldo,
        total_depositos=total_depositos,
        total_saques=total_saques
    )

# -------------------------
# DEPÓSITO
# -------------------------
@app.route('/depositar', methods=['POST'])
def depositar():
    valor = float(request.form['valor'])
    usuario = session['usuario']
    data = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (valor, usuario))
    cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'Depósito', ?, ?)", (usuario, valor, data))

    conn.commit()
    conn.close()

    return redirect('/dashboard')

# -------------------------
# SAQUE
# -------------------------
@app.route('/sacar', methods=['POST'])
def sacar():
    valor = float(request.form['valor'])
    usuario = session['usuario']
    data = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT saldo FROM usuarios WHERE usuario=?", (usuario,))
    saldo = cursor.fetchone()[0]

    if valor <= saldo:
        cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE usuario=?", (valor, usuario))
        cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'Saque', ?, ?)", (usuario, valor, data))
        conn.commit()
    else:
        flash("Saldo insuficiente")

    conn.close()
    return redirect('/dashboard')

# -------------------------
# TRANSFERÊNCIA
# -------------------------
@app.route('/transferir', methods=['GET','POST'])
def transferir():
    if 'usuario' not in session:
        return redirect('/login')

    if request.method == 'POST':
        origem = session['usuario']
        destino = request.form['destino']
        valor = float(request.form['valor'])
        data = datetime.now().strftime("%d/%m/%Y %H:%M")

        conn = conectar()
        cursor = conn.cursor()

        # saldo origem
        cursor.execute("SELECT saldo FROM usuarios WHERE usuario=?", (origem,))
        saldo = cursor.fetchone()[0]

        # verifica destino
        cursor.execute("SELECT * FROM usuarios WHERE usuario=?", (destino,))
        existe = cursor.fetchone()

        if not existe:
            flash("Usuário destino não existe")
            return redirect('/transferir')

        if valor > saldo:
            flash("Saldo insuficiente")
            return redirect('/transferir')

        # transferência
        cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE usuario=?", (valor, origem))
        cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (valor, destino))

        cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'Transferência enviada', ?, ?)", (origem, valor, data))
        cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'Transferência recebida', ?, ?)", (destino, valor, data))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template('transferencia.html')

# -------------------------
# EXTRATO
# -------------------------
@app.route('/extrato')
def extrato():
    usuario = session['usuario']

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT tipo, valor, data_hora FROM transacoes WHERE usuario=?", (usuario,))
    dados = cursor.fetchall()

    conn.close()

    return render_template('extrato.html', dados=dados)

# -------------------------
# LOGOUT
# -------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -------------------------
# START
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)