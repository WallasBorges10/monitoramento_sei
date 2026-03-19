import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de Processos SEI", layout="wide")

st.title("📊 Dashboard de Gestão de Processos")

uploaded_file = st.file_uploader("Escolha o arquivo (Excel ou CSV)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # 1. Carregar os dados
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='latin-1', sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)
        
        # 2. LIMPEZA CRÍTICA DE COLUNAS (Onde estava o erro)
        # Remove espaços em branco no início/fim e normaliza o texto
        df.columns = df.columns.str.strip()
        
        # 3. Tratamento de Datas e Números
        # (Ajuste os nomes abaixo caso sua planilha use nomes ligeiramente diferentes)
        colunas_datas = ['Data de recebimento', 'Data de hoje', 'Data de Saída']
        for col in colunas_datas:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        if 'Tempo / Dias' in df.columns:
            df['Tempo / Dias'] = pd.to_numeric(df['Tempo / Dias'], errors='coerce').fillna(0)

        # --- Verificação de Segurança ---
        if 'Situação' not in df.columns:
            st.error(f"Coluna 'Situação' não encontrada. Colunas detectadas: {list(df.columns)}")
            st.stop()

        # --- 4. KPIs PRINCIPAIS ---
        total_processos = len(df)
        # Filtro flexível para "Aberto" ou "Concluído"
        abertos = len(df[df['Situação'].str.contains('Aberto', na=False, case=False)])
        concluidos = len(df[df['Situação'].str.contains('Concluído|Concluido', na=False, case=False)])
        tempo_medio = df['Tempo / Dias'].mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de Processos", total_processos)
        c2.metric("📦 Em Aberto", abertos)
        c3.metric("✅ Concluídos", concluidos)
        c4.metric("⏱️ Tempo Médio", f"{tempo_medio:.1f} dias")

        st.divider()

        # --- 5. GRÁFICOS ---
        row1_col1, row1_col2 = st.columns(2)

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

        with row1_col2:
            st.subheader("Distribuição por Situação")
            fig_sit = px.pie(df, names='Situação', hole=0.4)
            st.plotly_chart(fig_sit, use_container_width=True)

        st.subheader("🔍 Visualização dos Dados")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Erro inesperado: {e}")
