from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "banco_master3_secret"

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

@app.route('/')
def home():
    return redirect('/login')

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
            flash("Login inválido")

    return render_template('login.html')

@app.route('/cadastro', methods=['GET','POST'])
def cadastro():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = generate_password_hash(request.form['senha'])

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", (usuario, senha, 0))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM usuarios WHERE usuario=?", (session['usuario'],))
    saldo = cursor.fetchone()[0]
    conn.close()

    return render_template('dashboard.html', saldo=saldo, usuario=session['usuario'])

@app.route('/depositar', methods=['POST'])
def depositar():
    valor = float(request.form['valor'])
    data = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE usuario=?", (valor, session['usuario']))
    cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'Depósito', ?, ?)", (session['usuario'], valor, data))

    conn.commit()
    conn.close()

    return redirect('/dashboard')

@app.route('/sacar', methods=['POST'])
def sacar():
    valor = float(request.form['valor'])
    data = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT saldo FROM usuarios WHERE usuario=?", (session['usuario'],))
    saldo = cursor.fetchone()[0]

    if valor <= saldo:
        cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE usuario=?", (valor, session['usuario']))
        cursor.execute("INSERT INTO transacoes VALUES (NULL, ?, 'Saque', ?, ?)", (session['usuario'], valor, data))
        conn.commit()

    conn.close()
    return redirect('/dashboard')

@app.route('/extrato')
def extrato():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT tipo, valor, data_hora FROM transacoes WHERE usuario=?", (session['usuario'],))
    dados = cursor.fetchall()

    conn.close()
    return render_template('extrato.html', dados=dados)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)