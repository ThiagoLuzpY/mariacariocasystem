import streamlit as st
import pandas as pd
from modules.database import conectar
import plotly.express as px
from datetime import datetime

def app():
    st.header("📦 Gestão Completa do Estoque")
    con = conectar()
    cursor = con.cursor()

    # 🕽️ Adicione isso exatamente aqui
    params = dict(st.query_params)  # 🔥 transformamos num dicionário de verdade

    if "menu_estoque" in params:
        st.session_state.menu_estoque = params["menu_estoque"]
        if "editar_id" in params:
            st.session_state.editar_id = int(params["editar_id"])
        st.query_params.clear()

    if 'menu_estoque' not in st.session_state:
        st.session_state.menu_estoque = 'Cadastrar Produto'

    st.sidebar.radio(
        "Menu Estoque",
        ["Cadastrar Produto", "Visualizar Estoque", "Análise de Estoque"],
        key="menu_estoque"
    )

    menu_estoque = st.session_state.menu_estoque

    # Resetar formulário após cadastro bem-sucedido
    if st.session_state.get("recarregar_cadastro"):
        campos_para_limpar = ["sku", "nome", "descricao", "preco_custo", "preco_venda", "quantidade", "data_compra"]
        for campo in campos_para_limpar:
            st.session_state.pop(campo, None)
        for i in range(10):
            for prefixo in ["tipo", "valor", "qtd"]:
                st.session_state.pop(f"{prefixo}_{i}", None)
        st.session_state.recarregar_cadastro = False

    # -------- CADASTRAR PRODUTO --------
    if menu_estoque == "Cadastrar Produto":
        st.subheader("Cadastrar Novo Produto")

        editar_id = st.session_state.get("editar_id", None)

        # Inicializar valores padrão
        sku_default = nome_default = desc_default = ""
        custo_default = venda_default = 0.0
        quant_default = 0
        data_default = datetime.today()
        variacoes_existentes = []

        if editar_id:
            produto = pd.read_sql("SELECT * FROM estoque WHERE id = ?", con, params=(editar_id,))
            variacoes_existentes = pd.read_sql("SELECT * FROM variacoes_estoque WHERE produto_id = ?", con,
                                               params=(editar_id,))

            if not produto.empty:
                st.info(f"🛠️ Editando produto ID {editar_id}")
                sku_default = produto.at[0, "sku"]
                nome_default = produto.at[0, "nome_produto"]
                desc_default = produto.at[0, "descricao"]
                custo_default = produto.at[0, "preco_custo"]
                venda_default = produto.at[0, "preco_venda"]
                quant_default = produto.at[0, "quantidade"]
                data_default = pd.to_datetime(produto.at[0, "data_compra"])
            else:
                st.warning("Produto não encontrado.")
                st.session_state.editar_id = None

        with st.form("form_produto"):
            sku = st.text_input("SKU", value=sku_default)
            nome = st.text_input("Nome do Produto *", value=nome_default)
            descricao = st.text_area("Descrição do Produto", value=desc_default)
            preco_custo = st.number_input("Preço de Custo *", min_value=0.0, step=0.1, value=custo_default)
            preco_venda = st.number_input("Preço de Venda", min_value=0.0, step=0.1, value=venda_default)

            adicionar_variacoes = st.checkbox("Deseja adicionar variações?", value=len(variacoes_existentes) > 0)

            if not adicionar_variacoes:
                quantidade = st.number_input("Quantidade Inicial", min_value=0, step=1, value=quant_default)
            else:
                st.markdown(":warning: A quantidade será definida pelas variações abaixo.")
                quantidade = 0

            data_compra = st.date_input("Data de Compra *", value=data_default)

            variacoes = []
            if adicionar_variacoes:
                st.markdown("### Adicionar Variações")
                variacoes_existentes = variacoes_existentes.to_dict(orient="records") if isinstance(
                    variacoes_existentes, pd.DataFrame) else []

                for i in range(10):
                    tipo_padrao = valor_padrao = ""
                    qtd_padrao = 0
                    if i < len(variacoes_existentes):
                        tipo_padrao = variacoes_existentes[i]['tipo_variacao']
                        valor_padrao = variacoes_existentes[i]['valor_variacao']
                        qtd_padrao = variacoes_existentes[i].get('qtd_variacao_inicial', 0)

                    col1, col2, col3 = st.columns([3, 4, 3])
                    with col1:
                        tipo = st.selectbox(f"Tipo de variação #{i + 1}", ["", "tamanho", "cor", "modelo"],
                                            index=["", "tamanho", "cor", "modelo"].index(
                                                tipo_padrao) if tipo_padrao in ["tamanho", "cor", "modelo"] else 0,
                                            key=f"tipo_{i}")
                    with col2:
                        valor = st.text_input(f"Valor da variação #{i + 1}", value=valor_padrao, key=f"valor_{i}")
                    with col3:
                        qtd = st.number_input(f"Qtd", min_value=0, step=1, value=qtd_padrao, key=f"qtd_{i}")

                    if tipo and valor:
                        variacoes.append((tipo, valor, qtd))

            submit = st.form_submit_button("Salvar Produto")

            if submit:
                if not nome or not preco_custo or not data_compra:
                    st.error("Campos obrigatórios não preenchidos!")
                    st.stop()

                if not editar_id:
                    cursor.execute("SELECT id FROM estoque WHERE sku = ?", (sku,))
                    if cursor.fetchone():
                        st.error("❌ Já existe um produto com esse SKU. Use outro ou edite o existente.")
                        st.stop()

                soma_variacoes = sum([q for (_, _, q) in variacoes])

                if not adicionar_variacoes and quantidade == 0:
                    st.error("❌ Quantidade não pode ser zero para produtos sem variações.")
                    st.stop()

                if adicionar_variacoes and soma_variacoes == 0:
                    st.error("❌ É necessário informar ao menos 1 variação com quantidade maior que zero.")
                    st.stop()

                if editar_id:
                    # Atualizar produto principal
                    cursor.execute('''
                        UPDATE estoque SET sku=?, nome_produto=?, descricao=?, preco_custo=?, preco_venda=?, quantidade=?, data_compra=?
                        WHERE id=?''',
                                   (sku, nome, descricao, preco_custo, preco_venda, soma_variacoes, data_compra,
                                    editar_id))

                    # Exclui as variações antigas
                    cursor.execute("DELETE FROM variacoes_estoque WHERE produto_id = ?", (editar_id,))

                    # Insere novamente as variações com sku_variacao gerado corretamente
                    for tipo, valor, qtd in variacoes:
                        # Insere variação sem o SKU
                        cursor.execute('''
                            INSERT INTO variacoes_estoque (produto_id, tipo_variacao, valor_variacao, qtd_variacao_inicial)
                            VALUES (?, ?, ?, ?)''', (editar_id, tipo, valor, qtd))

                        id_variacao = cursor.lastrowid

                        # Constrói o sku_variacao com base no SKU base e ID da variação
                        sku_variacao = f"{sku}-{id_variacao}"

                        # Atualiza a linha recém-criada com o sku_variacao
                        cursor.execute('''
                            UPDATE variacoes_estoque
                            SET sku_variacao = ?
                            WHERE id = ?''', (sku_variacao, id_variacao))

                    con.commit()
                    st.success("Produto atualizado com sucesso!")
                else:
                    # Novo
                    cursor.execute('''
                        INSERT INTO estoque (sku, nome_produto, descricao, preco_custo, preco_venda, quantidade, data_compra)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                   (sku, nome, descricao, preco_custo, preco_venda,
                                    soma_variacoes if adicionar_variacoes else quantidade, data_compra))
                    produto_id = cursor.lastrowid

                    # 🔄 Inserir variações e gerar sku_variacao corretamente
                    for tipo, valor, qtd in variacoes:
                        # 1. Inserir a variação inicialmente sem o sku_variacao
                        cursor.execute('''
                            INSERT INTO variacoes_estoque (produto_id, tipo_variacao, valor_variacao, qtd_variacao_inicial)
                            VALUES (?, ?, ?, ?)''', (produto_id, tipo, valor, qtd))

                        id_variacao = cursor.lastrowid  # 🔑 pega o ID gerado automaticamente

                        # 2. Construir o SKU da variação com base no SKU da família + ID da variação
                        sku_variacao = f"{sku}-{id_variacao}"

                        # 3. Atualizar a coluna sku_variacao com o valor construído
                        cursor.execute('''
                            UPDATE variacoes_estoque
                            SET sku_variacao = ?
                            WHERE id = ?''', (sku_variacao, id_variacao))

                    con.commit()

                    st.success("Produto e variações cadastrados com sucesso!")

                # Limpar campos
                campos_para_limpar = ["sku", "nome", "descricao", "preco_custo", "preco_venda", "quantidade",
                                      "data_compra"]
                for campo in campos_para_limpar:
                    st.session_state.pop(campo, None)
                for i in range(10):
                    for prefixo in ["tipo", "valor", "qtd"]:
                        st.session_state.pop(f"{prefixo}_{i}", None)

                # Resetar editar_id
                st.session_state.editar_id = None

                st.query_params.update({
                    "menu_estoque": "Visualizar Estoque"
                })
                st.rerun()

    # -------- VISUALIZAR ESTOQUE --------
    elif menu_estoque == "Visualizar Estoque":
        st.subheader("Produtos em Estoque")

        df_produtos = pd.read_sql("SELECT * FROM estoque", con)
        df_variacoes = pd.read_sql('''
            SELECT 
                v.id,
                v.sku_variacao,
                v.produto_id,
                v.tipo_variacao,
                v.valor_variacao,
                v.qtd_variacao_inicial,
                v.qtd_variacao,
                (v.qtd_variacao_inicial - v.qtd_variacao) AS qtd_restante,
                e.sku AS produto_sku
            FROM variacoes_estoque v
            JOIN estoque e ON v.produto_id = e.id
        ''', con)
        df_variacoes['qtd_restante'] = df_variacoes['qtd_variacao_inicial'] - df_variacoes['qtd_variacao']

        st.write("### Produtos principais:")
        for idx, row in df_produtos.iterrows():
            variacoes_prod = df_variacoes[df_variacoes['produto_id'] == row['id']]
            variacoes_prod.loc[:, 'qtd_restante'] = variacoes_prod['qtd_variacao_inicial'] - variacoes_prod['qtd_variacao']
            soma_variacoes = variacoes_prod['qtd_restante'].sum() if not variacoes_prod.empty else 0
            quantidade_total = soma_variacoes if not variacoes_prod.empty else row['quantidade']

            with st.expander(f"📜 {row['nome_produto']} (SKU: {row['sku']})"):
                st.write(f"📌 **Descrição:** {row['descricao']}")
                st.write(f"💰 Preço de custo: R$ {row['preco_custo']:.2f}")
                st.write(f"🏷️ Preço de venda: R$ {row['preco_venda']:.2f}")
                st.write(f"📦 Quantidade total: {int(quantidade_total)}")
                st.write(f"🗓️ Data de compra: {row['data_compra']}")

                if not variacoes_prod.empty:
                    st.markdown("🔄 **Variações Cadastradas:**")
                    st.dataframe(
                        variacoes_prod[[
                            'sku_variacao',  # ex: MCC001-4
                            'id',  # id da variação
                            'produto_sku',  # SKU base (da família)
                            'tipo_variacao',
                            'valor_variacao',
                            'qtd_variacao_inicial',
                            'qtd_variacao',
                            'qtd_restante'
                        ]],
                        use_container_width=True
                    )

                col1, col2 = st.columns(2)
                if col1.button("✏️ Editar", key=f"edit_{row['id']}"):
                    st.session_state.editar_id = row['id']
                    st.query_params.update({
                        "menu_estoque": "Cadastrar Produto",
                        "editar_id": row["id"]
                    })
                    st.rerun()

                if col2.button("🗑️ Excluir", key=f"delete_{row['id']}"):
                    cursor.execute("DELETE FROM variacoes_estoque WHERE produto_id = ?", (row['id'],))
                    cursor.execute("DELETE FROM estoque WHERE id = ?", (row['id'],))
                    con.commit()
                    st.success("Produto deletado com sucesso.")
                    st.rerun()

        if not df_produtos.empty:
            if st.button("Exportar Estoque Completo"):
                df_export = df_produtos.copy()
                df_export.to_excel("estoque_completo.xlsx", index=False)
                st.success("Exportado com sucesso!")

    # -------- ANÁLISE DE ESTOQUE --------
    elif menu_estoque == "Análise de Estoque":
        st.subheader("📦 Análise do Estoque (Produtos com Baixo Estoque)")

        limite = st.slider("Definir limite baixo de estoque", min_value=0, max_value=500, value=5, step=5)

        # Armazenar se o botão foi clicado
        if "atualizou_analise" not in st.session_state:
            st.session_state.atualizou_analise = False

        if st.button("🔁 Atualizar Análise"):
            st.session_state.atualizou_analise = True

        # Processar apenas se já clicou em atualizar
        if st.session_state.atualizou_analise:
            # Leitura dos dados
            df_produtos = pd.read_sql("SELECT id, nome_produto, quantidade FROM estoque", con)
            df_variacoes = pd.read_sql(
                "SELECT produto_id, tipo_variacao, valor_variacao, qtd_variacao_inicial, qtd_variacao FROM variacoes_estoque",
                con)
            df_variacoes['qtd_restante'] = df_variacoes['qtd_variacao_inicial'] - df_variacoes['qtd_variacao']

            soma_var = df_variacoes.groupby('produto_id')['qtd_restante'].sum().reset_index()
            soma_var.rename(columns={'qtd_restante': 'qtd_var'}, inplace=True)

            df_analise = pd.merge(df_produtos, soma_var, how='left', left_on='id', right_on='produto_id')
            df_analise['qtd_var'] = df_analise['qtd_var'].fillna(0)
            df_analise['quantidade'] = df_analise['quantidade'].fillna(0)

            df_analise['quantidade_total'] = df_analise.apply(
                lambda row: row['qtd_var'] if row['qtd_var'] > 0 else row['quantidade'], axis=1
            )

            df_analise = df_analise.sort_values(by='quantidade_total')

            df_baixo_estoque = df_analise[df_analise['quantidade_total'] <= limite]

            # Exibe resumo
            st.markdown("📊 **Resumo da Análise:**")
            st.dataframe(df_analise[['nome_produto', 'quantidade', 'qtd_var', 'quantidade_total']],
                         use_container_width=True)

            total_alerta = len(df_baixo_estoque)
            unidades_alerta = int(df_baixo_estoque['quantidade_total'].sum())

            st.markdown(f"🔴 **Produtos críticos:** {total_alerta}")
            st.markdown(f"📉 **Unidades em risco:** {unidades_alerta}")

            if not df_baixo_estoque.empty:
                st.markdown("📉 **Produtos com Estoque Baixo**")
                fig = px.bar(
                    df_baixo_estoque,
                    x='nome_produto',
                    y='quantidade_total',
                    labels={'quantidade_total': 'Quantidade', 'nome_produto': 'Produto'},
                    color='quantidade_total',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig, use_container_width=True)

                csv = df_baixo_estoque.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Exportar Baixo Estoque", data=csv, file_name="estoque_baixo.csv", mime='text/csv')
            else:
                st.success("✅ Nenhum produto abaixo do limite definido.")

            # 🔍 Mostrar variações com estoque crítico
            if st.checkbox("🔍 Ver variações com estoque crítico"):
                df_var_baixas = df_variacoes[df_variacoes['qtd_restante'] <= limite]
                if not df_var_baixas.empty:
                    st.markdown("🔸 **Variações com Baixo Estoque:**")
                    st.dataframe(df_var_baixas, use_container_width=True)
                else:
                    st.info("✅ Nenhuma variação individual abaixo do limite.")
