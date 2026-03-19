import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de Processos SEI", layout="wide")

st.title("📊 Dashboard de Gestão de Processos")
st.markdown("Carregue sua planilha exportada para visualizar os indicadores em tempo real.")

# --- 1. UPLOAD DO ARQUIVO ---
uploaded_file = st.file_uploader("Escolha o arquivo (Excel ou CSV)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    # Leitura dos dados
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Tratamento básico de colunas (Garantir que datas sejam datas)
        date_cols = ['Data de recebimento', 'Data de hoje', 'Data de Saída']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # --- 2. KPIs PRINCIPAIS ---
        total_processos = len(df)
        abertos = len(df[df['Situação'].str.contains('Aberto', na=False)])
        concluidos = len(df[df['Situação'].str.contains('Concluído', na=False)])
        tempo_medio = df['Tempo / Dias'].mean() if 'Tempo / Dias' in df.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Processos", total_processos)
        col2.metric("📦 Em Aberto", abertos, delta_color="inverse")
        col3.metric("✅ Concluídos", concluidos)
        col4.metric("⏱️ Tempo Médio (Dias)", f"{tempo_medio:.1f}")

        st.divider()

        # --- 3. GRÁFICOS INTERATIVOS ---
        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            st.subheader("Processos por Responsável")
            fig_resp = px.bar(df['Responsável'].value_counts().reset_index(), 
                              x='index', y='Responsável', 
                              labels={'index': 'Responsável', 'Responsável': 'Qtd'},
                              color='Responsável', template="plotly_white")
            st.plotly_chart(fig_resp, use_container_width=True)

        with row1_col2:
            st.subheader("Distribuição por Situação")
            fig_sit = px.pie(df, names='Situação', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_sit, use_container_width=True)

        row2_col1, row2_col2 = st.columns(2)

        with row2_col1:
            st.subheader("Tipos de Documento")
            fig_tipo = px.bar(df['Tipo'].value_counts().reset_index(), 
                              y='index', x='Tipo', orientation='h',
                              labels={'index': 'Tipo', 'Tipo': 'Qtd'},
                              color_discrete_sequence=['#636EFA'])
            st.plotly_chart(fig_tipo, use_container_width=True)

        with row2_col2:
            st.subheader("Tempo de Tramitação por Processo")
            # Filtrando apenas processos com tempo definido
            df_tempo = df.dropna(subset=['Tempo / Dias'])
            fig_tempo = px.scatter(df_tempo, x='Data de recebimento', y='Tempo / Dias', 
                                   size='Tempo / Dias', color='Responsável',
                                   hover_data=['Assunto'], template="plotly_dark")
            st.plotly_chart(fig_tempo, use_container_width=True)

        # --- 4. TABELA DETALHADA ---
        st.subheader("🔍 Detalhamento dos Dados")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando o carregamento da planilha para gerar o dashboard.")
