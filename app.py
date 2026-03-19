with row1_col1:
    st.subheader("Processos por Responsável")
    
    # Criamos a contagem e resetamos o index
    # O Pandas 2.0+ nomeia as colunas como [NomeOriginal, 'count']
    df_resp = df['Responsável'].value_counts().reset_index()
    
    # Para garantir que funcione em qualquer versão, renomeamos manualmente
    df_resp.columns = ['Responsável', 'Quantidade']
    
    fig_resp = px.bar(
        df_resp, 
        x='Responsável', 
        y='Quantidade', 
        color='Responsável',
        text_auto=True, # Mostra o número em cima da barra
        template="plotly_white"
    )
    st.plotly_chart(fig_resp, use_container_width=True)
