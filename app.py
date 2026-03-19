import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard KPIs SEI", layout="wide", page_icon="📊")

def parse_sheet_data(df):
    """
    Função adaptada para extrair dados. 
    Tenta ler a primeira linha como valores se as colunas forem os labels.
    """
    try:
        # Se o DataFrame estiver vazio, ignora
        if df.empty:
            return None
        
        # Caso 1: A planilha tem cabeçalhos (Labels) e os dados estão na primeira linha
        labels = df.columns.tolist()
        values = df.iloc[0].tolist()

        # Limpeza simples de espaços nos nomes das colunas
        labels = [str(l).strip() for l in labels]

        # Mapeamento dinâmico baseado em palavras-chave para ser mais resiliente
        def get_val(keyword, default=0):
            for i, label in enumerate(labels):
                if keyword.lower() in label.lower():
                    val = values[i]
                    return int(val) if pd.notnull(val) else 0
            return default

        data = {
            "Total": values[0] if pd.notnull(values[0]) else 0,
            "Tipo": {
                "Despacho": get_val("Despacho"),
                "Ofício": get_val("Ofício"),
                "Parecer": get_val("Parecer") # Adicionado como exemplo
            },
            "Situação": {
                "Abertos": get_val("Aberto"),
                "Concluídos": get_val("concluído"),
                "Sobrestados": get_val("sobrestado"),
            },
            "Tempo": {
                "0-5 dias": get_val("0-5") or get_val("Até 5"),
                "6-15 dias": get_val("6-15"),
                "15+ dias": get_val("mais de 15") or get_val(">15"),
            }
        }
        return data
    except Exception as e:
        st.error(f"Erro ao processar aba: {e}")
        return None

st.title("📊 Monitoramento de Indicadores SEI")
st.markdown("Visualize o desempenho e tramitação de processos de forma intuitiva.")

# Sidebar para Upload
st.sidebar.header("Configurações")
uploaded_file = st.sidebar.file_uploader("Carregar arquivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    
    all_data = {}
    for sheet in sheet_names:
        # Lendo a aba - Ajuste 'header=0' se a primeira linha for o título das colunas
        df_sheet = pd.read_excel(xls, sheet_name=sheet)
        parsed = parse_sheet_data(df_sheet)
        if parsed:
            all_data[sheet] = parsed

    if all_data:
        selected_period = st.sidebar.selectbox("Selecione o Período (Aba):", list(all_data.keys()))
        kpis = all_data[selected_period]

        # --- MÉTRICAS DE DESTAQUE ---
        st.subheader(f"📍 Indicadores: {selected_period}")
        m1, m2, m3, m4 = st.columns(4)
        
        m1.metric("Total de Processos", kpis["Total"])
        m2.metric("Despachos", kpis["Tipo"].get("Despacho", 0))
        m3.metric("Ofícios", kpis["Tipo"].get("Ofício", 0))
        m4.metric("Concluídos", kpis["Situação"].get("Concluídos", 0))

        st.markdown("---")

        # --- GRÁFICOS ---
        col1, col2 = st.columns(2)

        with col1:
            st.write("### 🍰 Composição por Tipo")
            # Filtra apenas itens com valor > 0 para o gráfico não ficar poluído
            tipos_filtrados = {k: v for k, v in kpis["Tipo"].items() if v > 0}
            if tipos_filtrados:
                df_tipo = pd.DataFrame(list(tipos_filtrados.items()), columns=["Tipo", "Qtd"])
                fig_tipo = px.pie(df_tipo, names="Tipo", values="Qtd", hole=0.4, 
                                 color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_tipo, use_container_width=True)
            else:
                st.info("Sem dados de 'Tipo' para exibir.")

        with col2:
            st.write("### ⏱️ Tempo de Tramitação")
            tempos_filtrados = {k: v for k, v in kpis["Tempo"].items() if v > 0}
            if tempos_filtrados:
                df_tempo = pd.DataFrame(list(tempos_filtrados.items()), columns=["Faixa", "Qtd"])
                fig_tempo = px.bar(df_tempo, x="Faixa", y="Qtd", color="Faixa", 
                                  text_auto=True, color_discrete_sequence=px.colors.sequential.Viridis)
                st.plotly_chart(fig_tempo, use_container_width=True)
            else:
                st.info("Sem dados de 'Tempo' para exibir.")

        st.write("### 📂 Situação Atual dos Processos")
        situacao_filtrada = {k: v for k, v in kpis["Situação"].items() if v > 0}
        if situacao_filtrada:
            df_sit = pd.DataFrame(list(situacao_filtrada.items()), columns=["Situação", "Qtd"])
            fig_sit = px.bar(df_sit, x="Qtd", y="Situação", orientation='h', 
                             color="Situação", text_auto=True, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_sit, use_container_width=True)

        # --- COMPARATIVO ENTRE ABAS ---
        if len(all_data) > 1:
            st.markdown("---")
            st.subheader("📈 Evolução Temporal")
            evol_list = [{"Período": k, "Total": v["Total"]} for k, v in all_data.items()]
            df_evol = pd.DataFrame(evol_list)
            fig_evol = px.line(df_evol, x="Período", y="Total", markers=True, 
                              line_shape="spline", title="Evolução do Volume de Processos")
            st.plotly_chart(fig_evol, use_container_width=True)
            
    else:
        st.error("Formato de dados não reconhecido. Verifique se as abas contêm as informações nas primeiras linhas.")

else:
    st.info("👆 Por favor, carregue o arquivo Excel para gerar o Dashboard.")
