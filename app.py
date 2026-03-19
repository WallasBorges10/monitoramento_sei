import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página
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
        
        # Converte 'Tempo / Dias' para numérico
        if 'Tempo / Dias' in df.columns:
            df['Tempo / Dias'] = pd.to_numeric(df['Tempo / Dias'], errors='coerce')
        
        # Converte colunas de data se existirem
        for date_col in ['Data de Abertura', 'Data de Conclusão']:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None and not df.empty:
        # --- PADRONIZAÇÃO DO CAMPO RESPONSÁVEL (apenas primeiro nome) ---
        if 'Responsável' in df.columns:
            # Remove valores nulos e aplica split para pegar primeiro nome
            df['Responsável'] = df['Responsável'].fillna('Não atribuído').astype(str)
            df['Responsável'] = df['Responsável'].apply(lambda x: x.split()[0] if len(x.split()) > 0 else x)
        
        # --- MAPEAMENTO DE SITUAÇÕES (para garantir contagem correta) ---
        # Oferece ao usuário a opção de definir os termos para "Aberto" e "Concluído"
        with st.sidebar:
            st.header("Configurações de Situação")
            st.markdown("Defina as palavras-chave que identificam processos **em aberto** e **concluídos**.")
            
            if 'Situação' in df.columns:
                # Obtém valores únicos para sugerir
                situacoes_unicas = df['Situação'].dropna().unique().tolist()
                
                # Campo para palavras-chave de aberto
                default_aberto = ['Aberto', 'Em andamento', 'Pendente']
                aberto_keywords = st.text_input(
                    "Palavras para ABERTO (separadas por vírgula)",
                    value=', '.join([k for k in default_aberto if any(k in s for s in situacoes_unicas)] or default_aberto)
                )
                lista_aberto = [k.strip() for k in aberto_keywords.split(',') if k.strip()]
                
                # Campo para palavras-chave de concluído
                default_concluido = ['Concluído', 'Finalizado', 'Encerrado']
                concluido_keywords = st.text_input(
                    "Palavras para CONCLUÍDO (separadas por vírgula)",
                    value=', '.join([k for k in default_concluido if any(k in s for s in situacoes_unicas)] or default_concluido)
                )
                lista_concluido = [k.strip() for k in concluido_keywords.split(',') if k.strip()]
            else:
                st.warning("Coluna 'Situação' não encontrada. As métricas ficarão comprometidas.")
                lista_aberto = []
                lista_concluido = []
        
        # --- FILTROS INTERATIVOS ---
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
            
            # Filtro de Situação (baseado nos valores originais)
            if 'Situação' in df.columns:
                situacoes_filtro = st.multiselect(
                    "Situação (original)",
                    options=df['Situação'].dropna().unique(),
                    default=[]
                )
            else:
                situacoes_filtro = []
            
            # Filtro de intervalo de datas (se houver Data de Abertura)
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
        
        # --- APLICAÇÃO DOS FILTROS ---
        df_filtered = df.copy()
        if responsaveis:
            df_filtered = df_filtered[df_filtered['Responsável'].isin(responsaveis)]
        if situacoes_filtro:
            df_filtered = df_filtered[df_filtered['Situação'].isin(situacoes_filtro)]
        if start_date and end_date and 'Data de Abertura' in df_filtered.columns:
            df_filtered = df_filtered[
                (df_filtered['Data de Abertura'].dt.date >= start_date) &
                (df_filtered['Data de Abertura'].dt.date <= end_date)
            ]
        
        # --- CÁLCULO DAS MÉTRICAS (CORRIGIDO) ---
        total_processos = len(df_filtered)
        
        if 'Situação' in df_filtered.columns and lista_aberto and lista_concluido:
            # Cria máscaras combinando as palavras-chave
            mask_aberto = df_filtered['Situação'].apply(
                lambda x: any(kw.lower() in str(x).lower() for kw in lista_aberto) if pd.notna(x) else False
            )
            mask_concluido = df_filtered['Situação'].apply(
                lambda x: any(kw.lower() in str(x).lower() for kw in lista_concluido) if pd.notna(x) else False
            )
            # Nota: pode haver sobreposição se uma situação for classificada como ambos; definimos prioridade (concluído sobrescreve aberto)
            abertos = mask_aberto.sum()
            concluidos = mask_concluido.sum()
            # Outras situações (não classificadas) serão ignoradas nessas métricas
        else:
            abertos = concluidos = 0
        
        # Tempo médio (considerando apenas valores positivos)
        if 'Tempo / Dias' in df_filtered.columns:
            tempo_valido = df_filtered['Tempo / Dias'].dropna()
            tempo_valido = tempo_valido[tempo_valido > 0]  # remove zeros se fizer sentido
            tempo_medio = tempo_valido.mean() if not tempo_valido.empty else 0
        else:
            tempo_medio = 0
        
        # --- LINHA DE MÉTRICAS PRINCIPAIS ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Processos", total_processos)
        col2.metric("Em Aberto", abertos)
        col3.metric("Concluídos", concluidos)
        col4.metric("Tempo Médio (dias)", f"{tempo_medio:.1f}" if tempo_medio else "N/A")
        
        st.divider()
        
        # --- GRÁFICOS E ANÁLISES DETALHADAS ---
        # Organização em abas para facilitar a navegação
        tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Temporal", "Responsáveis", "Detalhamento"])
        
        with tab1:
            # Primeira linha de gráficos na visão geral
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
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_resp.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Quantidade")
                    st.plotly_chart(fig_resp, use_container_width=True)
                else:
                    st.info("Coluna 'Responsável' não encontrada.")
            
            with row1_col2:
                st.subheader("Distribuição por Situação (agrupada)")
                if 'Situação' in df_filtered.columns:
                    # Criar categoria simplificada com base nas palavras-chave
                    def categorize_situation(sit):
                        if pd.isna(sit):
                            return "Não informado"
                        sit_lower = str(sit).lower()
                        for kw in lista_concluido:
                            if kw.lower() in sit_lower:
                                return "Concluído"
                        for kw in lista_aberto:
                            if kw.lower() in sit_lower:
                                return "Em aberto"
                        return "Outros"
                    
                    df_filtered['Situação Grupo'] = df_filtered['Situação'].apply(categorize_situation)
                    sit_grouped = df_filtered['Situação Grupo'].value_counts().reset_index()
                    sit_grouped.columns = ['Grupo', 'Quantidade']
                    
                    fig_sit_group = px.pie(
                        sit_grouped,
                        values='Quantidade',
                        names='Grupo',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_sit_group, use_container_width=True)
                else:
                    st.info("Coluna 'Situação' não encontrada.")
            
            # Segunda linha: histograma de tempo
            st.subheader("Distribuição do Tempo de Tramitação (dias)")
            if 'Tempo / Dias' in df_filtered.columns:
                tempo_data = df_filtered['Tempo / Dias'].dropna()
                if not tempo_data.empty:
                    fig_hist = px.histogram(
                        tempo_data,
                        nbins=20,
                        labels={'value': 'Dias', 'count': 'Frequência'},
                        color_discrete_sequence=['#2E86AB']
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.info("Dados de tempo insuficientes.")
            else:
                st.info("Coluna 'Tempo / Dias' não encontrada.")
        
        with tab2:
            # Análises temporais
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader("Processos Abertos por Mês")
                if 'Data de Abertura' in df_filtered.columns:
                    df_time = df_filtered.dropna(subset=['Data de Abertura']).copy()
                    if not df_time.empty:
                        df_time['Mês'] = df_time['Data de Abertura'].dt.to_period('M').astype(str)
                        monthly = df_time.groupby('Mês').size().reset_index(name='Quantidade')
                        fig_open = px.line(
                            monthly,
                            x='Mês',
                            y='Quantidade',
                            markers=True,
                            line_shape='linear',
                            color_discrete_sequence=['#2E86AB']
                        )
                        fig_open.update_layout(xaxis_title="Mês", yaxis_title="Processos")
                        st.plotly_chart(fig_open, use_container_width=True)
                    else:
                        st.info("Nenhuma data de abertura válida.")
                else:
                    st.info("Coluna 'Data de Abertura' não encontrada.")
            
            with col_right:
                st.subheader("Processos Concluídos por Mês")
                if 'Data de Conclusão' in df_filtered.columns:
                    df_conc = df_filtered.dropna(subset=['Data de Conclusão']).copy()
                    if not df_conc.empty:
                        df_conc['Mês'] = df_conc['Data de Conclusão'].dt.to_period('M').astype(str)
                        monthly_conc = df_conc.groupby('Mês').size().reset_index(name='Quantidade')
                        fig_conc = px.line(
                            monthly_conc,
                            x='Mês',
                            y='Quantidade',
                            markers=True,
                            line_shape='linear',
                            color_discrete_sequence=['#A569BD']
                        )
                        fig_conc.update_layout(xaxis_title="Mês", yaxis_title="Processos")
                        st.plotly_chart(fig_conc, use_container_width=True)
                    else:
                        st.info("Nenhuma data de conclusão válida.")
                else:
                    st.info("Coluna 'Data de Conclusão' não encontrada.")
            
            # Opcional: acumulado
            st.subheader("Acumulado de Processos Abertos ao Longo do Tempo")
            if 'Data de Abertura' in df_filtered.columns:
                df_time = df_filtered.dropna(subset=['Data de Abertura']).copy()
                if not df_time.empty:
                    df_time = df_time.sort_values('Data de Abertura')
                    df_time['Acumulado'] = range(1, len(df_time) + 1)
                    fig_acum = px.area(
                        df_time,
                        x='Data de Abertura',
                        y='Acumulado',
                        labels={'Data de Abertura': 'Data', 'Acumulado': 'Processos Acumulados'},
                        color_discrete_sequence=['#E67E22']
                    )
                    st.plotly_chart(fig_acum, use_container_width=True)
        
        with tab3:
            # Análise por responsável
            if 'Responsável' in df_filtered.columns:
                # Tabela resumo por responsável
                st.subheader("Resumo por Responsável")
                resumo_resp = df_filtered.groupby('Responsável').agg(
                    Total=('Responsável', 'count'),
                    Tempo_Medio=('Tempo / Dias', 'mean'),
                    Min_Dias=('Tempo / Dias', 'min'),
                    Max_Dias=('Tempo / Dias', 'max')
                ).round(1).reset_index()
                resumo_resp.columns = ['Responsável', 'Total Processos', 'Tempo Médio (dias)', 'Mínimo (dias)', 'Máximo (dias)']
                st.dataframe(resumo_resp, use_container_width=True)
                
                # Gráfico de barras do tempo médio
                st.subheader("Tempo Médio por Responsável")
                fig_tempo_resp = px.bar(
                    resumo_resp,
                    x='Responsável',
                    y='Tempo Médio (dias)',
                    color='Responsável',
                    text_auto='.1f',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_tempo_resp.update_layout(showlegend=False, xaxis_title=None)
                st.plotly_chart(fig_tempo_resp, use_container_width=True)
                
                # Boxplot do tempo por responsável
                st.subheader("Distribuição do Tempo por Responsável")
                fig_box = px.box(
                    df_filtered,
                    x='Responsável',
                    y='Tempo / Dias',
                    color='Responsável',
                    points='all'
                )
                fig_box.update_layout(showlegend=False, xaxis_title=None)
                st.plotly_chart(fig_box, use_container_width=True)
            else:
                st.info("Coluna 'Responsável' não encontrada.")
        
        with tab4:
            # Detalhamento: tabela completa e estatísticas adicionais
            st.subheader("Dados Detalhados")
            st.dataframe(df_filtered, use_container_width=True)
            
            # Exibir algumas estatísticas extras
            if 'Assunto' in df_filtered.columns:
                st.subheader("Top 10 Assuntos")
                top_assuntos = df_filtered['Assunto'].value_counts().head(10).reset_index()
                top_assuntos.columns = ['Assunto', 'Quantidade']
                fig_assunto = px.bar(
                    top_assuntos,
                    y='Assunto',
                    x='Quantidade',
                    orientation='h',
                    color='Quantidade',
                    color_continuous_scale='Blues'
                )
                fig_assunto.update_layout(yaxis_title=None, xaxis_title="Quantidade")
                st.plotly_chart(fig_assunto, use_container_width=True)
            
            # Estatísticas gerais
            st.subheader("Estatísticas Gerais")
            stats = pd.DataFrame({
                'Métrica': ['Total de Registros', 'Período (dias)', 'Processos sem Responsável', 'Processos sem Data'],
                'Valor': [
                    len(df_filtered),
                    (df_filtered['Data de Abertura'].max() - df_filtered['Data de Abertura'].min()).days if 'Data de Abertura' in df_filtered.columns else 'N/A',
                    df_filtered['Responsável'].isna().sum() if 'Responsável' in df_filtered.columns else 'N/A',
                    df_filtered['Data de Abertura'].isna().sum() if 'Data de Abertura' in df_filtered.columns else 'N/A'
                ]
            })
            st.dataframe(stats, use_container_width=True)
    
    else:
        st.warning("O arquivo carregado está vazio ou não pôde ser processado.")
else:
    st.info("Por favor, faça o upload de um arquivo para iniciar a análise.")
