import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard de Desempenho SEI", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Painel de Desempenho e Produtividade - Processos SEI")

with st.sidebar:
    st.header("📁 Upload de Dados")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV ou Excel", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        st.success("Arquivo carregado!")
    else:
        st.info("Aguardando arquivo...")

@st.cache_data
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
        else:
            df = pd.read_excel(file)
        
        # Limpeza básica
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()
        
        # Conversão de tipos
        if 'Tempo / Dias' in df.columns:
            df['Tempo / Dias'] = pd.to_numeric(df['Tempo / Dias'], errors='coerce')
        
        # Converter datas (usando 'Data de Saída')
        if 'Data de Saída' in df.columns:
            df['Data de Saída'] = pd.to_datetime(df['Data de Saída'], errors='coerce')
        
        # Padronizar responsável (apenas primeiro nome) - corrigido para garantir que nomes compostos sejam reduzidos
        if 'Responsável' in df.columns:
            df['Responsável'] = df['Responsável'].fillna('Não atribuído').astype(str)
            df['Responsável'] = df['Responsável'].apply(lambda x: x.split()[0] if len(x.split()) > 0 else x)
        
        # Garantir que a coluna de número do processo seja string
        if 'Nº Processo SEI' in df.columns:
            df['Nº Processo SEI'] = df['Nº Processo SEI'].astype(str)
        
        return df
    except Exception as e:
        st.error(f"Erro na leitura: {e}")
        return None

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None and not df.empty:
        # --- DEDUPLICAÇÃO POR PROCESSO (VALORES ÚNICOS) ---
        # Verifica se a coluna 'Nº Processo SEI' existe (com a grafia correta)
        if 'Nº Processo SEI' in df.columns:
            # Ordena por Data de Saída (mais recente primeiro) para manter a última ocorrência de cada processo
            # Se houver empates ou datas ausentes, o keep='first' manterá a primeira após a ordenação descendente
            df_sorted = df.sort_values('Data de Saída', ascending=False, na_position='last')
            df_unique = df_sorted.drop_duplicates(subset=['Nº Processo SEI'], keep='first')
            
            st.info(f"Base original: {len(df)} linhas | Após deduplicação por processo: {len(df_unique)} processos únicos.")
            df = df_unique
        else:
            st.warning("Coluna 'Nº Processo SEI' não encontrada. As contagens podem considerar linhas duplicadas.")
        
        # --- CONFIGURAÇÕES DE SITUAÇÃO ---
        with st.sidebar:
            st.header("⚙️ Configurações")
            st.markdown("Defina as palavras-chave para classificar situações:")
            
            if 'Situação' in df.columns:
                situacoes_unicas = df['Situação'].dropna().unique().tolist()
                
                col1, col2 = st.columns(2)
                with col1:
                    aberto_keywords = st.text_input(
                        "🔴 Em aberto (separadas por vírgula)",
                        value="Aberto, Em andamento, Pendente"
                    )
                with col2:
                    concluido_keywords = st.text_input(
                        "🟢 Concluído (separadas por vírgula)",
                        value="Concluído, Finalizado, Encerrado"
                    )
                
                lista_aberto = [k.strip() for k in aberto_keywords.split(',') if k.strip()]
                lista_concluido = [k.strip() for k in concluido_keywords.split(',') if k.strip()]
            else:
                st.warning("Coluna 'Situação' não encontrada.")
                lista_aberto = lista_concluido = []
            
            st.divider()
            
            # --- FILTROS INTERATIVOS ---
            st.header("🔍 Filtros")
            
            if 'Responsável' in df.columns:
                responsaveis = st.multiselect("Responsável", options=df['Responsável'].dropna().unique(), default=[])
            else:
                responsaveis = []
            
            if 'Situação' in df.columns:
                situacoes_filtro = st.multiselect("Situação (original)", options=df['Situação'].dropna().unique(), default=[])
            else:
                situacoes_filtro = []
            
            if 'Assunto' in df.columns:
                assuntos = st.multiselect("Assunto", options=df['Assunto'].dropna().unique(), default=[])
            else:
                assuntos = []
            
            if 'Etiquetas' in df.columns:
                todas_etiquetas = set()
                for tags in df['Etiquetas'].dropna():
                    for tag in str(tags).split(','):
                        todas_etiquetas.add(tag.strip())
                etiquetas = st.multiselect("Etiquetas", options=sorted(todas_etiquetas), default=[])
            else:
                etiquetas = []
            
            # Filtro de data usando 'Data de Saída'
            if 'Data de Saída' in df.columns and df['Data de Saída'].notna().any():
                min_date = df['Data de Saída'].min().date()
                max_date = df['Data de Saída'].max().date()
                date_range = st.date_input(
                    "Período (Data de Saída)",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                if len(date_range) == 2:
                    start_date, end_date = date_range
                else:
                    start_date, end_date = min_date, max_date
            else:
                start_date = end_date = None
        
        # --- APLICAÇÃO DOS FILTROS ---
        df_filtered = df.copy()
        if responsaveis:
            df_filtered = df_filtered[df_filtered['Responsável'].isin(responsaveis)]
        if situacoes_filtro:
            df_filtered = df_filtered[df_filtered['Situação'].isin(situacoes_filtro)]
        if assuntos:
            df_filtered = df_filtered[df_filtered['Assunto'].isin(assuntos)]
        if etiquetas and 'Etiquetas' in df.columns:
            mask_etiqueta = df_filtered['Etiquetas'].apply(
                lambda x: any(tag in str(x).split(',') for tag in etiquetas) if pd.notna(x) else False
            )
            df_filtered = df_filtered[mask_etiqueta]
        if start_date and end_date and 'Data de Saída' in df_filtered.columns:
            df_filtered = df_filtered[
                (df_filtered['Data de Saída'].dt.date >= start_date) &
                (df_filtered['Data de Saída'].dt.date <= end_date)
            ]
        
        # --- CLASSIFICAÇÃO DAS SITUAÇÕES ---
        if 'Situação' in df_filtered.columns and lista_aberto and lista_concluido:
            def classificar_situacao(sit):
                if pd.isna(sit):
                    return "Não classificado"
                sit_lower = str(sit).lower()
                for kw in lista_concluido:
                    if kw.lower() in sit_lower:
                        return "Concluído"
                for kw in lista_aberto:
                    if kw.lower() in sit_lower:
                        return "Em aberto"
                return "Outros"
            
            df_filtered['Classe Situação'] = df_filtered['Situação'].apply(classificar_situacao)
        else:
            df_filtered['Classe Situação'] = "Não classificado"
        
        # --- CÁLCULO DAS MÉTRICAS (sobre processos únicos) ---
        total_processos = len(df_filtered)
        abertos = (df_filtered['Classe Situação'] == "Em aberto").sum()
        concluidos = (df_filtered['Classe Situação'] == "Concluído").sum()
        outros = (df_filtered['Classe Situação'] == "Outros").sum()
        nao_class = (df_filtered['Classe Situação'] == "Não classificado").sum()
        
        # Tempo médio (considerando apenas valores >0)
        if 'Tempo / Dias' in df_filtered.columns:
            tempo_positivo = df_filtered['Tempo / Dias'].dropna()
            tempo_positivo = tempo_positivo[tempo_positivo > 0]
            tempo_medio_geral = tempo_positivo.mean() if not tempo_positivo.empty else 0
            tempo_medio_concluidos = df_filtered[df_filtered['Classe Situação'] == 'Concluído']['Tempo / Dias'].mean() or 0
        else:
            tempo_medio_geral = tempo_medio_concluidos = 0
        
        taxa_conclusao = (concluidos / total_processos * 100) if total_processos > 0 else 0
        
        # --- LINHA DE MÉTRICAS ---
        st.subheader("📈 Indicadores de Desempenho")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total de Processos (únicos)", total_processos)
        col2.metric("Em Aberto", abertos)
        col3.metric("Concluídos", concluidos)
        col4.metric("Taxa de Conclusão", f"{taxa_conclusao:.1f}%")
        col5.metric("Tempo Médio (dias)", f"{tempo_medio_geral:.1f}")
        
        st.divider()
        
        # --- ABAS ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Visão Geral", 
            "👥 Desempenho por Responsável", 
            "🏷️ Análise por Assunto/Etiquetas", 
            "📅 Evolução Temporal",
            "🔍 Detalhamento"
        ])
        
        with tab1:
            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                st.subheader("Distribuição por Situação")
                sit_counts = df_filtered['Classe Situação'].value_counts().reset_index()
                sit_counts.columns = ['Situação', 'Quantidade']
                fig_sit = px.pie(sit_counts, values='Quantidade', names='Situação',
                                 color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.3)
                fig_sit.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_sit, use_container_width=True)
            
            with row1_col2:
                st.subheader("Processos por Responsável")
                if 'Responsável' in df_filtered.columns:
                    resp_counts = df_filtered['Responsável'].value_counts().reset_index()
                    resp_counts.columns = ['Responsável', 'Quantidade']
                    fig_resp = px.bar(resp_counts, x='Responsável', y='Quantidade',
                                      color='Responsável', text='Quantidade',
                                      color_discrete_sequence=px.colors.qualitative.Set2)
                    fig_resp.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Quantidade")
                    st.plotly_chart(fig_resp, use_container_width=True)
                else:
                    st.info("Coluna 'Responsável' não encontrada.")
            
            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                st.subheader("Distribuição do Tempo de Tramitação")
                if 'Tempo / Dias' in df_filtered.columns:
                    tempo_data = df_filtered['Tempo / Dias'].dropna()
                    tempo_data = tempo_data[tempo_data > 0]
                    if not tempo_data.empty:
                        fig_hist = px.histogram(tempo_data, nbins=20, labels={'value': 'Dias', 'count': 'Frequência'},
                                               color_discrete_sequence=['#2E86AB'])
                        fig_hist.add_vline(x=tempo_medio_geral, line_dash="dash", line_color="red",
                                          annotation_text=f"Média: {tempo_medio_geral:.1f}")
                        st.plotly_chart(fig_hist, use_container_width=True)
                    else:
                        st.info("Dados de tempo insuficientes.")
                else:
                    st.info("Coluna 'Tempo / Dias' não encontrada.")
            
            with row2_col2:
                st.subheader("Tempo Médio por Responsável")
                if 'Responsável' in df_filtered.columns and 'Tempo / Dias' in df_filtered.columns:
                    tempo_resp = df_filtered.groupby('Responsável')['Tempo / Dias'].mean().reset_index()
                    tempo_resp = tempo_resp.dropna()
                    if not tempo_resp.empty:
                        fig_tempo_resp = px.bar(tempo_resp, x='Responsável', y='Tempo / Dias',
                                                color='Responsável', text_auto='.1f',
                                                color_discrete_sequence=px.colors.qualitative.Set2)
                        fig_tempo_resp.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Média de Dias")
                        st.plotly_chart(fig_tempo_resp, use_container_width=True)
                    else:
                        st.info("Dados insuficientes.")
                else:
                    st.info("Colunas necessárias não disponíveis.")
        
        with tab2:
            st.subheader("👥 Análise Detalhada por Responsável")
            if 'Responsável' in df_filtered.columns:
                resumo_resp = df_filtered.groupby('Responsável').agg(
                    Total=('Responsável', 'count'),
                    Abertos=('Classe Situação', lambda x: (x == 'Em aberto').sum()),
                    Concluidos=('Classe Situação', lambda x: (x == 'Concluído').sum()),
                    Taxa_Conclusao=('Classe Situação', lambda x: (x == 'Concluído').sum() / len(x) * 100 if len(x) > 0 else 0),
                    Tempo_Medio=('Tempo / Dias', 'mean'),
                    Min_Tempo=('Tempo / Dias', 'min'),
                    Max_Tempo=('Tempo / Dias', 'max')
                ).round(1).reset_index()
                resumo_resp.columns = ['Responsável', 'Total', 'Em Aberto', 'Concluídos',
                                      'Taxa Conclusão (%)', 'Tempo Médio (dias)', 'Mínimo (dias)', 'Máximo (dias)']
                resumo_resp['Taxa Conclusão (%)'] = resumo_resp['Taxa Conclusão (%)'].fillna(0)
                st.dataframe(resumo_resp, use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    fig_comp = go.Figure()
                    fig_comp.add_trace(go.Bar(x=resumo_resp['Responsável'], y=resumo_resp['Total'], name='Total', marker_color='lightblue'))
                    fig_comp.add_trace(go.Bar(x=resumo_resp['Responsável'], y=resumo_resp['Concluídos'], name='Concluídos', marker_color='lightgreen'))
                    fig_comp.update_layout(barmode='group', title="Total vs Concluídos por Responsável")
                    st.plotly_chart(fig_comp, use_container_width=True)
                
                with col2:
                    fig_box = px.box(df_filtered, x='Responsável', y='Tempo / Dias', color='Responsável',
                                    points='outliers', title="Distribuição do Tempo por Responsável")
                    fig_box.update_layout(showlegend=False)
                    st.plotly_chart(fig_box, use_container_width=True)
                
                st.subheader("🔎 Detalhamento Individual")
                selected_resp = st.selectbox("Selecione um responsável:", resumo_resp['Responsável'])
                if selected_resp:
                    df_resp = df_filtered[df_filtered['Responsável'] == selected_resp]
                    st.dataframe(df_resp, use_container_width=True)
            else:
                st.info("Coluna 'Responsável' não encontrada.")
        
        with tab3:
            st.subheader("🏷️ Análise por Assunto e Etiquetas")
            if 'Assunto' in df_filtered.columns:
                col_left, col_right = st.columns(2)
                with col_left:
                    top_n = st.slider("Top N assuntos", 5, 20, 10)
                    assunto_counts = df_filtered['Assunto'].value_counts().head(top_n).reset_index()
                    assunto_counts.columns = ['Assunto', 'Quantidade']
                    fig_assunto = px.bar(assunto_counts, y='Assunto', x='Quantidade', orientation='h',
                                        color='Quantidade', color_continuous_scale='Blues', title=f"Top {top_n} Assuntos")
                    fig_assunto.update_layout(yaxis_title=None)
                    st.plotly_chart(fig_assunto, use_container_width=True)
                with col_right:
                    if len(df_filtered['Assunto'].unique()) > 1:
                        assuntos_sit = pd.crosstab(df_filtered['Assunto'], df_filtered['Classe Situação']).reset_index().melt(
                            id_vars='Assunto', var_name='Situação', value_name='Quantidade')
                        top_assuntos_list = assunto_counts['Assunto'].tolist()
                        assuntos_sit = assuntos_sit[assuntos_sit['Assunto'].isin(top_assuntos_list)]
                        fig_assunto_sit = px.bar(assuntos_sit, x='Assunto', y='Quantidade', color='Situação',
                                                barmode='stack', title="Distribuição dos Assuntos por Situação")
                        st.plotly_chart(fig_assunto_sit, use_container_width=True)
                    else:
                        st.info("Poucos assuntos para análise cruzada.")
            
            if 'Etiquetas' in df_filtered.columns:
                st.subheader("Análise de Etiquetas")
                df_tags = df_filtered.dropna(subset=['Etiquetas']).copy()
                if not df_tags.empty:
                    tags_exploded = df_tags.assign(Etiqueta=df_tags['Etiquetas'].str.split(',')).explode('Etiqueta')
                    tags_exploded['Etiqueta'] = tags_exploded['Etiqueta'].str.strip()
                    tag_counts = tags_exploded['Etiqueta'].value_counts().reset_index()
                    tag_counts.columns = ['Etiqueta', 'Quantidade']
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        top_tags = tag_counts.head(15)
                        fig_tags = px.bar(top_tags, y='Etiqueta', x='Quantidade', orientation='h',
                                         color='Quantidade', color_continuous_scale='Viridis', title="Top 15 Etiquetas")
                        st.plotly_chart(fig_tags, use_container_width=True)
                    with col2:
                        tag_tempo = tags_exploded.groupby('Etiqueta')['Tempo / Dias'].mean().reset_index()
                        tag_tempo = tag_tempo.dropna().sort_values('Tempo / Dias', ascending=False).head(15)
                        fig_tag_tempo = px.bar(tag_tempo, y='Etiqueta', x='Tempo / Dias', orientation='h',
                                              color='Tempo / Dias', color_continuous_scale='Reds', title="Tempo Médio por Etiqueta")
                        st.plotly_chart(fig_tag_tempo, use_container_width=True)
                    
                    selected_tag = st.selectbox("Selecione uma etiqueta:", tag_counts['Etiqueta'].head(20))
                    if selected_tag:
                        mask = df_filtered['Etiquetas'].apply(
                            lambda x: selected_tag in str(x).split(',') if pd.notna(x) else False
                        )
                        df_tag_filtered = df_filtered[mask]
                        st.dataframe(df_tag_filtered, use_container_width=True)
                else:
                    st.info("Nenhuma etiqueta preenchida.")
            else:
                st.info("Coluna 'Etiquetas' não encontrada.")
        
        with tab4:
            st.subheader("📅 Evolução Temporal (baseada em Data de Saída)")
            if 'Data de Saída' in df_filtered.columns:
                df_time = df_filtered.dropna(subset=['Data de Saída']).copy()
                if not df_time.empty:
                    df_time['Mês'] = df_time['Data de Saída'].dt.to_period('M').astype(str)
                    monthly_open = df_time.groupby('Mês').size().reset_index(name='Processos')
                    
                    fig_time = px.line(monthly_open, x='Mês', y='Processos', markers=True,
                                      line_shape='linear', color_discrete_sequence=['#2E86AB'],
                                      title="Processos por Mês (Data de Saída)")
                    fig_time.update_layout(xaxis_title="Mês", yaxis_title="Quantidade")
                    st.plotly_chart(fig_time, use_container_width=True)
                    
                    df_time_sorted = df_time.sort_values('Data de Saída')
                    df_time_sorted['Acumulado'] = range(1, len(df_time_sorted) + 1)
                    fig_acum = px.area(df_time_sorted, x='Data de Saída', y='Acumulado',
                                      title="Acumulado de Processos", labels={'Data de Saída': 'Data'})
                    st.plotly_chart(fig_acum, use_container_width=True)
                    
                    st.subheader("Distribuição por Dia da Semana")
                    df_time['Dia da Semana'] = df_time['Data de Saída'].dt.day_name()
                    weekday_counts = df_time['Dia da Semana'].value_counts().reindex(
                        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    ).reset_index()
                    weekday_counts.columns = ['Dia', 'Quantidade']
                    fig_weekday = px.bar(weekday_counts, x='Dia', y='Quantidade', color='Quantidade',
                                        color_continuous_scale='Blues')
                    st.plotly_chart(fig_weekday, use_container_width=True)
                else:
                    st.info("Sem datas válidas.")
            else:
                st.info("Coluna 'Data de Saída' não encontrada.")
        
        with tab5:
            st.subheader("🔍 Detalhamento dos Processos")
            st.dataframe(df_filtered, use_container_width=True)
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download CSV", data=csv, file_name='dados_filtrados.csv', mime='text/csv')
    
    else:
        st.warning("Arquivo vazio ou não pôde ser processado.")
else:
    st.info("Por favor, faça o upload de um arquivo.")

st.markdown("---")
st.markdown("Dashboard desenvolvido para análise de desempenho e produtividade de processos SEI.")
