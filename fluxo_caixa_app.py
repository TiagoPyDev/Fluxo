# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import io
import numpy as np
import holidays

# ============================================
# CONFIGURAÇÕES DIRETAMENTE NO CÓDIGO
# ============================================

# Cores do tema
CORES = {
    'entradas': '#2E8B57',      # Verde
    'saidas': '#DC143C',         # Vermelho
    'saldo': '#1E3A8A',          # Azul escuro
    'saldo_zero': '#9CA3AF',     # Cinza
    'primaria': '#1E3A8A',       # Cor primária (botões, links)
    'fundo': '#FFFFFF',           # Fundo branco
    'fundo_secundario': '#F3F4F6', # Fundo secundário
    'texto': '#1F2937'            # Cor do texto
}

# Configurações de feriados e dias úteis
FERIADOS_BR = holidays.Brazil()
DIAS_UTEIS = list(range(5))  # 0-4 = segunda a sexta
DIAS_PARA_CREDITO = 2  # Dias após pagamento para dinheiro cair na conta

# Configurações da página
st.set_page_config(
    page_title="Fluxo de Caixa Projetado",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar tema customizado via CSS
st.markdown(f"""
<style>
    /* Cores personalizadas */
    .stApp {{
        background-color: {CORES['fundo']};
    }}
    .stButton>button {{
        background-color: {CORES['primaria']};
        color: white;
    }}
    .stButton>button:hover {{
        background-color: {CORES['primaria']}dd;
    }}
    .metric-card {{
        background-color: {CORES['fundo_secundario']};
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid {CORES['primaria']};
        margin-bottom: 1rem;
    }}
    .metric-card h4 {{
        margin: 0;
        font-size: 0.9rem;
        color: #666;
    }}
    .metric-card h2 {{
        margin: 0;
        font-size: 1.8rem;
        font-weight: bold;
    }}
    footer {{
        text-align: center;
        color: gray;
        padding: 10px;
        font-size: 0.8rem;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================
# CLASSES DE PROCESSAMENTO
# ============================================

class DataProcessor:
    def __init__(self):
        self.df_historico = None
        self.df_pagamentos = None
        
    def load_historico(self, file_path):
        """Carrega e processa o arquivo histórico de faturas"""
        try:
            # Carregar dados
            df = pd.read_excel(file_path, sheet_name='Faturamento')
            
            # Verificar se o dataframe está vazio
            if df.empty:
                st.error("O arquivo carregado está vazio!")
                return None
            
            # Processar datas
            df['DTEMISSAO'] = pd.to_datetime(df['DTEMISSAO'], errors='coerce')
            df['DTVENCIMENTO'] = pd.to_datetime(df['DTVENCIMENTO'], errors='coerce')
            
            # Remover linhas com datas inválidas
            df = df.dropna(subset=['DTVENCIMENTO'])
            
            if df.empty:
                st.error("Nenhuma data de vencimento válida encontrada!")
                return None
            
            # Extrair apenas a data (sem hora)
            df['DATA_EMISSAO'] = df['DTEMISSAO'].dt.date
            df['DATA_VENCIMENTO'] = df['DTVENCIMENTO'].dt.date
            
            # Calcular data de crédito (2 dias após pagamento)
            df['DATA_CREDITO'] = df['DATA_VENCIMENTO'].apply(self._proximo_dia_util)
            
            # Remover linhas com data de crédito inválida
            df = df.dropna(subset=['DATA_CREDITO'])
            
            # Extrair mês/ano para agrupamento
            df['MES_ANO'] = pd.to_datetime(df['DATA_CREDITO']).dt.to_period('M')
            
            # Garantir que valores são numéricos
            df['VALORBRUTO'] = pd.to_numeric(df['VALORBRUTO'], errors='coerce').fillna(0)
            df['VALORLIQUIDO'] = pd.to_numeric(df['VALORLIQUIDO'], errors='coerce').fillna(0)
            
            self.df_historico = df
            return df
            
        except Exception as e:
            st.error(f"Erro ao carregar arquivo: {str(e)}")
            return None
    
    def _proximo_dia_util(self, data):
        """Retorna o próximo dia útil após a data (considerando feriados)"""
        if pd.isna(data):
            return None
        
        try:
            data_atual = pd.to_datetime(data)
            dias_adicionados = 0
            
            while dias_adicionados < DIAS_PARA_CREDITO:
                data_atual += timedelta(days=1)
                if data_atual.weekday() < 5 and data_atual not in FERIADOS_BR:
                    dias_adicionados += 1
            
            return data_atual.date()
        except:
            return None
    
    def calcular_fluxo_projetado(self, df, meses_projecao=12):
        """Calcula fluxo de caixa projetado"""
        if df is None or df.empty:
            return pd.DataFrame()
        
        try:
            # Agrupar entradas por cliente para projetar padrões
            entradas_por_cliente = df.groupby('CLIENTE').agg({
                'VALORLIQUIDO': ['mean', 'std', 'count'],
                'DATA_CREDITO': lambda x: list(x) if len(x) > 0 else []
            }).round(2)
            
            entradas_por_cliente.columns = ['media', 'desvio', 'frequencia', 'datas_historicas']
            
            return entradas_por_cliente
        except:
            return pd.DataFrame()
    
    def filtrar_dados(self, df, data_inicio=None, data_fim=None, clientes=None, empresa=None):
        """Aplica filtros ao dataframe"""
        if df is None or df.empty:
            return df
        
        try:
            df_filtrado = df.copy()
            
            if data_inicio:
                data_inicio_dt = pd.to_datetime(data_inicio).date()
                df_filtrado = df_filtrado[df_filtrado['DATA_CREDITO'] >= data_inicio_dt]
            
            if data_fim:
                data_fim_dt = pd.to_datetime(data_fim).date()
                df_filtrado = df_filtrado[df_filtrado['DATA_CREDITO'] <= data_fim_dt]
            
            if clientes and len(clientes) > 0:
                df_filtrado = df_filtrado[df_filtrado['CLIENTE'].isin(clientes)]
            
            if empresa and empresa != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['EMPRESA'] == empresa]
            
            return df_filtrado
        except:
            return pd.DataFrame()
    
    def calcular_saldo_diario(self, df_entradas, df_saidas=None):
        """Calcula saldo diário baseado em entradas e saídas"""
        if df_entradas is None or df_entradas.empty:
            return pd.DataFrame()
        
        try:
            # Agrupar entradas por data
            entradas_diarias = df_entradas.groupby('DATA_CREDITO')['VALORLIQUIDO'].sum().reset_index()
            entradas_diarias.columns = ['data', 'entradas']
            
            # Se houver saídas, processar
            if df_saidas is not None and not df_saidas.empty:
                saidas_diarias = df_saidas.groupby('DATA_CREDITO')['VALORLIQUIDO'].sum().reset_index()
                saidas_diarias.columns = ['data', 'saidas']
                
                # Combinar entradas e saídas
                saldo = pd.merge(entradas_diarias, saidas_diarias, on='data', how='outer').fillna(0)
            else:
                saldo = entradas_diarias.copy()
                saldo['saidas'] = 0
            
            # Calcular saldo líquido
            saldo['saldo_liquido'] = saldo['entradas'] - saldo['saidas']
            
            # Calcular saldo acumulado
            saldo = saldo.sort_values('data')
            saldo['saldo_acumulado'] = saldo['saldo_liquido'].cumsum()
            
            return saldo
        except:
            return pd.DataFrame()

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def formatar_valor(valor):
    """Formata valor para exibição em R$"""
    try:
        if pd.isna(valor) or valor is None:
            return "R$ 0,00"
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def safe_min_max(series):
    """Retorna min e max com segurança para séries vazias"""
    try:
        if series is None or len(series) == 0:
            return None, None
        series_clean = series.dropna()
        if len(series_clean) == 0:
            return None, None
        return series_clean.min(), series_clean.max()
    except:
        return None, None

# ============================================
# APLICAÇÃO PRINCIPAL
# ============================================

# Inicializar processador de dados
@st.cache_resource
def get_processor():
    return DataProcessor()

processor = get_processor()

# Título principal
st.title("💰 Fluxo de Caixa Projetado")
st.markdown("---")

# Sidebar - Upload de arquivos
with st.sidebar:
    st.header("📁 Upload de Dados")
    
    # Upload do histórico
    historico_file = st.file_uploader(
        "Carregar base histórica (Faturamento Histórico.xlsx)",
        type=['xlsx', 'xls'],
        key='historico'
    )
    
    if historico_file:
        with st.spinner("Carregando dados..."):
            df = processor.load_historico(historico_file)
        
        if df is not None and not df.empty:
            st.success(f"✅ Histórico carregado: {len(df)} registros")
        else:
            st.error("❌ Erro ao carregar arquivo. Verifique o formato.")
            st.stop()
    
    st.markdown("---")
    
    # Filtros (só aparecem se os dados foram carregados)
    if historico_file and df is not None and not df.empty:
        st.header("🔍 Filtros")
        
        # Filtro de período
        st.subheader("Período")
        
        data_min, data_max = safe_min_max(df['DATA_CREDITO'])
        
        if data_min is None or data_max is None:
            st.warning("Não há datas válidas para filtrar")
            data_inicio = date.today()
            data_fim = date.today()
        else:
            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input(
                    "Data inicial",
                    value=data_min,
                    min_value=data_min,
                    max_value=data_max
                )
            with col2:
                data_fim = st.date_input(
                    "Data final",
                    value=data_max,
                    min_value=data_min,
                    max_value=data_max
                )
        
        # Filtro de empresa
        empresas = ['Todas'] + sorted(df['EMPRESA'].dropna().unique().tolist())
        empresa_selecionada = st.selectbox(
            "Empresa",
            options=empresas
        )
        
        # Filtro de clientes
        clientes = sorted(df['CLIENTE'].dropna().unique().tolist())
        clientes_selecionados = st.multiselect(
            "Clientes (deixe vazio para todos)",
            options=clientes
        )
        
        # Opções de projeção
        st.markdown("---")
        st.header("📈 Projeção")
        
        meses_projecao = st.slider(
            "Meses para projetar",
            min_value=1,
            max_value=24,
            value=6
        )
    else:
        st.stop()

# Área principal
if historico_file is None or df is None or df.empty:
    st.info("👈 Carregue o arquivo de faturamento histórico para começar")
    st.stop()

# Aplicar filtros
with st.spinner("Aplicando filtros..."):
    df_filtrado = processor.filtrar_dados(
        df,
        data_inicio=data_inicio if 'data_inicio' in locals() else None,
        data_fim=data_fim if 'data_fim' in locals() else None,
        clientes=clientes_selecionados if 'clientes_selecionados' in locals() and clientes_selecionados else None,
        empresa=empresa_selecionada if 'empresa_selecionada' in locals() else None
    )

if df_filtrado.empty:
    st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados")
    st.stop()

# Tabs para organização
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Visão Geral",
    "📅 Fluxo Diário",
    "📈 Projeções",
    "📋 Dados Detalhados"
])

with tab1:
    st.header("Visão Geral do Fluxo de Caixa")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_entradas = df_filtrado['VALORLIQUIDO'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <h4>Total Recebimentos</h4>
            <h2>{formatar_valor(total_entradas)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        num_notas = len(df_filtrado)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Número de Notas</h4>
            <h2>{num_notas:,}</h2>
        </div>
        """.replace(",", "."), unsafe_allow_html=True)
    
    with col3:
        num_clientes = df_filtrado['CLIENTE'].nunique()
        st.markdown(f"""
        <div class="metric-card">
            <h4>Clientes</h4>
            <h2>{num_clientes}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        ticket_medio = total_entradas / num_notas if num_notas > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h4>Ticket Médio</h4>
            <h2>{formatar_valor(ticket_medio)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Gráfico de fluxo por mês
    st.subheader("Fluxo Mensal de Recebimentos")
    
    fluxo_mensal = df_filtrado.groupby('MES_ANO')['VALORLIQUIDO'].sum().reset_index()
    fluxo_mensal['MES_ANO'] = fluxo_mensal['MES_ANO'].astype(str)
    
    fig_mensal = px.bar(
        fluxo_mensal,
        x='MES_ANO',
        y='VALORLIQUIDO',
        title="Recebimentos por Mês",
        labels={'VALORLIQUIDO': 'Valor (R$)', 'MES_ANO': 'Mês/Ano'},
        color_discrete_sequence=[CORES['entradas']]
    )
    fig_mensal.update_layout(showlegend=False)
    st.plotly_chart(fig_mensal, use_container_width=True)
    
    # Top clientes
    st.subheader("Top 10 Clientes por Valor")
    
    top_clientes = df_filtrado.groupby('CLIENTE')['VALORLIQUIDO'].sum().nlargest(10).reset_index()
    
    fig_clientes = px.bar(
        top_clientes,
        x='VALORLIQUIDO',
        y='CLIENTE',
        orientation='h',
        title="Maiores Clientes",
        labels={'VALORLIQUIDO': 'Valor Total (R$)', 'CLIENTE': 'Cliente'},
        color_discrete_sequence=[CORES['entradas']]
    )
    st.plotly_chart(fig_clientes, use_container_width=True)

with tab2:
    st.header("Fluxo de Caixa Diário")
    
    # Calcular saldo diário
    saldo_diario = processor.calcular_saldo_diario(df_filtrado)
    
    if not saldo_diario.empty:
        # Gráfico de saldo diário
        fig_saldo_diario = go.Figure()
        
        fig_saldo_diario.add_trace(go.Bar(
            x=saldo_diario['data'],
            y=saldo_diario['entradas'],
            name='Entradas',
            marker_color=CORES['entradas']
        ))
        
        fig_saldo_diario.add_trace(go.Bar(
            x=saldo_diario['data'],
            y=saldo_diario['saidas'] * -1,  # Saídas negativas para visualização
            name='Saídas',
            marker_color=CORES['saidas']
        ))
        
        fig_saldo_diario.update_layout(
            title="Entradas e Saídas Diárias",
            xaxis_title="Data",
            yaxis_title="Valor (R$)",
            barmode='relative'
        )
        
        st.plotly_chart(fig_saldo_diario, use_container_width=True)
        
        # Gráfico de saldo acumulado
        fig_saldo_acumulado = px.line(
            saldo_diario,
            x='data',
            y='saldo_acumulado',
            title="Saldo Acumulado ao Longo do Tempo",
            labels={'saldo_acumulado': 'Saldo Acumulado (R$)', 'data': 'Data'},
            color_discrete_sequence=[CORES['saldo']]
        )
        
        # Linha do zero
        fig_saldo_acumulado.add_hline(
            y=0,
            line_dash="dash",
            line_color=CORES['saldo_zero'],
            opacity=0.5
        )
        
        st.plotly_chart(fig_saldo_acumulado, use_container_width=True)
        
        # Tabela de saldo diário
        st.subheader("Detalhamento Diário")
        
        saldo_diario_display = saldo_diario.copy()
        saldo_diario_display['entradas'] = saldo_diario_display['entradas'].apply(formatar_valor)
        saldo_diario_display['saidas'] = saldo_diario_display['saidas'].apply(formatar_valor)
        saldo_diario_display['saldo_liquido'] = saldo_diario_display['saldo_liquido'].apply(formatar_valor)
        saldo_diario_display['saldo_acumulado'] = saldo_diario_display['saldo_acumulado'].apply(formatar_valor)
        
        st.dataframe(
            saldo_diario_display,
            use_container_width=True,
            hide_index=True
        )

with tab3:
    st.header("Projeções Futuras")
    
    # Calcular projeções baseadas no histórico
    projecoes = processor.calcular_fluxo_projetado(df_filtrado, meses_projecao)
    
    if not projecoes.empty:
        st.subheader("Média por Cliente")
        
        projecoes_display = projecoes.reset_index()
        projecoes_display.columns = ['Cliente', 'Média (R$)', 'Desvio Padrão', 'Frequência', 'Datas Históricas']
        projecoes_display['Média (R$)'] = projecoes_display['Média (R$)'].apply(formatar_valor)
        projecoes_display['Desvio Padrão'] = projecoes_display['Desvio Padrão'].apply(formatar_valor)
        
        st.dataframe(projecoes_display, use_container_width=True)
        
        # Gráfico de projeção mensal
        st.subheader("Projeção Mensal")
        
        # Criar datas futuras baseadas nos padrões
        try:
            ultima_data = pd.to_datetime(df_filtrado['DATA_CREDITO'].max())
            ultimo_mes = ultima_data.to_period('M')
            meses_futuros = [ultimo_mes + i for i in range(1, meses_projecao + 1)]
            
            # Estimar valores futuros baseados na média histórica
            media_mensal_historica = df_filtrado.groupby('MES_ANO')['VALORLIQUIDO'].sum().mean()
            
            projecao_mensal = pd.DataFrame({
                'Mês': [str(m) for m in meses_futuros],
                'Valor Projetado (R$)': [media_mensal_historica] * meses_projecao
            })
            
            fig_projecao = px.bar(
                projecao_mensal,
                x='Mês',
                y='Valor Projetado (R$)',
                title=f"Projeção para os próximos {meses_projecao} meses",
                color_discrete_sequence=[CORES['entradas']]
            )
            
            st.plotly_chart(fig_projecao, use_container_width=True)
            
            # Aviso sobre a projeção
            st.info(
                "ℹ️ As projeções são baseadas nas médias históricas e podem não refletir "
                "valores reais futuros. Utilize como referência e ajuste conforme necessário."
            )
        except Exception as e:
            st.warning("Não foi possível gerar a projeção mensal.")

with tab4:
    st.header("Dados Detalhados")
    
    # Mostrar dados filtrados
    df_display = df_filtrado.copy()
    
    # Formatar valores
    df_display['VALORBRUTO'] = df_display['VALORBRUTO'].apply(formatar_valor)
    df_display['VALORLIQUIDO'] = df_display['VALORLIQUIDO'].apply(formatar_valor)
    
    # Selecionar colunas para exibição
    colunas_exibir = ['EMPRESA', 'COD', 'CLIENTE', 'DATA_EMISSAO', 'DATA_VENCIMENTO', 
                      'DATA_CREDITO', 'VALORBRUTO', 'VALORLIQUIDO']
    
    st.dataframe(
        df_display[colunas_exibir],
        use_container_width=True,
        hide_index=True
    )
    
    # Botão para download
    csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download dos dados filtrados (CSV)",
        data=csv,
        file_name=f"fluxo_caixa_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# Footer
st.markdown("---")
st.markdown(
    f"""
    <footer>
        Desenvolvido para análise de fluxo de caixa | 
        💰 Entradas em conta 2 dias úteis após vencimento |
        📅 Considera apenas dias úteis
    </footer>
    """,
    unsafe_allow_html=True
)
