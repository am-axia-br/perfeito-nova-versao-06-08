import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="perfecto",
    page_icon="✨",
    layout="wide"
)

# Título estilizado
st.markdown("""
    <style>
    .perfecto-title {
        font-size: 4em;
        font-weight: bold;
        color: #FF5757;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    <div class="perfecto-title">perfecto</div>
    """, unsafe_allow_html=True)

st.markdown("Desenvolvido por am-axia-br")

# Informações de versão e timestamp
st.sidebar.markdown("---")
st.sidebar.info(f"Última atualização: 2025-08-06 15:39:15")
st.sidebar.info(f"Usuário: am-axia-br")

# Barra lateral
st.sidebar.header("Configurações")
option = st.sidebar.selectbox(
    "Escolha uma visualização:",
    ["Gráfico de Linha", "Gráfico de Barras", "Tabela de Dados"]
)

# Gerar dados de exemplo
def gerar_dados():
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    data = np.random.randn(30).cumsum()
    df = pd.DataFrame({"Data": dates, "Valores": data})
    return df

df = gerar_dados()

# Exibir visualização com base na seleção
if option == "Gráfico de Linha":
    st.subheader("Gráfico de Linha")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df["Data"], df["Valores"], marker='o', color='#FF5757')
    ax.set_title("Evolução dos Valores")
    ax.set_xlabel("Data")
    ax.set_ylabel("Valores")
    st.pyplot(fig)
    
elif option == "Gráfico de Barras":
    st.subheader("Gráfico de Barras")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(df["Data"].astype(str), df["Valores"], color='#FF5757')
    ax.set_title("Valores por Data")
    ax.set_xlabel("Data")
    ax.set_ylabel("Valores")
    plt.xticks(rotation=90)
    st.pyplot(fig)
    
else:
    st.subheader("Tabela de Dados")
    st.dataframe(df)

# Adicionar widgets interativos
st.header("Widgets Interativos")
nome = st.text_input("Digite seu nome:")
if nome:
    st.write(f"Olá, {nome}!")

# Adicionar seletor de data
data_selecionada = st.date_input("Selecione uma data")
st.write(f"Data selecionada: {data_selecionada}")

# Adicionar botão
if st.button("Clique aqui!"):
    st.balloons()
    st.write("Obrigado por clicar!")

# Adicionar footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: gray; font-size: 0.8em;">
    © 2025 perfecto | Criado com ❤️ por am-axia-br | Atualizado em: 2025-08-06 15:39:15 UTC
</div>
""", unsafe_allow_html=True)