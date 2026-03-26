from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "banco_master3")

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
        saldo REAL,
        chave_pix TEXT
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
        cursor.execute(
            "INSERT INTO usuarios (usuario, senha, saldo, chave_pix) VALUES (?, ?, ?, ?)",
            ("admin", senha, 1000, "admin@pix")
        )
        conn.commit()

    conn.close()

criar_tabelas()
criar_admin()

# LOGIN
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

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect('/login')

    usuario = session['usuario']

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT saldo FROM usuarios WHERE usuario=?", (usuario,))
    saldo = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE usuario=?", (usuario,))
    total = cursor.fetchone()[0] or 0

    conn.close()

    return render_template('dashboard.html', usuario=usuario, saldo=saldo, total=total)

# DEPÓSITO
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

# SAQUE
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

# PIX
@app.route('/pix', methods=['GET','POST'])
def pix():
    if 'usuario' not in session:
        return redirect('/login')

    if request.method == 'POST':
        chave = request.form['chave']
        valor = float(request.form['valor'])
        origem = session['usuario']
        data = datetime.now().strftime("%d/%m/%Y %H:%M")

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("SELECT usuario FROM usuarios WHERE usuario=? OR chave_pix=?", (chave, chave))
        destino = cursor.fetchone()

        if not destino:
            flash("Chave PIX não encontrada")
            return redirect('/pix')

        destino = destino[0]

        cursor.execute("SELECT saldo FROM usuarios WHERE usuario=?", (origem,))
        saldo = cursor.fetchone()[0]

        if valor > saldo:
            flash("Saldo insuficiente")
            return redirect('/pix')

        cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE usuario=?", (valor, origem))
        cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (valor, destino))

        cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'PIX enviado', ?, ?)", (origem, valor, data))
        cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'PIX recebido', ?, ?)", (destino, valor, data))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template('pix.html')

# RELATÓRIO
@app.route('/relatorio')
def relatorio():
    if 'usuario' not in session:
        return redirect('/login')

    usuario = session['usuario']

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM transacoes WHERE usuario=?", (usuario,))
    total_operacoes = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE usuario=?", (usuario,))
    total_movimentado = cursor.fetchone()[0] or 0

    conn.close()

    return render_template('relatorio.html', total_operacoes=total_operacoes, total_movimentado=total_movimentado)

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)