import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard SEI - Real Data", layout="wide")

st.title("📊 Gestão de Processos SEI")

uploaded_file = st.file_uploader("Arraste sua planilha aqui", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # 1. CARREGAMENTO COM DETECÇÃO DE SEPARADOR
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file)

        # 2. LIMPEZA TOTAL (Nomes de colunas e Conteúdo)
        df.columns = df.columns.str.strip() # Remove espaços nos títulos
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x) # Remove espaços nas células

        # 3. CONVERSÃO DE TIPOS (Garantindo que 'Tempo / Dias' seja número)
        if 'Tempo / Dias' in df.columns:
            df['Tempo / Dias'] = pd.to_numeric(df['Tempo / Dias'], errors='coerce').fillna(0)

        # 4. CÁLCULO DOS KPIs (Baseado na sua amostra real)
        total_processos = len(df)
        
        # Filtros precisos para a coluna 'Situação'
        # Buscamos qualquer célula que contenha "Aberto" ou "Concluído"
        mask_aberto = df['Situação'].str.contains('Aberto', case=False, na=False)
        mask_concluido = df['Situação'].str.contains('Concluído|Concluido', case=False, na=False)
        
        abertos = mask_aberto.sum()
        concluidos = mask_concluido.sum()
        tempo_medio = df['Tempo / Dias'].mean()

        # EXIBIÇÃO DOS INDICADORES
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Processos", total_processos)
        col2.metric("📂 Em Aberto", abertos)
        col3.metric("✅ Concluídos", concluidos)
        col4.metric("⏱️ Média de Dias", f"{tempo_medio:.1f}")

        st.divider()

        # 5. GRÁFICOS CORRIGIDOS (Evitando erro de 'index' ou 'count')
        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            st.subheader("Processos por Responsável")
            # Contagem real: Claudia (4), Calazans (1), Juliano (1)
            df_resp = df['Responsável'].value_counts().reset_index()
            df_resp.columns = ['Nome', 'Quantidade'] # Forçamos nomes claros
            
            fig_resp = px.bar(df_resp, x='Nome', y='Quantidade', 
                              color='Nome', text='Quantidade',
                              color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_resp, use_container_width=True)

        with row1_col2:
            st.subheader("Situação Atual")
            fig_sit = px.pie(df, names='Situação', hole=0.5,
                             color_discrete_map={'Aberto na unidade': '#EF553B', 
                                               'Concluído na unidade': '#00CC96'})
            st.plotly_chart(fig_sit, use_container_width=True)

        # 6. TABELA COM FILTRO DINÂMICO
        st.subheader("🔍 Base de Dados Completa")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Erro na leitura dos dados: {e}")
        st.info("Verifique se as colunas 'Situação' e 'Responsável' existem na sua planilha.")
else:
    st.info("Aguardando upload dos dados reais...")
