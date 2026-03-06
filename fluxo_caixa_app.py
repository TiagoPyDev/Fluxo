import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Fluxo de Caixa Real")
st.title("💰 Dashboard de Fluxo de Caixa Real")

# --- Funções de Processamento ---

@st.cache_data
def carregar_dados(uploaded_file):
    """Carrega as abas 'Painel' e 'Base' de um arquivo Excel."""
    if uploaded_file is not None:
        try:
            df_painel = pd.read_excel(uploaded_file, sheet_name='Painel', header=None)
            df_base = pd.read_excel(uploaded_file, sheet_name='Base')
            return df_painel, df_base
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}. Certifique-se de que as abas 'Painel' e 'Base' existem.")
            return None, None
    return None, None

def processar_painel(df_painel):
    """Extrai a estrutura de contas e os saldos iniciais do painel."""
    # Encontrar a linha de cabeçalho (onde começam as datas)
    header_row_idx = None
    for idx, row in df_painel.iterrows():
        if pd.notna(row[1]) and '2025-01-01' in str(row.values):
            header_row_idx = idx
            break

    if header_row_idx is None:
        st.error("Não foi possível encontrar a linha de cabeçalho com as datas no painel.")
        return None, None, None

    # Definir o cabeçalho
    df_painel.columns = df_painel.iloc[header_row_idx]
    df_painel = df_painel[header_row_idx+1:].reset_index(drop=True)
    df_painel = df_painel.dropna(how='all').reset_index(drop=True)

    # Extrair Saldo Inicial (assumindo que a primeira coluna é a descrição)
    saldo_inicial_row = df_painel[df_painel.iloc[:, 0] == 'SALDO INICIAL']
    if not saldo_inicial_row.empty:
        # O saldo inicial está na coluna de '2025-01-01' (índice 2)
        saldo_inicial_val = pd.to_numeric(saldo_inicial_row.iloc[0, 2], errors='coerce')
        if pd.isna(saldo_inicial_val):
            saldo_inicial_val = 0.0
    else:
        saldo_inicial_val = 0.0

    return df_painel, saldo_inicial_val, header_row_idx

def processar_base(df_base):
    """Limpa e prepara a base de dados de lançamentos."""
    df_base.columns = [str(col).strip().upper() for col in df_base.columns]

    col_map = {
        'DT.PAGTO.': 'Dt.pagto',
        'DT.PAGTO': 'Dt.pagto',
        'VL.RATEADO': 'Vl.rateado',
        'FANTASIA': 'Fantasia',
        'SEGMENTO': 'Segmento'
    }
    df_base.rename(columns=col_map, inplace=True)

    if 'Dt.pagto' not in df_base.columns or 'Vl.rateado' not in df_base.columns:
        st.error("A base de dados não contém as colunas 'Dt.pagto' ou 'Vl.rateado'.")
        return None

    # Converter data
    df_base['Dt.pagto'] = pd.to_datetime(df_base['Dt.pagto'], errors='coerce', dayfirst=False)
    df_base = df_base.dropna(subset=['Dt.pagto', 'Vl.rateado']).copy()
    df_base['Ano-Mês'] = df_base['Dt.pagto'].dt.to_period('M').astype(str)

    # Converter valores
    df_base['Vl.rateado'] = pd.to_numeric(df_base['Vl.rateado'], errors='coerce').fillna(0)

    # Mapear contas (códigos) para suas categorias de nível superior (ex: 41101 -> SALARIOS E ENCARGOS)
    # Esta é uma simplificação. O ideal seria pegar essa hierarquia do Painel.
    df_base['Categoria'] = df_base['Segmento'].astype(str).str[:5]

    # Preencher nulos
    df_base['Fantasia'] = df_base['Fantasia'].fillna('Outros')
    df_base['Segmento'] = df_base['Segmento'].fillna('Outros')

    return df_base

def construir_painel_filtrado(df_painel, df_base_filtrado, meses):
    """Constrói o painel de fluxo de caixa dinamicamente a partir da estrutura do painel."""
    linhas_relevantes = []
    for index, row in df_painel.iterrows():
        descricao = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        if descricao and descricao not in ['', 'nan', 'CAIXA EFETIVO', 'CAIXA EFETIVO ACUMULADO']:
            linhas_relevantes.append(index)

    painel_df = df_painel.iloc[linhas_relevantes].copy()
    painel_df.reset_index(drop=True, inplace=True)

    # Pegar apenas as linhas com descrição e código (linhas de totais e detalhes)
    painel_df = painel_df[painel_df.iloc[:, 0].notna()].copy()

    resultado = pd.DataFrame()
    resultado['Descrição'] = painel_df.iloc[:, 0].astype(str).str.strip()
    # A primeira coluna numérica (índice 2) é o início dos meses
    meses_col_indices = range(2, len(painel_df.columns))

    for col_idx in meses_col_indices:
        mes = painel_df.columns[col_idx]
        if pd.isna(mes) or 'Unnamed' in str(mes):
            continue

        mes_str = str(mes)
        if mes_str not in meses:
            continue

        valores_mes = []
        for _, row in painel_df.iterrows():
            # Se for uma linha de total (começa com número e espaço) ou uma linha de detalhe (começa com ponto)
            desc = str(row.iloc[0])
            codigo_conta = desc.split()[0] if desc and desc[0].isdigit() else None

            if codigo_conta:
                # Filtrar a base pelo código da conta
                mask_categoria = df_base_filtrado['Segmento'].astype(str).str.startswith(codigo_conta)
                valor_filtrado = df_base_filtrado.loc[mask_categoria, 'Vl.rateado'].sum()
                valores_mes.append(valor_filtrado)
            else:
                # Linha de título (ex: RECEITAS TOTAL), manter o valor do painel original (não usaremos)
                # Vamos usar a soma dos filhos para calcular os totais posteriormente.
                valores_mes.append(0)  # Placeholder, será recalculado

        resultado[mes_str] = valores_mes

    return resultado

def calcular_saldos(painel_valores, saldo_inicial, meses, df_base_filtrado):
    """Calcula os saldos com base nos fluxos filtrados."""
    saldos = []
    saldo_acumulado = saldo_inicial

    for i, mes in enumerate(meses):
        # Encontrar a linha de "SALDO INICIAL" e "SALDO FINAL"
        fluxo_liquido = 0
        # Somar todas as entradas e saídas (linhas que não são títulos)
        # Vamos pegar a soma de todos os valores, já que as contas de receita são positivas e despesas negativas
        fluxo_liquido = painel_valores[mes].sum()

        # Adicionar o saldo inicial no primeiro mês
        if i == 0:
            saldo_final = saldo_inicial + fluxo_liquido
        else:
            saldo_final = saldo_acumulado + fluxo_liquido

        saldos.append({'Mês': mes, 'Saldo Inicial': saldo_acumulado, 'Fluxo Líquido': fluxo_liquido, 'Saldo Final': saldo_final})
        saldo_acumulado = saldo_final

    return pd.DataFrame(saldos)

# --- Interface Streamlit ---
st.sidebar.header("📂 Upload e Filtros")

uploaded_file = st.sidebar.file_uploader("Carregar arquivo Excel (abas: Painel e Base)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    # Carregar dados
    df_painel_raw, df_base_raw = carregar_dados(uploaded_file)

    if df_painel_raw is not None and df_base_raw is not None:
        # Processar base
        df_base = processar_base(df_base_raw)
        if df_base is None:
            st.stop()

        # Processar painel para obter saldo inicial e estrutura
        df_painel_estrutura, saldo_inicial_val, header_idx = processar_painel(df_painel_raw)

        if df_painel_estrutura is None:
            st.stop()

        st.sidebar.success("Dados carregados com sucesso!")

        # --- Filtros ---
        empresas = sorted(df_base['Fantasia'].dropna().unique())
        clientes = sorted(df_base['Segmento'].dropna().unique())
        datas_disponiveis = sorted(df_base['Ano-Mês'].unique())

        with st.sidebar:
            st.subheader("🔍 Filtros")
            empresas_selecionadas = st.multiselect("Empresa (Fantasia)", empresas, default=empresas)
            clientes_selecionados = st.multiselect("Cliente (Segmento)", clientes, default=clientes)
            data_range = st.select_slider(
                "Período",
                options=datas_disponiveis,
                value=(datas_disponiveis[0], datas_disponiveis[-1]) if datas_disponiveis else (None, None)
            )

        # Aplicar filtros
        df_filtrado = df_base.copy()
        if empresas_selecionadas:
            df_filtrado = df_filtrado[df_filtrado['Fantasia'].isin(empresas_selecionadas)]
        if clientes_selecionados:
            df_filtrado = df_filtrado[df_filtrado['Segmento'].isin(clientes_selecionados)]
        if data_range[0] and data_range[1]:
            df_filtrado = df_filtrado[(df_filtrado['Ano-Mês'] >= data_range[0]) & (df_filtrado['Ano-Mês'] <= data_range[1])]

        meses_no_periodo = sorted(df_filtrado['Ano-Mês'].unique())

        if not meses_no_periodo:
            st.warning("Nenhum dado encontrado para o período e filtros selecionados.")
            st.stop()

        # Construir painel de valores
        painel_valores = construir_painel_filtrado(df_painel_estrutura, df_filtrado, meses_no_periodo)

        # Calcular totais por categoria (linhas de título como RECEITAS TOTAL, etc.)
        # Isso é complexo de fazer automaticamente sem a hierarquia. Vamos mostrar as contas individuais.
        st.subheader("📊 Fluxo de Caixa Detalhado")

        # Exibir o painel
        col_config = {"Descrição": st.column_config.TextColumn("Descrição", width="large")}
        for mes in meses_no_periodo:
            col_config[mes] = st.column_config.NumberColumn(mes, format="R$ %.2f")

        st.dataframe(painel_valores, use_container_width=True, column_config=col_config)

        # Calcular e mostrar saldos
        st.divider()
        st.subheader("📈 Evolução do Saldo")

        df_saldos = calcular_saldos(painel_valores, saldo_inicial_val, meses_no_periodo, df_filtrado)

        # Gráfico
        fig = px.line(df_saldos, x='Mês', y=['Saldo Inicial', 'Saldo Final'],
                      title="Saldo Inicial vs Final por Mês",
                      markers=True, template="plotly_white")
        fig.update_layout(yaxis_title="Valor (R$)")
        st.plotly_chart(fig, use_container_width=True)

        # Tabela de saldos
        st.dataframe(df_saldos.style.format({
            'Saldo Inicial': 'R$ {:,.2f}',
            'Fluxo Líquido': 'R$ {:,.2f}',
            'Saldo Final': 'R$ {:,.2f}'
        }), use_container_width=True, hide_index=True)

        # Resumo Executivo
        st.divider()
        st.subheader("📋 Resumo Executivo")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Saldo Inicial (Período)", f"R$ {df_saldos['Saldo Inicial'].iloc[0]:,.2f}")
        with col2:
            st.metric("Fluxo Líquido Total (Período)", f"R$ {df_saldos['Fluxo Líquido'].sum():,.2f}")
        with col3:
            st.metric("Saldo Final (Período)", f"R$ {df_saldos['Saldo Final'].iloc[-1]:,.2f}")

else:
    st.info("👈 Carregue o arquivo Excel no menu lateral para começar.")
    st.markdown("""
    **Formato esperado do arquivo:**
    - Aba **Painel**: Estrutura do fluxo de caixa (linhas de conta, datas no cabeçalho, valores totais).
    - Aba **Base**: Lançamentos individuais com colunas como 'Dt.pagto', 'Vl.rateado', 'Fantasia', 'Segmento' (código da conta).
    """)
