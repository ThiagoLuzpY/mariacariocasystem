import streamlit as st
from modules import estoque, vendas, clientes, financas, relatorios, premiacoes

def main():
    st.set_page_config(layout="wide")
    st.title("Maria Carioca - Sistema de Gestão Completo")

    paginas = {
        'Estoque': estoque.app,
        'Vendas': vendas.app,
        'Clientes': clientes.app,
        'Finanças': financas.app,
        'Relatórios': relatorios.app,
        'Premiações': premiacoes.app
    }

    escolha = st.sidebar.selectbox('Menu Principal', list(paginas.keys()))

    try:
        paginas[escolha]()
    except Exception as e:
        st.error(f"Ocorreu um erro ao abrir o módulo {escolha}: {str(e)}")

if __name__ == "__main__":
    main()
