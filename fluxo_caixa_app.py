import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import io

# Set page configuration
st.set_page_config(
    page_title="Fluxo de Caixa Real - Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .positive {
        color: #10b981;
        font-weight: bold;
    }
    .negative {
        color: #ef4444;
        font-weight: bold;
    }
    .stDataFrame {
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# MODELO DO PAINEL (estrutura fixa baseada no arquivo anexo)
# ============================================================================
def criar_modelo_painel():
    """
    Cria a estrutura do painel de fluxo de caixa com base no modelo do arquivo anexo.
    Esta função define a estrutura fixa que será preenchida com os dados da base.
    """
    
    # Datas para o painel (12 meses + 1 futuro)
    datas = []
    for i in range(1, 13):
        datas.append(datetime(2025, i, 1))
    datas.append(datetime(2026, 1, 1))  # Janeiro/2026
    
    # Estrutura do painel (linhas)
    estrutura_painel = [
        "SALDO INICIAL",
        "",
        "RECEITAS TOTAL",
        "FATURAMENTO",
        "FATURAMENTO - devedores",
        "INSS RETIDO EM NOTA",
        "DEPOSITO A IDENTIFICAR",
        "",
        "IMPOSTOS SOBRE VENDAS",
        ". ISS",
        ". PIS",
        ". COFINS",
        ". DEPÓSITO JUDICIAL",
        "",
        "DESEMBOLSOS FIXOS  E VARIÁVEIS",
        "SALARIOS E ENCARGOS",
        ". SALÁRIOS",
        ". HORAS EXTRAS",
        ". FÉRIAS",
        ". 13º SALÁRIO",
        ". FOLGA TRABALHADA",
        ". FÉRIAS TRABALHADAS",
        ". REMUNERAÇÃO SÓCIOS",
        ". PLR/PRÊMIOS",
        ". FAP",
        ". INSS-AVISO INDENIZADO",
        ". FGTS FOLHA",
        ". INSS FOLHA",
        ". RESCISÃO CONTRATUAL",
        "BENEFÍCIOS",
        ". VALE REFEIÇÃO",
        ". VALE TRANSPORTE",
        ". CESTA BÁSICA",
        ". PLANO DE SAÚDE",
        ". ASSISTÊNCIA ADONTOLOGICA",
        ". FARMÁCIA E MEDICAMENTOS",
        ". CESTA BÁSCIA COMPLEMENTAR",
        ". SEGURO DE VIDA EM GRUPO",
        ". CURSOS/TREINAMENTOS - EXTERNO",
        ". CURSOS/TREINAMENTOS - INTERNOS",
        ". ROUPAS E EQUIP TRABALHO",
        ". CONVÊNIO FUNCIONÁRIOS",
        ". PRÊMIO ASSIDUIDADE/BOA PERMANE",
        "ASPECTOS TRABALHISTAS",
        ". MULTA FGTS",
        ". ACORDOS TRABALHISTAS",
        ". INDENIZAÇÕES",
        ". PERÍCIA MÉDICA",
        ". DESPESAS - AUDIÊNCIAS",
        "CUSTOS DE ADMISSÃO",
        ". ANÚNCIOS/AGÊNCIA DE EMPREGO",
        ". EXAMES MÉDICOS",
        ". EXAMES PSICOTÉCNICOS",
        ". PESQUISAS E INVESTIGAÇÕES",
        "MÃO DE OBRA TERCEIROS",
        ". MÃO DE OBRA TERCEIROS",
        ". OUTROS CUSTOS",
        "ENERGIAS",
        ". ENERGIA ELETRICA",
        ". AGUA",
        "MANUTENÇÃO",
        ". MANUTENÇÃO UNIFORMES",
        ". MANUTENÇÃO MÁQUINAS E EQUIP",
        ". MANUT VEÍCULOS/SINISTRO INTERN",
        ". MANUTENÇÃO PREDIAL",
        ". MANUTENÇÃO ESCRITÓRIO",
        ". MANUTENÇÃO REDE TELEFÔNICA",
        ". MANUTENÇÃO E EQUIP INFORMATICA",
        ". MATERIAIS CONSUMO MANUTENÇÃO",
        ". SERV. PRESTADOS 3º MANUTENÇÃO",
        ". FRETES S/ COMPRAS MAT MANUTEN",
        "MATERIAL DE LIMPEZA",
        ". MATERIAL DE LIMPEZA",
        "ALUGUÉIS",
        ". ALUGUÉIS DE IMÓVEIS",
        ". ALUGUÉIS DE VEÍCULOS",
        ". ALUGUEL DE MÁQ E EQUIPAMENTOS",
        ". ALUGUEL DE MÓVEIS E UTENSÍLIOS",
        "DESPESAS COM VEÍCULOS",
        ". COMBUSTÍVEIS",
        ". LICENC/SEGURO/SEG OBR/DPVAT/IN",
        ". MULTAS DE VEÍCULOS",
        ". MONITORAMENTO VEÍCULOS",
        ". COMUNICAÇÃO VISUAL",
        "IMPOSTOS, TAXAS E SEGUROS",
        ". RENOVAÇÃO CERTIFICADO/VISTORIA",
        ". TAXAS (MUNICIPAL/ESTADUAL/FEDE",
        ". SEGURO EMPRESARIAL",
        ". SEGURO RESPONSABILIDADE CIVIL",
        ". CONTR SINDICAL/ASSOCIAÇOES",
        ". IPTU",
        "COMUNICAÇÕES",
        ". MOTOBOY",
        ". CORREIO",
        ". TELECOMUNICAÇÕES - TEL FIXO",
        ". TELECOMUNICAÇÕES - CELULAR",
        ". NEXTEL/CLARO",
        ". LINHA PROCESSAMENTO",
        ". INTERNET",
        "VIAGENS E LOCOMOÇÃO",
        ". VIAGENS E ESTADIAS",
        ". PEDÁGIO",
        ". TAXI/ÔNIBUS/ESTACIONAMENTO",
        ". LANCHES E REFEIÇÕES",
        ". AJUDA DE CUSTO-REPRESENTANTES",
        "ADMINISTRAÇÃO",
        ". FORMAÇÃO PESSOAL/TREINAMENTO",
        ". BRINDES/DOAÇÕES/EVENTOS INTERN",
        ". CAFÉ/AGUA/MATERIAL COPA",
        ". MATERIAL DE CONSUMO DIVERSOS",
        ". DESPESAS LEGAIS/JUD/CARTORIO",
        ". IMPRESSOS E MATERIAL DE ESCRIT",
        ". ASSINATURAS DIVERSAS",
        ". MOTO BOY",
        ". BENS PEQ VALOR/MATERIAL POSTO",
        ". MULTAS INDEDUTIVEIS",
        ". OUTRAS DESPESAS INDEDUTÍVEIS",
        "SERVIÇOS CONTRATADOS",
        ". ASSESSORIA ADMINISTRATIVA",
        ". ASSESSORIA CONTÁBIL",
        ". ASSESSORIA JURÍDICA",
        ". ASSESSORIA TÉCNICA",
        ". SERVIÇOS PRESTADOS 3º - PF",
        ". SERVIÇOS PRESTADOS 3º - PJ",
        "COMISSÕES",
        ". COMISSÕES REPRESENTANTES",
        ". OUTRAS COMISSÕES",
        "DESPESAS COM MARKETING",
        ". PUBLICIDADE E PROPAGANDA",
        ". JORNAIS E REVISTAS",
        ". FEIRA E EVENTOS",
        ". NOVOS PROJETOS/EXPANSÃO/PESQUI",
        "DESPESAS COM CLIENTES",
        ". PERDAS COM CLIENTES",
        ". BRINDES PARA CLIENTES",
        ". INDENIZAÇÕES COM CLIENTES",
        ". CMV - MODELO MGV - ANTIGO PDD",
        "",
        "OUTRAS ENTRADAS / SAÍDAS QUE NÃO AFETAM O DRE",
        "OUTROS IMPOSTOS",
        ". INTERCOMPANY SUPERVISÃO SIA",
        ". INTERCOMPANY PROPAR / SIA",
        ". NTERCOMPANY PROPAR / PRO",
        ". INTERCOMPANY PROPAR / PRO CLEAN",
        "IR",
        "CSLL",
        "REFIS",
        "OUTRAS SAÍDAS",
        ". DEPÓSITO RECURSAL/Simples Sensor",
        ". BLOQUEIO JUDICIAL",
        "INVESTIMENTOS",
        ". SOFTWARE",
        ". MAQUINAS E EQUIPAMENTOS",
        ". MÓVEIS E UTENSÍLIOS",
        ". VEÍCULOS / IMÓVEIS",
        ". APORTE/AQUISIÇÃO DE EMPRESAS",
        "DISTRIBUIÇÃO",
        "RESCISÃO FÁBIO",
        "DISTRIBUIÇÃO DIVIDENDOS",
        "",
        "ENTRADAS / SAÍDAS FINANCEIRAS",
        ". RECEITAS FINANCEIRAS",
        ". CCB - CÉDULA CRÉDITO BANCÁRIO - CREDITO",
        ". CCB - CÉDULA CRÉDITO BANCÁRIO - DEBITO",
        ". RECEITA FINANCEIRA CCB",
        ". DESP BANCÁRIAS/BLOQUEIO JUD/IR S/ APLICAÇÕES",
        "",
        "Transferência entre empresas",
        "",
        "SALDO FINAL",
        "",
        "CAIXA EFETIVO",
        "",
        "CAIXA EFETIVO ACUMULADO"
    ]
    
    # Criar DataFrame vazio do painel
    df_painel = pd.DataFrame(index=estrutura_painel)
    
    # Adicionar colunas de data
    for i, data in enumerate(datas):
        col_name = data.strftime('%Y-%m')
        df_painel[col_name] = 0.0
    
    return df_painel, datas

# ============================================================================
# FUNÇÕES DE PROCESSAMENTO
# ============================================================================
@st.cache_data
def carregar_dados_base(uploaded_file):
    """Carrega e processa o arquivo de base Excel"""
    try:
        # Ler o arquivo Excel, especificando a aba 'Base'
        df_base = pd.read_excel(uploaded_file, sheet_name='Base', engine='openpyxl')
        return df_base
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return None

def processar_base_para_painel(df_base, df_painel, datas, filtros=None):
    """
    Processa os dados da base e preenche o painel.
    Aplica filtros de empresa, cliente e data quando fornecidos.
    """
    # Criar cópia para não modificar o original
    df_painel_filled = df_painel.copy()
    df_base_filtered = df_base.copy() if df_base is not None else pd.DataFrame()
    
    # Aplicar filtros se fornecidos
    if filtros and df_base_filtered is not None and not df_base_filtered.empty:
        if 'Empresa' in filtros and filtros['Empresa'] and 'Fantasia' in df_base_filtered.columns:
            df_base_filtered = df_base_filtered[df_base_filtered['Fantasia'].str.contains(filtros['Empresa'], na=False, case=False)]
        
        if 'Cliente' in filtros and filtros['Cliente'] and 'Fantasia' in df_base_filtered.columns:
            df_base_filtered = df_base_filtered[df_base_filtered['Fantasia'].str.contains(filtros['Cliente'], na=False, case=False)]
        
        if 'Data Início' in filtros and filtros['Data Início'] and 'Dt.pagto' in df_base_filtered.columns:
            df_base_filtered = df_base_filtered[pd.to_datetime(df_base_filtered['Dt.pagto']) >= pd.to_datetime(filtros['Data Início'])]
        
        if 'Data Fim' in filtros and filtros['Data Fim'] and 'Dt.pagto' in df_base_filtered.columns:
            df_base_filtered = df_base_filtered[pd.to_datetime(df_base_filtered['Dt.pagto']) <= pd.to_datetime(filtros['Data Fim'])]
    
    # Se não há dados, retornar painel vazio
    if df_base_filtered is None or df_base_filtered.empty:
        return df_painel_filled
    
    # Agrupar por descrição e mês
    # Criar coluna de mês a partir da data de pagamento
    if 'Dt.pagto' in df_base_filtered.columns:
        df_base_filtered['Mês'] = pd.to_datetime(df_base_filtered['Dt.pagto']).dt.to_period('M')
        
        # Agrupar por descrição e mês, somando os valores
        grouped = df_base_filtered.groupby(['Descrição', 'Mês'])['Vl.rateado'].sum().reset_index()
        
        # Preencher o painel
        for _, row in grouped.iterrows():
            descricao = row['Descrição']
            mes = row['Mês']
            valor = row['Vl.rateado']
            
            # Converter período para string no formato YYYY-MM
            mes_str = str(mes)
            
            # Verificar se a descrição existe no painel
            if descricao in df_painel_filled.index and mes_str in df_painel_filled.columns:
                df_painel_filled.loc[descricao, mes_str] += valor
    
    return df_painel_filled

def calcular_saldos(df_painel_filled):
    """
    Calcula os saldos inicial e final com base nos dados.
    """
    # Identificar colunas de mês (assumindo que são todas as colunas exceto a primeira que é o índice)
    meses_cols = df_painel_filled.columns.tolist()
    
    # SALDO INICIAL - primeiro mês
    if 'SALDO INICIAL' in df_painel_filled.index and len(meses_cols) > 0:
        primeiro_mes = meses_cols[0]
        # Se o saldo inicial estiver vazio, definir como 0
        if pd.isna(df_painel_filled.loc['SALDO INICIAL', primeiro_mes]) or df_painel_filled.loc['SALDO INICIAL', primeiro_mes] == 0:
            df_painel_filled.loc['SALDO INICIAL', primeiro_mes] = 6355160.80  # Valor do arquivo original
    
    # Calcular saldos subsequentes
    for i in range(len(meses_cols)):
        mes_atual = meses_cols[i]
        
        # Calcular saldo inicial para meses seguintes
        if i > 0:
            mes_anterior = meses_cols[i-1]
            if 'SALDO FINAL' in df_painel_filled.index:
                saldo_anterior = df_painel_filled.loc['SALDO FINAL', mes_anterior]
                if 'SALDO INICIAL' in df_painel_filled.index:
                    df_painel_filled.loc['SALDO INICIAL', mes_atual] = saldo_anterior
        
        # Calcular receitas totais
        receitas_indices = ['FATURAMENTO', 'FATURAMENTO - devedores', 'INSS RETIDO EM NOTA', 'DEPOSITO A IDENTIFICAR']
        if 'RECEITAS TOTAL' in df_painel_filled.index:
            receitas_total = 0
            for idx in receitas_indices:
                if idx in df_painel_filled.index:
                    receitas_total += df_painel_filled.loc[idx, mes_atual]
            df_painel_filled.loc['RECEITAS TOTAL', mes_atual] = receitas_total
        
        # Calcular saldo final
        if 'SALDO FINAL' in df_painel_filled.index:
            saldo_inicial = df_painel_filled.loc['SALDO INICIAL', mes_atual] if 'SALDO INICIAL' in df_painel_filled.index else 0
            receitas = df_painel_filled.loc['RECEITAS TOTAL', mes_atual] if 'RECEITAS TOTAL' in df_painel_filled.index else 0
            
            # Somar todas as saídas (valores negativos)
            saidas = 0
            for idx in df_painel_filled.index:
                if idx not in ['SALDO INICIAL', 'RECEITAS TOTAL', 'SALDO FINAL', 'CAIXA EFETIVO', 'CAIXA EFETIVO ACUMULADO']:
                    valor = df_painel_filled.loc[idx, mes_atual]
                    if pd.notna(valor) and valor < 0:
                        saidas += valor
            
            df_painel_filled.loc['SALDO FINAL', mes_atual] = saldo_inicial + receitas + saidas
        
        # Calcular caixa efetivo (variação)
        if 'CAIXA EFETIVO' in df_painel_filled.index:
            saldo_inicial = df_painel_filled.loc['SALDO INICIAL', mes_atual] if 'SALDO INICIAL' in df_painel_filled.index else 0
            saldo_final = df_painel_filled.loc['SALDO FINAL', mes_atual] if 'SALDO FINAL' in df_painel_filled.index else 0
            df_painel_filled.loc['CAIXA EFETIVO', mes_atual] = saldo_final - saldo_inicial
    
    # Calcular caixa efetivo acumulado
    if 'CAIXA EFETIVO ACUMULADO' in df_painel_filled.index:
        acumulado = 0
        for mes in meses_cols:
            if 'CAIXA EFETIVO' in df_painel_filled.index:
                acumulado += df_painel_filled.loc['CAIXA EFETIVO', mes]
            df_painel_filled.loc['CAIXA EFETIVO ACUMULADO', mes] = acumulado
    
    return df_painel_filled

# ============================================================================
# FUNÇÕES DE VISUALIZAÇÃO
# ============================================================================
def exibir_painel(df_painel):
    """Exibe o painel completo formatado"""
    
    # Formatar números
    df_display = df_painel.copy()
    for col in df_display.columns:
        df_display[col] = df_display[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "R$ 0,00")
    
    st.dataframe(df_display, use_container_width=True, height=800)

def exibir_graficos(df_painel):
    """Exibe gráficos de análise"""
    
    # Preparar dados
    meses = df_painel.columns.tolist()
    
    # Gráfico de Saldo Inicial vs Final
    if 'SALDO INICIAL' in df_painel.index and 'SALDO FINAL' in df_painel.index:
        saldo_inicial = [df_painel.loc['SALDO INICIAL', mes] for mes in meses]
        saldo_final = [df_painel.loc['SALDO FINAL', mes] for mes in meses]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=meses, y=saldo_inicial, mode='lines+markers', name='Saldo Inicial'))
        fig.add_trace(go.Scatter(x=meses, y=saldo_final, mode='lines+markers', name='Saldo Final'))
        
        fig.update_layout(
            title='Evolução do Saldo',
            xaxis_title='Mês',
            yaxis_title='Valor (R$)',
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de Receitas vs Despesas
    if 'RECEITAS TOTAL' in df_painel.index:
        receitas = [df_painel.loc['RECEITAS TOTAL', mes] for mes in meses]
        
        # Calcular despesas totais (soma de todos os negativos que não são receitas)
        despesas = []
        for mes in meses:
            total_despesas = 0
            for idx in df_painel.index:
                if idx not in ['SALDO INICIAL', 'RECEITAS TOTAL', 'SALDO FINAL', 'CAIXA EFETIVO', 'CAIXA EFETIVO ACUMULADO']:
                    valor = df_painel.loc[idx, mes]
                    if pd.notna(valor) and valor < 0:
                        total_despesas += valor
            despesas.append(abs(total_despesas))
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=meses, y=receitas, name='Receitas', marker_color='#10b981'))
        fig.add_trace(go.Bar(x=meses, y=despesas, name='Despesas', marker_color='#ef4444'))
        
        fig.update_layout(
            title='Receitas vs Despesas',
            xaxis_title='Mês',
            yaxis_title='Valor (R$)',
            barmode='group',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

def exibir_metricas_principais(df_painel):
    """Exibe métricas principais em cards"""
    
    meses = df_painel.columns.tolist()
    ultimo_mes = meses[-2] if len(meses) > 1 else meses[0]  # Último mês do ano
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        saldo_atual = df_painel.loc['SALDO FINAL', ultimo_mes] if 'SALDO FINAL' in df_painel.index else 0
        st.metric(
            label=f"Saldo Final ({ultimo_mes})",
            value=f"R$ {saldo_atual:,.2f}",
            delta=None
        )
    
    with col2:
        receita_total = df_painel.loc['RECEITAS TOTAL', ultimo_mes] if 'RECEITAS TOTAL' in df_painel.index else 0
        st.metric(
            label=f"Receitas ({ultimo_mes})",
            value=f"R$ {receita_total:,.2f}",
            delta=None
        )
    
    with col3:
        # Calcular despesas totais
        despesas_total = 0
        for idx in df_painel.index:
            if idx not in ['SALDO INICIAL', 'RECEITAS TOTAL', 'SALDO FINAL', 'CAIXA EFETIVO', 'CAIXA EFETIVO ACUMULADO']:
                valor = df_painel.loc[idx, ultimo_mes]
                if pd.notna(valor) and valor < 0:
                    despesas_total += valor
        st.metric(
            label=f"Despesas ({ultimo_mes})",
            value=f"R$ {abs(despesas_total):,.2f}",
            delta=None
        )
    
    with col4:
        caixa_efetivo = df_painel.loc['CAIXA EFETIVO', ultimo_mes] if 'CAIXA EFETIVO' in df_painel.index else 0
        cor = "positive" if caixa_efetivo >= 0 else "negative"
        st.markdown(f"""
        <div class="metric-card">
            <h3>Caixa Efetivo ({ultimo_mes})</h3>
            <p class="{cor}">R$ {caixa_efetivo:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# APLICAÇÃO PRINCIPAL
# ============================================================================
def main():
    st.markdown('<p class="main-header">💰 Fluxo de Caixa Real - Dashboard</p>', unsafe_allow_html=True)
    
    # Sidebar - Filtros e upload
    with st.sidebar:
        st.header("📁 Upload da Base")
        uploaded_file = st.file_uploader(
            "Carregar arquivo Excel (aba 'Base')",
            type=['xlsx'],
            help="Formato esperado: arquivo com aba 'Base' contendo as transações"
        )
        
        st.divider()
        
        st.header("🔍 Filtros")
        
        # Obter opções para filtros se houver dados
        empresas = []
        clientes = []
        if uploaded_file and 'df_base' in st.session_state and st.session_state.df_base is not None:
            df_base = st.session_state.df_base
            if 'Fantasia' in df_base.columns:
                empresas = df_base['Fantasia'].dropna().unique().tolist()
                clientes = df_base['Fantasia'].dropna().unique().tolist()
        
        filtro_empresa = st.selectbox(
            "Empresa",
            options=["Todas"] + empresas,
            index=0
        )
        
        filtro_cliente = st.selectbox(
            "Cliente",
            options=["Todos"] + clientes,
            index=0
        )
        
        st.subheader("Período")
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=datetime(2025, 1, 1)
            )
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=datetime(2025, 12, 31)
            )
        
        st.divider()
        
        st.header("⚙️ Ações")
        if st.button("🔄 Atualizar Dashboard", use_container_width=True, type="primary"):
            st.session_state.atualizar = True
        
        if st.button("📊 Exportar Painel", use_container_width=True):
            if 'df_painel_filled' in st.session_state:
                # Converter para Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    st.session_state.df_painel_filled.to_excel(writer, sheet_name='Painel')
                st.download_button(
                    label="📥 Download Excel",
                    data=output.getvalue(),
                    file_name="fluxo_caixa_painel.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    # Área principal
    tab1, tab2, tab3 = st.tabs(["📋 Painel Completo", "📈 Análise Gráfica", "📊 Base de Dados"])
    
    # Inicializar session state
    if 'df_painel' not in st.session_state:
        st.session_state.df_painel, st.session_state.datas = criar_modelo_painel()
    
    if 'df_painel_filled' not in st.session_state:
        st.session_state.df_painel_filled = st.session_state.df_painel.copy()
    
    # Processar novo arquivo se carregado
    if uploaded_file is not None:
        df_base = carregar_dados_base(uploaded_file)
        if df_base is not None:
            st.session_state.df_base = df_base
            st.sidebar.success(f"✅ Base carregada: {len(df_base)} registros")
    
    # Aplicar filtros e atualizar
    if 'df_base' in st.session_state and st.session_state.get('atualizar', False):
        with st.spinner("Processando dados..."):
            # Criar filtros
            filtros = {}
            if filtro_empresa != "Todas":
                filtros['Empresa'] = filtro_empresa
            if filtro_cliente != "Todos":
                filtros['Cliente'] = filtro_cliente
            filtros['Data Início'] = data_inicio
            filtros['Data Fim'] = data_fim
            
            # Processar
            df_painel_filled = processar_base_para_painel(
                st.session_state.df_base,
                st.session_state.df_painel.copy(),
                st.session_state.datas,
                filtros
            )
            df_painel_filled = calcular_saldos(df_painel_filled)
            st.session_state.df_painel_filled = df_painel_filled
            st.session_state.atualizar = False
            st.rerun()
    
    # Tab 1: Painel Completo
    with tab1:
        if 'df_painel_filled' in st.session_state:
            # Métricas principais
            exibir_metricas_principais(st.session_state.df_painel_filled)
            
            st.divider()
            
            # Painel completo
            st.subheader("📋 Painel de Fluxo de Caixa")
            exibir_painel(st.session_state.df_painel_filled)
    
    # Tab 2: Análise Gráfica
    with tab2:
        if 'df_painel_filled' in st.session_state:
            exibir_graficos(st.session_state.df_painel_filled)
            
            # Tabela resumo
            st.divider()
            st.subheader("📊 Resumo Mensal")
            
            resumo_indices = ['SALDO INICIAL', 'RECEITAS TOTAL', 'SALDO FINAL', 'CAIXA EFETIVO']
            resumo_df = pd.DataFrame()
            for idx in resumo_indices:
                if idx in st.session_state.df_painel_filled.index:
                    resumo_df[idx] = st.session_state.df_painel_filled.loc[idx]
            
            # Formatar
            for col in resumo_df.columns:
                resumo_df[col] = resumo_df[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "R$ 0,00")
            
            st.dataframe(resumo_df, use_container_width=True)
    
    # Tab 3: Base de Dados
    with tab3:
        st.subheader("📊 Base de Dados Carregada")
        
        if 'df_base' in st.session_state:
            df_base = st.session_state.df_base
            
            # Estatísticas rápidas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Registros", len(df_base))
            with col2:
                if 'Vl.rateado' in df_base.columns:
                    total_valor = df_base['Vl.rateado'].sum()
                    st.metric("Valor Total", f"R$ {total_valor:,.2f}")
            with col3:
                if 'Dt.pagto' in df_base.columns:
                    datas = pd.to_datetime(df_base['Dt.pagto']).dt.date
                    periodo = f"{datas.min()} a {datas.max()}"
                    st.metric("Período", periodo)
            
            st.dataframe(df_base, use_container_width=True, height=600)
        else:
            st.info("ℹ️ Nenhuma base carregada. Use o menu lateral para fazer upload.")

if __name__ == "__main__":
    main()
