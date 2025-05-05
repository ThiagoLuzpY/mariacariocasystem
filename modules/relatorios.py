import streamlit as st
import pandas as pd
from modules.database import conectar
import plotly.graph_objects as go
from datetime import datetime

def app():
    st.header("📑 Relatórios Detalhados")

    con = conectar()

    menu_relatorios = st.sidebar.radio("Relatórios", ["Vendas Mensais", "Performance de Produtos", "Relatório Financeiro Completo"])

    if menu_relatorios == "Vendas Mensais":
        st.subheader("Relatório Detalhado de Vendas por Mês")

        df_vendas = pd.read_sql("SELECT valor_venda, data_venda FROM vendas", con)
        df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
        vendas_mes = df_vendas.groupby(df_vendas['data_venda'].dt.strftime('%Y-%m')).sum().reset_index()

        fig = go.Figure(go.Bar(
            x=vendas_mes['data_venda'], y=vendas_mes['valor_venda'],
            marker=dict(color=vendas_mes['valor_venda'], colorscale='Blues'),
            text=vendas_mes['valor_venda'], textposition='outside'))

        fig.update_layout(title="Faturamento Mensal Detalhado", xaxis_title="Mês", yaxis_title="Faturamento (R$)")
        st.plotly_chart(fig, use_container_width=True)

    elif menu_relatorios == "Performance de Produtos":
        st.subheader("Performance de Vendas por Produto")

        df_produtos = pd.read_sql('''
        SELECT estoque.nome_produto, SUM(vendas.quantidade) as quantidade_vendida
        FROM vendas
        JOIN estoque ON vendas.produto_id = estoque.id
        GROUP BY estoque.nome_produto ORDER BY quantidade_vendida DESC
        ''', con)

        fig = go.Figure(go.Bar(
            x=df_produtos['nome_produto'], y=df_produtos['quantidade_vendida'],
            marker=dict(color=df_produtos['quantidade_vendida'], colorscale='Greens'),
            text=df_produtos['quantidade_vendida'], textposition='outside'))

        fig.update_layout(title="Quantidade Vendida por Produto", xaxis_title="Produto", yaxis_title="Quantidade Vendida")
        st.plotly_chart(fig, use_container_width=True)

    elif menu_relatorios == "Relatório Financeiro Completo":
        st.subheader("Relatório Financeiro Completo e Minucioso")

        df_vendas = pd.read_sql("SELECT valor_venda, data_venda FROM vendas", con)
        df_despesas = pd.read_sql("SELECT valor, data_despesa FROM despesas", con)

        total_faturamento = df_vendas['valor_venda'].sum()
        total_despesas = df_despesas['valor'].sum()
        lucro_total = total_faturamento - total_despesas

        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento Total", f"R$ {total_faturamento:.2f}")
        col2.metric("Despesas Totais", f"R$ {total_despesas:.2f}")
        col3.metric("Lucro Líquido Total", f"R$ {lucro_total:.2f}")

        st.write("### Histórico Completo de Vendas e Despesas")

        vendas_exp = df_vendas.copy()
        vendas_exp["Tipo"] = "Receita"
        vendas_exp.rename(columns={"valor_venda": "Valor", "data_venda": "Data"}, inplace=True)

        despesas_exp = df_despesas.copy()
        despesas_exp["Tipo"] = "Despesa"
        despesas_exp.rename(columns={"valor": "Valor", "data_despesa": "Data"}, inplace=True)

        financeiro = pd.concat([vendas_exp, despesas_exp]).sort_values(by="Data", ascending=False)
        st.dataframe(financeiro, use_container_width=True)

        if st.button("Exportar Financeiro Completo"):
            financeiro.to_excel("financeiro_completo.xlsx", index=False)
            st.success("Relatório exportado com sucesso!")

    con.close()
