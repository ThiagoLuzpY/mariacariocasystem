import streamlit as st
import pandas as pd
from modules.database import conectar
from datetime import datetime, timedelta

def app():
    st.header("🎖️ Sistema Exclusivo de Premiações")

    con = conectar()
    cursor = con.cursor()

    menu_premiacoes = st.sidebar.radio("Menu Premiações", ["Pontuar Clientes", "Resgatar Pontos", "Ranking Clientes"])

    if menu_premiacoes == "Pontuar Clientes":
        st.subheader("Pontuar Clientes Automaticamente")

        vendas = pd.read_sql('''
        SELECT vendas.id, vendas.valor_venda, clientes.nome, clientes.id AS cliente_id, vendas.data_venda
        FROM vendas
        JOIN clientes ON vendas.cliente_id = clientes.id
        WHERE vendas.data_venda >= date('now','-30 days')
        ''', con)

        vendas["pontos_ganhos"] = vendas["valor_venda"] // 50  # 1 ponto a cada R$ 50 gastos
        vendas["validade"] = (pd.to_datetime(vendas["data_venda"]) + timedelta(days=30)).dt.date

        st.dataframe(vendas, use_container_width=True)

        if st.button("Salvar Pontuação"):
            for _, row in vendas.iterrows():
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS pontos_clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER,
                    pontos INTEGER,
                    data_compra TEXT,
                    validade TEXT,
                    resgatado INTEGER DEFAULT 0
                )''')

                cursor.execute('''
                INSERT INTO pontos_clientes (cliente_id, pontos, data_compra, validade)
                VALUES (?, ?, ?, ?)''', (row["cliente_id"], row["pontos_ganhos"], row["data_venda"], row["validade"]))
            con.commit()
            st.success("Pontuação salva com sucesso!")

    elif menu_premiacoes == "Resgatar Pontos":
        st.subheader("Resgate de Pontos por Clientes")

        clientes = pd.read_sql("SELECT id, nome FROM clientes", con)
        cliente_nome = st.selectbox("Cliente", clientes["nome"])
        cliente_id = clientes.loc[clientes["nome"] == cliente_nome, "id"].iloc[0]

        pontos_disponiveis = pd.read_sql('''
        SELECT SUM(pontos) AS pontos FROM pontos_clientes
        WHERE cliente_id=? AND validade >= date('now') AND resgatado=0
        ''', con, params=(cliente_id,))

        pontos = pontos_disponiveis["pontos"].iloc[0] or 0
        st.write(f"Pontos disponíveis: {pontos}")

        valor_resgate = st.number_input("Valor da compra atual", min_value=0.0, step=0.1)
        pontos_necessarios = valor_resgate // 2  # Regra: Para usar pontos, precisa ter 2x o valor em pontos (1 ponto vale R$1)

        if pontos >= pontos_necessarios and pontos_necessarios > 0:
            desconto = pontos_necessarios * 0.50  # cada ponto vale R$0,50
            st.write(f"O cliente pode usar até {pontos_necessarios} pontos para desconto de R${desconto:.2f}")

            if st.button("Confirmar Resgate"):
                cursor.execute('''
                UPDATE pontos_clientes SET resgatado=1 WHERE cliente_id=? AND resgatado=0
                AND validade >= date('now') LIMIT ?''', (cliente_id, pontos_necessarios))
                con.commit()
                st.success(f"Resgatado com sucesso! Desconto concedido: R${desconto:.2f}")
        else:
            st.warning("Pontos insuficientes para resgate nesta compra.")

    elif menu_premiacoes == "Ranking Clientes":
        st.subheader("Ranking dos Clientes Mais Pontuados")

        ranking = pd.read_sql('''
        SELECT clientes.nome, SUM(pontos_clientes.pontos) AS total_pontos
        FROM pontos_clientes
        JOIN clientes ON pontos_clientes.cliente_id = clientes.id
        GROUP BY clientes.nome
        ORDER BY total_pontos DESC LIMIT 10
        ''', con)

        st.dataframe(ranking, use_container_width=True)

        if st.button("Exportar Ranking"):
            ranking.to_excel("ranking_clientes.xlsx", index=False)
            st.success("Ranking exportado com sucesso!")

    con.close()
