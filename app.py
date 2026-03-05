import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard KPIs SEI", layout="wide")

def parse_sheet_data(df):
    """
    Função para extrair dados da estrutura:
    Linha 0: Labels (Despacho, Aberto na Unidade, etc)
    Linha 1: Valores numéricos
    """
    try:
        # A primeira linha de dados do DF (index 0) contém os nomes das categorias
        # A segunda linha de dados do DF (index 1) contém os valores
        labels = df.iloc[0]
        values = df.iloc[1]
        
        data = {
            "Total": int(values[0]) if pd.notnull(values[0]) else 0,
            "Tipo": {
                str(labels[1]).strip(): int(values[1]) if pd.notnull(values[1]) else 0,
                str(labels[2]).strip(): int(values[2]) if pd.notnull(values[2]) else 0,
            },
            "Situação": {
                str(labels[3]).strip(): int(values[3]) if pd.notnull(values[3]) else 0,
                str(labels[4]).strip(): int(values[4]) if pd.notnull(values[4]) else 0,
                str(labels[5]).strip(): int(values[5]) if pd.notnull(values[5]) else 0,
            },
            "Tempo": {
                str(labels[6]).strip(): int(values[6]) if pd.notnull(values[6]) else 0,
                str(labels[7]).strip(): int(values[7]) if pd.notnull(values[7]) else 0,
                str(labels[8]).strip(): int(values[8]) if pd.notnull(values[8]) else 0,
            }
        }
        return data
    except Exception:
        return None

st.title("Monitoramento SEI")
st.markdown("---")

# Upload do arquivo único com várias abas
uploaded_file = st.sidebar.file_uploader("Carregar arquivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    # Carregar o arquivo Excel e listar as abas
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    
    # Dicionário para armazenar dados de todas as abas
    all_data = {}
    for sheet in sheet_names:
        df_sheet = pd.read_excel(xls, sheet_name=sheet)
        parsed = parse_sheet_data(df_sheet)
        if parsed:
            all_data[sheet] = parsed

    if all_data:
        # Seletor de Período (Abas)
        selected_period = st.sidebar.selectbox("Selecione o Período (Aba):", list(all_data.keys()))
        kpis = all_data[selected_period]

        # --- MÉTRICAS DE DESTAQUE ---
        st.subheader(f"Indicadores: {selected_period}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Processos", kpis["Total"])
        m2.metric("Despachos", kpis["Tipo"].get("Despacho", 0))
        m3.metric("Ofícios", kpis["Tipo"].get("Ofício", 0))
        # Busca flexível por "Processo concluído" para evitar erros de espaços extras
        concluidos = next((v for k, v in kpis["Situação"].items() if "concluído" in k.lower()), 0)
        m4.metric("Concluídos", concluidos)

        st.markdown("---")

        # --- GRÁFICOS ---
        col1, col2 = st.columns(2)

        with col1:
            st.write("### Composição por Tipo")
            df_tipo = pd.DataFrame(list(kpis["Tipo"].items()), columns=["Tipo", "Qtd"])
            fig_tipo = px.pie(df_tipo, names="Tipo", values="Qtd", hole=0.4, 
                              color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_tipo, use_container_width=True)

        with col2:
            st.write("### Tempo de Tramitação")
            df_tempo = pd.DataFrame(list(kpis["Tempo"].items()), columns=["Faixa", "Qtd"])
            fig_tempo = px.bar(df_tempo, x="Faixa", y="Qtd", color="Faixa", text_auto=True)
            st.plotly_chart(fig_tempo, use_container_width=True)

        st.write("### Situação Atual")
        df_sit = pd.DataFrame(list(kpis["Situação"].items()), columns=["Situação", "Qtd"])
        fig_sit = px.bar(df_sit, x="Qtd", y="Situação", orientation='h', 
                         color="Situação", text_auto=True)
        st.plotly_chart(fig_sit, use_container_width=True)

        # --- COMPARATIVO ENTRE ABAS ---
        if len(all_data) > 1:
            st.markdown("---")
            st.subheader("Evolução entre os Períodos")
            evol_list = [{"Mês": k, "Total": v["Total"]} for k, v in all_data.items()]
            df_evol = pd.DataFrame(evol_list)
            fig_evol = px.line(df_evol, x="Mês", y="Total", markers=True, title="Total de Processos por Aba")
            st.plotly_chart(fig_evol, use_container_width=True)
    else:
        st.error("Não foi possível encontrar dados no formato esperado nas abas deste arquivo.")

else:
    st.info("Aguardando upload do arquivo Excel com as abas de período.")