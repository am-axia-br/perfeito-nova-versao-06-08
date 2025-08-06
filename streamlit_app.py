import streamlit as st

# Configuração básica
st.set_page_config(
    page_title="perfecto",
    page_icon="✨"
)

# Título
st.title("perfecto")
st.markdown("Desenvolvido por am-axia-br")

# Conteúdo básico
st.write("Aplicativo em manutenção. Versão completa em breve!")

# Barra lateral
st.sidebar.header("Status")
st.sidebar.info("Versão de diagnóstico")
st.sidebar.info(f"Última atualização: 2025-08-06 15:52:19")

# Botão interativo
if st.button("Testar conexão"):
    st.success("Conexão bem sucedida!")
    st.balloons()