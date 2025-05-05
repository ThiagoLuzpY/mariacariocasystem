import os
import sqlite3

def conectar():
    pasta_local = os.path.join(os.path.dirname(__file__), '..', 'database')
    pasta_local = os.path.abspath(pasta_local)

    if not os.path.exists(pasta_local):
        os.makedirs(pasta_local)

    return sqlite3.connect(os.path.join(pasta_local, 'loja.db'))

def criar_tabelas():
    con = conectar()
    cursor = con.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT,  -- SKU base da família
        sku_variacao TEXT,  -- SKU completo da variação (ex: MCC001-4)
        nome_produto TEXT NOT NULL,
        descricao TEXT,
        preco_custo REAL NOT NULL,
        preco_venda REAL,
        quantidade INTEGER DEFAULT 0,
        data_compra TEXT NOT NULL
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER,
    id_variacao INTEGER,
    sku_variacao TEXT,  -- SKU completo da variação (ex: MCC001-4)
    nome_produto TEXT,
    variacao_escolhida TEXT,
    quantidade INTEGER,
    valor_venda REAL,
    forma_pagamento TEXT,
    data_venda TEXT,
    vendedor TEXT,
    cliente_id INTEGER,
    nome_cliente TEXT,
    estoque_restante INTEGER,
    FOREIGN KEY(produto_id) REFERENCES estoque(id),
    FOREIGN KEY(id_variacao) REFERENCES variacoes_estoque(id),
    FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        telefone TEXT,
        email TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT,
        valor REAL,
        data_despesa TEXT
    )''')

    # ⚠️ NOVA TABELA VARIAÇÕES
    cursor.execute('DROP TABLE IF EXISTS variacoes_estoque')
    cursor.execute('''
    CREATE TABLE variacoes_estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        sku_variacao TEXT,  -- SKU completo da variação (ex: MCC001-4)
        tipo_variacao TEXT NOT NULL,
        valor_variacao TEXT NOT NULL,
        qtd_variacao INTEGER DEFAULT 0,
        qtd_variacao_inicial INTEGER DEFAULT 0,
        FOREIGN KEY(produto_id) REFERENCES estoque(id)
    )''')

    con.commit()
    con.close()

if __name__ == "__main__":
    criar_tabelas()
