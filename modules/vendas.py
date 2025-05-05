import streamlit as st
import pandas as pd
from modules.database import conectar
from datetime import datetime
import io

def app():
    st.header("💳 Controle de Vendas")

    con = conectar()
    cursor = con.cursor()

    # Estados para confirmação de exclusão
    if "confirmar_exclusao_venda" not in st.session_state:
        st.session_state.confirmar_exclusao_venda = None

    if 'menu_vendas' not in st.session_state:
        st.session_state.menu_vendas = 'Cadastrar Venda'

    if st.session_state.get("recarregar_venda", False):
        campos_para_limpar = [
            "variacao_selecionada", "quantidade_venda", "valor_venda",
            "forma_pagamento_venda", "data_venda", "vendedor_nome", "cliente_selecionado",
            "produto_id", "nome_produto", "sku_produto", "estoque_disponivel"
        ]
        for campo in campos_para_limpar:
            if campo in st.session_state:
                del st.session_state[campo]
        st.session_state.recarregar_venda = False
        st.session_state.menu_vendas = "Visualizar Vendas"
        st.rerun()

    st.sidebar.radio(
        "Menu Vendas",
        ["Cadastrar Venda", "Visualizar Vendas"],
        key="menu_vendas"
    )

    menu_vendas = st.session_state.menu_vendas

    if menu_vendas == "Cadastrar Venda":
        with st.expander("Registrar Nova Venda", expanded=True):
            variacoes = pd.read_sql('''
                SELECT 
                    v.id as id_variacao,
                    v.sku_variacao, 
                    v.tipo_variacao, 
                    v.valor_variacao, 
                    v.qtd_variacao, 
                    v.qtd_variacao_inicial,
                    v.produto_id,
                    e.nome_produto,
                    e.sku,
                    e.preco_venda
                FROM variacoes_estoque v
                JOIN estoque e ON v.produto_id = e.id
            ''', con)

            clientes = pd.read_sql("SELECT id, nome FROM clientes", con)

            if not variacoes.empty:
                variacao_opcoes = [
                    f"{row['nome_produto']} - {row['tipo_variacao']}: {row['valor_variacao']}"
                    for _, row in variacoes.iterrows()
                ]

                variacao_selecionada = st.selectbox(
                    "Produto (Variação)",
                    ["Selecione uma variação"] + variacao_opcoes,
                    key="variacao_selecionada"
                )

                if variacao_selecionada != "Selecione uma variação":
                    idx = variacao_opcoes.index(variacao_selecionada)
                    variacao_info = variacoes.iloc[idx]

                    id_variacao = variacao_info["id_variacao"]
                    sku_variacao = variacao_info["sku_variacao"]
                    st.session_state.sku_variacao = sku_variacao
                    produto_id = variacao_info["produto_id"]
                    nome_produto = variacao_info["nome_produto"]
                    sku_produto = variacao_info["sku"]
                    preco_sugerido = variacao_info["preco_venda"]

                    # 🧠 Parsing seguro do tipo e valor da variação
                    try:
                        tipo_valor_split = variacao_selecionada.split(":")
                        tipo = tipo_valor_split[0].split("-")[-1].strip()
                        valor = tipo_valor_split[1].strip()
                    except (IndexError, AttributeError):
                        tipo = valor = ""

                    # 🔎 Soma das vendas feitas para essa variação específica
                    vendas_var = cursor.execute('''
                        SELECT SUM(quantidade) FROM vendas 
                        WHERE produto_id = ? AND variacao_escolhida = ?
                    ''', (produto_id, variacao_selecionada)).fetchone()[0] or 0

                    estoque_inicial = variacao_info["qtd_variacao_inicial"]
                    consumo = variacao_info["qtd_variacao"]
                    estoque_disponivel = estoque_inicial - consumo

                    st.session_state.produto_id = produto_id
                    st.session_state.nome_produto = nome_produto
                    st.session_state.sku_produto = sku_produto
                    st.session_state.estoque_disponivel = estoque_disponivel
                    st.session_state.id_variacao = id_variacao
                    st.session_state.variacao_escolhida = variacao_selecionada

                    st.markdown(f"🏷️ **Família:** {nome_produto} (SKU: {sku_produto})")
                    st.markdown(f"📦 **Estoque disponível desta variação:** {estoque_disponivel} unidades")
                    st.markdown(f"💰 **Preço sugerido:** R$ {preco_sugerido:.2f}")

                    if estoque_disponivel > 0:
                        quantidade = st.number_input(
                            "Quantidade vendida",
                            min_value=1,
                            max_value=int(estoque_disponivel),
                            step=1,
                            key="quantidade_venda"
                        )

                        valor_venda = st.number_input(
                            "Valor da venda (total)",
                            min_value=0.0,
                            step=0.1,
                            value=float(preco_sugerido),
                            key="valor_venda"
                        )

                        forma_pagamento = st.selectbox(
                            "Forma de Pagamento",
                            ["Dinheiro", "Cartão", "PIX", "Crediário"],
                            key="forma_pagamento_venda"
                        )

                        data_venda = st.date_input(
                            "Data da Venda",
                            value=datetime.today(),
                            key="data_venda"
                        )

                        vendedor = st.text_input("Nome do Vendedor", key="vendedor_nome")

                        cliente_nome = st.selectbox(
                            "Cliente",
                            ["Selecione um cliente"] + clientes["nome"].tolist(),
                            key="cliente_selecionado"
                        )

                        if st.button("Registrar Venda"):
                            if cliente_nome == "Selecione um cliente":
                                st.error("Por favor, selecione um cliente válido.")
                            elif not vendedor.strip():
                                st.error("Por favor, informe o nome do vendedor.")
                            else:
                                cliente_id = clientes.loc[clientes["nome"] == cliente_nome, "id"].iloc[0]

                                # Extração robusta do nome_produto, tipo_variacao e valor_variacao
                                try:
                                    nome_produto_split, variacao_split = variacao_selecionada.split(" - ", 1)
                                    tipo, valor = variacao_split.split(":", 1)

                                    nome_produto = nome_produto_split.strip()
                                    tipo = tipo.strip()
                                    valor = valor.strip()

                                except Exception as e:
                                    st.error(f"Erro ao interpretar seleção da variação: {e}")
                                    st.stop()

                                variacao_df = pd.read_sql('''
                                    SELECT v.id, v.qtd_variacao, v.qtd_variacao_inicial 
                                    FROM variacoes_estoque v
                                    JOIN estoque e ON v.produto_id = e.id
                                    WHERE e.nome_produto = ? AND v.tipo_variacao = ? AND v.valor_variacao = ?
                                ''', con, params=(nome_produto, tipo, valor))

                                if not variacao_df.empty:
                                    id_var = variacao_df.at[0, 'id']
                                    qtd_variacao_atual = variacao_df.at[0, 'qtd_variacao'] or 0
                                    qtd_inicial = variacao_df.at[0, 'qtd_variacao_inicial']

                                    estoque_disponivel = int(qtd_inicial) - int(qtd_variacao_atual)

                                    if quantidade > estoque_disponivel:
                                        st.error("Quantidade vendida excede o estoque disponível da variação.")
                                        st.stop()

                                    cursor.execute('''
                                        INSERT INTO vendas (
                                            produto_id, id_variacao, sku_variacao, nome_produto, variacao_escolhida,
                                            estoque_restante, quantidade, valor_venda, forma_pagamento,
                                            data_venda, vendedor, cliente_id, nome_cliente
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        produto_id, id_variacao, sku_variacao, nome_produto, variacao_selecionada,
                                        int(estoque_disponivel - quantidade),
                                        int(quantidade), valor_venda, forma_pagamento, data_venda,
                                        vendedor, cliente_id, cliente_nome
                                    ))

                                    nova_qtd_variacao = int(qtd_variacao_atual) + int(quantidade)

                                    cursor.execute('''
                                        UPDATE variacoes_estoque SET qtd_variacao = ?
                                        WHERE sku_variacao = ?
                                    ''', (int(nova_qtd_variacao), sku_variacao))

                                    con.commit()
                                    st.success("Venda registrada com sucesso e estoque atualizado corretamente!")
                                    st.session_state.recarregar_venda = True
                                    st.rerun()
                                else:
                                    st.error("❌ Variação não encontrada no estoque. Confira cadastro do produto.")
                        else:
                            if estoque_disponivel <= 0:
                                st.error("Estoque esgotado para esta variação. Não é possível registrar a venda.")

            else:

                st.warning("Não há variações cadastradas no sistema.")

    elif menu_vendas == "Visualizar Vendas":
        st.subheader("🧾 Vendas Realizadas")
        df_vendas = pd.read_sql('''
            SELECT 
                id, 
                produto_id,
                id_variacao,
                sku_variacao,
                nome_produto,
                variacao_escolhida,
                estoque_restante,
                quantidade, 
                valor_venda,
                forma_pagamento, 
                data_venda, 
                vendedor, 
                nome_cliente
            FROM vendas
        ''', con)

        st.dataframe(
            df_vendas[[
                "id", "sku_variacao", "nome_produto", "variacao_escolhida",
                "quantidade", "valor_venda", "forma_pagamento", "data_venda",
                "vendedor", "nome_cliente", "estoque_restante"
            ]],
            use_container_width=True
        )

        if not df_vendas.empty:

            df_vendas["estoque_restante"] = df_vendas["estoque_restante"].fillna(0).astype(str)

            df_vendas["variacao_escolhida"] = df_vendas["variacao_escolhida"].fillna("Sem Variação").astype(str)

            try:

                buffer = io.BytesIO()

                # 🧼 Limpeza para evitar erro no Excel
                df_vendas = df_vendas.applymap(
                    lambda x: x.encode('ascii', 'ignore').decode('ascii') if isinstance(x, str) else x)

                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_vendas.to_excel(writer, index=False, sheet_name="Vendas")

                st.download_button(
                    label="📥 Exportar Vendas para Excel",
                    data=buffer.getvalue(),
                    file_name="vendas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:

                st.error(f"Erro ao exportar para Excel: {e}")

        st.write("---")

        st.subheader("🗑️ Excluir Venda")

        id_venda_excluir = st.text_input("ID da Venda para excluir", key="id_excluir_venda")

        if st.button("Pedir Confirmação para Excluir Venda"):
            if id_venda_excluir.strip():
                venda = cursor.execute('''
                                SELECT id, produto_id, quantidade, variacao_escolhida 
                                FROM vendas WHERE id = ?
                            ''', (id_venda_excluir.strip(),)).fetchone()
                if venda:
                    st.session_state.confirmar_exclusao_venda = venda
                else:
                    st.error("Venda não encontrada.")

        if st.session_state.confirmar_exclusao_venda:
            venda_id, produto_id, qtd_vendida, variacao_str = st.session_state.confirmar_exclusao_venda

            with st.expander(f"⚠️ Confirmar exclusão da venda ID {venda_id}?"):
                if st.button(f"✅ Confirmar Exclusão da Venda ID {venda_id}"):
                    try:
                        if "-" in variacao_str and ":" in variacao_str:
                            tipo = variacao_str.split(":")[0].split("-")[-1].strip()
                            valor = variacao_str.split(":")[1].strip()
                        else:
                            st.error("Erro ao interpretar a variação da venda. Formato inválido.")
                            st.stop()
                    except Exception as e:
                        st.warning(f"Erro ao interpretar a variação da venda: {e}")
                        st.stop()

                    # ✅ Exclui a venda, mas não altera estoque, pois usamos apenas a lógica de (inicial - vendas)
                    cursor.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
                    # 🔄 Reverter o consumo registrado na variação
                    cursor.execute('''
                        UPDATE variacoes_estoque
                        SET qtd_variacao = qtd_variacao - ?
                        WHERE produto_id = ? AND tipo_variacao = ? AND valor_variacao = ?
                    ''', (qtd_vendida, produto_id, tipo, valor))

                    con.commit()

                    st.success(f"Venda ID {venda_id} excluída com sucesso!")
                    st.session_state.confirmar_exclusao_venda = None
                    st.rerun()

    con.close()
