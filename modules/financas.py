import streamlit as st
import pandas as pd
from modules.database import conectar
import plotly.express as px
from datetime import datetime

def app():
    st.header("📊 Controle Financeiro")

    con = conectar()
    cursor = con.cursor()

    menu_financas = st.sidebar.radio("Menu de Finanças", ["Registrar Despesas", "Visão Geral", "Análise Financeira"])

    if menu_financas == "Registrar Despesas":
        st.subheader("Registrar Nova Despesa")
        descricao = st.text_input("Descrição da Despesa")
        valor = st.number_input("Valor da Despesa", min_value=0.0, step=0.1)
        data_despesa = st.date_input("Data da Despesa", value=datetime.today())

        if st.button("Salvar Despesa"):
            if descricao and valor > 0:
                cursor.execute('''
                INSERT INTO despesas (descricao, valor, data_despesa)
                VALUES (?, ?, ?)''', (descricao, valor, data_despesa))
                con.commit()
                st.success("Despesa registrada com sucesso!")
            else:
                st.error("Descrição e valor são obrigatórios!")

        df_despesas = pd.read_sql("SELECT * FROM despesas", con)
        st.write("### Despesas Registradas")
        st.dataframe(df_despesas, use_container_width=True)

        if st.button("Exportar Despesas para Excel"):
            df_despesas.to_excel("despesas.xlsx", index=False)
            st.success("Exportado com sucesso!")

    elif menu_financas == "Visão Geral":
        st.subheader("Resumo Financeiro Mensal")

        df_vendas = pd.read_sql("SELECT valor_venda, data_venda FROM vendas", con)
        df_despesas = pd.read_sql("SELECT valor, data_despesa FROM despesas", con)

        df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
        df_despesas['data_despesa'] = pd.to_datetime(df_despesas['data_despesa'])

        faturamento = df_vendas.groupby(df_vendas['data_venda'].dt.to_period('M')).sum().reset_index()
        despesas = df_despesas.groupby(df_despesas['data_despesa'].dt.to_period('M')).sum().reset_index()

        faturamento['data_venda'] = faturamento['data_venda'].astype(str)
        despesas['data_despesa'] = despesas['data_despesa'].astype(str)

        col1, col2 = st.columns(2)
        col1.metric("Faturamento Total", f"R$ {faturamento['valor_venda'].sum():.2f}")
        col2.metric("Despesas Totais", f"R$ {despesas['valor'].sum():.2f}")

        lucro = faturamento['valor_venda'].sum() - despesas['valor'].sum()
        st.metric("Lucro Líquido Total", f"R$ {lucro:.2f}")

        fig = px.bar(faturamento, x='data_venda', y='valor_venda', title='Faturamento Mensal')
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(despesas, x='data_despesa', y='valor', title='Despesas Mensais', color_discrete_sequence=['#FF5733'])
        st.plotly_chart(fig2, use_container_width=True)

    elif menu_financas == "Análise Financeira":
        st.subheader("Análise de Lucratividade")

        mes_atual = datetime.today().month
        ano_atual = datetime.today().year

        df_vendas = pd.read_sql("SELECT valor_venda FROM vendas WHERE strftime('%m', data_venda)=? AND strftime('%Y', data_venda)=?", con, params=(f"{mes_atual:02}", str(ano_atual)))
        df_despesas = pd.read_sql("SELECT valor FROM despesas WHERE strftime('%m', data_despesa)=? AND strftime('%Y', data_despesa)=?", con, params=(f"{mes_atual:02}", str(ano_atual)))

        faturamento_mes = df_vendas['valor_venda'].sum()
        despesas_mes = df_despesas['valor'].sum()

        lucro_mes = faturamento_mes - despesas_mes

        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento Mês Atual", f"R$ {faturamento_mes:.2f}")
        col2.metric("Despesas Mês Atual", f"R$ {despesas_mes:.2f}")
        col3.metric("Lucro Mês Atual", f"R$ {lucro_mes:.2f}")

    con.close()
