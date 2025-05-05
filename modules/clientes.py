import streamlit as st
import pandas as pd
from modules.database import conectar
from io import BytesIO

def app():
    st.header("👤 Gestão de Clientes")

    con = conectar()
    cursor = con.cursor()

    if "confirmar_exclusao" not in st.session_state:
        st.session_state.confirmar_exclusao = None
    if "limpar_campos_cliente" not in st.session_state:
        st.session_state.limpar_campos_cliente = False

    # 🔵 Tratamento para limpar os campos depois do rerun
    if st.session_state.limpar_campos_cliente:
        st.session_state.nome_cliente = ""
        st.session_state.telefone_cliente = ""
        st.session_state.email_cliente = ""
        st.session_state.limpar_campos_cliente = False

    with st.expander("Cadastrar novo cliente", expanded=True):
        nome = st.text_input("Nome do Cliente", key="nome_cliente")
        telefone = st.text_input("Telefone", key="telefone_cliente")
        email = st.text_input("Email", key="email_cliente")

        if st.button("Salvar Cliente"):
            if nome.strip():
                cursor.execute('''
                    INSERT INTO clientes (nome, telefone, email)
                    VALUES (?, ?, ?)''', (nome.strip(), telefone.strip(), email.strip()))
                con.commit()
                st.success("Cliente cadastrado com sucesso!")

                # 🔵 Agora limpar todos os campos corretamente
                st.session_state.limpar_campos_cliente = True
                st.rerun()
            else:
                st.error("Nome do cliente é obrigatório!")

    st.write("## Clientes cadastrados:")

    df_clientes = pd.read_sql("SELECT * FROM clientes", con)

    edited_df = st.data_editor(
        df_clientes,
        use_container_width=True,
        num_rows="dynamic",
        key="edicao_clientes"
    )

    if st.button("Salvar Alterações"):
        for idx, row in edited_df.iterrows():
            cursor.execute('''
                UPDATE clientes
                SET nome = ?, telefone = ?, email = ?
                WHERE id = ?
            ''', (row['nome'], row['telefone'], row['email'], row['id']))
        con.commit()
        st.success("Alterações salvas com sucesso!")
        st.rerun()

    st.write("---")
    st.subheader("🗑️ Excluir Cliente")

    id_para_excluir = st.text_input("ID do Cliente para excluir", key="id_excluir")

    if st.button("Pedir Confirmação para Excluir"):
        if id_para_excluir.strip():
            cliente = cursor.execute(
                "SELECT nome FROM clientes WHERE id = ?",
                (id_para_excluir.strip(),)
            ).fetchone()
            if cliente:
                st.session_state.confirmar_exclusao = (id_para_excluir.strip(), cliente[0])
            else:
                st.error("Cliente não encontrado.")

    # Mostrar o expander de confirmação se necessário
    if st.session_state.confirmar_exclusao:
        id_confirmar, nome_confirmar = st.session_state.confirmar_exclusao
        with st.expander(f"⚠️ Confirmar exclusão de '{nome_confirmar}'?"):
            if st.button(f"✅ Confirmar Exclusão de {nome_confirmar}"):
                cursor.execute("DELETE FROM clientes WHERE id = ?", (id_confirmar,))
                con.commit()
                st.success(f"Cliente '{nome_confirmar}' excluído com sucesso!")
                st.session_state.confirmar_exclusao = None
                st.rerun()

    # 🔵 Botão para exportar tabela como Excel
    buffer = BytesIO()
    edited_df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)
    st.download_button(
        label="📥 Exportar Clientes para Excel",
        data=buffer,
        file_name="clientes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    con.close()
