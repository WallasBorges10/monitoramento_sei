import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página (sem emoticon no título)
st.set_page_config(page_title="Dashboard SEI - Gestão de Processos", layout="wide")

st.title("Painel de Gestão de Processos SEI")

# Sidebar para upload e filtros
with st.sidebar:
    st.header("Upload de Dados")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV ou Excel", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        st.success("Arquivo carregado com sucesso!")
    else:
        st.info("Aguardando arquivo...")

# Função para carregar e limpar os dados
@st.cache_data
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            # Detecta separador automaticamente
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
        else:
            df = pd.read_excel(file)
        
        # Limpeza: remove espaços extras nos nomes das colunas e nos dados string
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()
        
        # Converte 'Tempo / Dias' para numérico, forçando erros para NaN
        if 'Tempo / Dias' in df.columns:
            df['Tempo / Dias'] = pd.to_numeric(df['Tempo / Dias'], errors='coerce')
        
        # Se houver coluna de data, tenta converter
        if 'Data de Abertura' in df.columns:
            df['Data de Abertura'] = pd.to_datetime(df['Data de Abertura'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None and not df.empty:
        # Filtros laterais (serão aplicados após os KPIs? Melhor aplicar antes para métricas dinâmicas)
        with st.sidebar:
            st.header("Filtros")
            
            # Filtro de Responsável
            if 'Responsável' in df.columns:
                responsaveis = st.multiselect(
                    "Responsável",
                    options=df['Responsável'].dropna().unique(),
                    default=[]
                )
            else:
                responsaveis = []
            
            # Filtro de Situação
            if 'Situação' in df.columns:
                situacoes = st.multiselect(
                    "Situação",
                    options=df['Situação'].dropna().unique(),
                    default=[]
                )
            else:
                situacoes = []
            
            # Filtro de intervalo de datas (se houver)
            if 'Data de Abertura' in df.columns and df['Data de Abertura'].notna().any():
                min_date = df['Data de Abertura'].min().date()
                max_date = df['Data de Abertura'].max().date()
                date_range = st.date_input(
                    "Período de Abertura",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                if len(date_range) == 2:
                    start_date, end_date = date_range
                else:
                    start_date, end_date = min_date, max_date
            else:
                start_date, end_date = None, None
        
        # Aplicar filtros
        df_filtered = df.copy()
        if responsaveis:
            df_filtered = df_filtered[df_filtered['Responsável'].isin(responsaveis)]
        if situacoes:
            df_filtered = df_filtered[df_filtered['Situação'].isin(situacoes)]
        if start_date and end_date and 'Data de Abertura' in df_filtered.columns:
            df_filtered = df_filtered[
                (df_filtered['Data de Abertura'].dt.date >= start_date) &
                (df_filtered['Data de Abertura'].dt.date <= end_date)
            ]
        
        # Cálculo dos KPIs (com base nos dados filtrados)
        total_processos = len(df_filtered)
        
        # Definição precisa das situações (ajuste conforme seus dados)
        # Usamos .str.contains para capturar variações, mas limitamos a palavras-chave
        if 'Situação' in df_filtered.columns:
            mask_aberto = df_filtered['Situação'].str.contains('Aberto', case=False, na=False, regex=False)
            mask_concluido = df_filtered['Situação'].str.contains('Concluído|Concluido', case=False, na=False, regex=False)
            abertos = mask_aberto.sum()
            concluidos = mask_concluido.sum()
        else:
            abertos = concluidos = 0
        
        # Tempo médio: ignorando valores nulos ou zero (se zero for inválido)
        if 'Tempo / Dias' in df_filtered.columns:
            tempo_valido = df_filtered['Tempo / Dias'].dropna()
            tempo_medio = tempo_valido.mean() if not tempo_valido.empty else 0
        else:
            tempo_medio = 0
        
        # LINHA DE MÉTRICAS (sem emoticons)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Processos", total_processos)
        col2.metric("Em Aberto", abertos)
        col3.metric("Concluídos", concluidos)
        col4.metric("Tempo Médio (dias)", f"{tempo_medio:.1f}" if tempo_medio else "N/A")
        
        st.divider()
        
        # GRÁFICOS - Primeira linha
        row1_col1, row1_col2 = st.columns(2)
        
        with row1_col1:
            st.subheader("Processos por Responsável")
            if 'Responsável' in df_filtered.columns:
                resp_counts = df_filtered['Responsável'].value_counts().reset_index()
                resp_counts.columns = ['Responsável', 'Quantidade']
                fig_resp = px.bar(
                    resp_counts,
                    x='Responsável',
                    y='Quantidade',
                    color='Responsável',
                    text='Quantidade',
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    title=None  # Título já definido no subheader
                )
                fig_resp.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Quantidade")
                st.plotly_chart(fig_resp, use_container_width=True)
            else:
                st.info("Coluna 'Responsável' não encontrada.")
        
        with row1_col2:
            st.subheader("Distribuição por Situação")
            if 'Situação' in df_filtered.columns:
                sit_counts = df_filtered['Situação'].value_counts().reset_index()
                sit_counts.columns = ['Situação', 'Quantidade']
                # Usar gráfico de barras horizontais para melhor legibilidade se muitas categorias
                if len(sit_counts) > 5:
                    fig_sit = px.bar(
                        sit_counts,
                        y='Situação',
                        x='Quantidade',
                        orientation='h',
                        color='Situação',
                        text='Quantidade',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_sit.update_layout(showlegend=False, yaxis_title=None, xaxis_title="Quantidade")
                else:
                    # Gráfico de pizza (sem hole)
                    fig_sit = px.pie(
                        sit_counts,
                        values='Quantidade',
                        names='Situação',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                st.plotly_chart(fig_sit, use_container_width=True)
            else:
                st.info("Coluna 'Situação' não encontrada.")
        
        # GRÁFICOS - Segunda linha (análises adicionais)
        row2_col1, row2_col2 = st.columns(2)
        
        with row2_col1:
            st.subheader("Evolução Temporal")
            # Verifica se existe coluna de data
            if 'Data de Abertura' in df_filtered.columns:
                df_time = df_filtered.dropna(subset=['Data de Abertura']).copy()
                if not df_time.empty:
                    # Agrupa por mês
                    df_time['Mês'] = df_time['Data de Abertura'].dt.to_period('M').astype(str)
                    monthly = df_time.groupby('Mês').size().reset_index(name='Quantidade')
                    fig_time = px.line(
                        monthly,
                        x='Mês',
                        y='Quantidade',
                        markers=True,
                        line_shape='linear',
                        color_discrete_sequence=['#2E86AB']
                    )
                    fig_time.update_layout(xaxis_title="Mês", yaxis_title="Processos")
                    st.plotly_chart(fig_time, use_container_width=True)
                else:
                    st.info("Nenhuma data válida para análise temporal.")
            else:
                st.info("Coluna 'Data de Abertura' não encontrada.")
        
        with row2_col2:
            st.subheader("Tempo Médio por Responsável")
            if 'Responsável' in df_filtered.columns and 'Tempo / Dias' in df_filtered.columns:
                tempo_resp = df_filtered.groupby('Responsável')['Tempo / Dias'].mean().reset_index()
                tempo_resp = tempo_resp.dropna()
                if not tempo_resp.empty:
                    fig_tempo_resp = px.bar(
                        tempo_resp,
                        x='Responsável',
                        y='Tempo / Dias',
                        color='Responsável',
                        text_auto='.1f',
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_tempo_resp.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Média de Dias")
                    st.plotly_chart(fig_tempo_resp, use_container_width=True)
                else:
                    st.info("Dados insuficientes para calcular tempo médio.")
            else:
                st.info("Colunas necessárias não disponíveis.")
        
        # GRÁFICOS - Terceira linha (opcional: principais assuntos)
        if 'Assunto' in df_filtered.columns:
            st.subheader("Principais Assuntos")
            # Top 10 assuntos
            top_assuntos = df_filtered['Assunto'].value_counts().head(10).reset_index()
            top_assuntos.columns = ['Assunto', 'Quantidade']
            fig_assunto = px.bar(
                top_assuntos,
                y='Assunto',
                x='Quantidade',
                orientation='h',
                color='Quantidade',
                color_continuous_scale='Blues',
                title=None
            )
            fig_assunto.update_layout(yaxis_title=None, xaxis_title="Quantidade")
            st.plotly_chart(fig_assunto, use_container_width=True)
        
        # TABELA DE DADOS
        st.subheader("Dados Detalhados")
        st.dataframe(df_filtered, use_container_width=True)
        
    else:
        st.warning("O arquivo carregado está vazio ou não pôde ser processado.")
else:
    st.info("Por favor, faça o upload de um arquivo para iniciar a análise.")
