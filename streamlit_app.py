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

# Título e informações
st.title("perfecto")
st.markdown("Desenvolvido por am-axia-br")
st.info("Aplicativo em modo básico - Versão 2025-08-07 03:15")

# Demonstração de funcionalidade básica
if st.button("Testar aplicativo"):
    st.success("Aplicativo funcionando corretamente!")
    st.balloons()
    
    # Gerar dados simples
    data = pd.DataFrame({
        'x': range(10),
        'y': [i**2 for i in range(10)]
    })
    
    # Mostrar tabela e gráfico
    st.write("### Dados de exemplo")
    st.dataframe(data)
    
    st.write("### Visualização")
    fig, ax = plt.subplots()
    ax.plot(data['x'], data['y'], marker='o')
    ax.set_title("Função quadrática")
    st.pyplot(fig)