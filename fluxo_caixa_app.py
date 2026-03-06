# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import io

from config import CORES
from data_processor import DataProcessor

# Configuração da página
st.set_page_config(
    page_title="Fluxo de Caixa Projetado",
    page_icon="💰",
    layout="wide"
)

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
        df = processor.load_historico(historico_file)
        st.success(f"✅ Histórico carregado: {len(df)} registros")
    
    # Upload de pagamentos (opcional)
    pagamentos_file = st.file_uploader(
        "Carregar pagamentos recebidos (opcional)",
        type=['xlsx', 'xls', 'csv'],
        key='pagamentos'
    )
    
    if pagamentos_file:
        st.info("📥 Arquivo de pagamentos carregado")
    
    st.markdown("---")
    
    # Filtros
    st.header("🔍 Filtros")
    
    if historico_file and df is not None:
        # Filtro de período
        st.subheader("Período")
        
        data_min = df['DATA_CREDITO'].min()
        data_max = df['DATA_CREDITO'].max()
        
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
        empresas = ['Todas'] + sorted(df['EMPRESA'].unique().tolist())
        empresa_selecionada = st.selectbox(
            "Empresa",
            options=empresas
        )
        
        # Filtro de clientes
        clientes = sorted(df['CLIENTE'].unique().tolist())
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

# Área principal
if historico_file is None:
    st.info("👈 Carregue o arquivo de faturamento histórico para começar")
    st.stop()

# Aplicar filtros
df_filtrado = processor.filtrar_dados(
    df,
    data_inicio=data_inicio if 'data_inicio' in locals() else None,
    data_fim=data_fim if 'data_fim' in locals() else None,
    clientes=clientes_selecionados if clientes_selecionados else None,
    empresa=None if empresa_selecionada == 'Todas' else empresa_selecionada
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
        st.metric(
            "Total Recebimentos",
            f"R$ {total_entradas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    
    with col2:
        num_notas = len(df_filtrado)
        st.metric("Número de Notas", f"{num_notas:,}".replace(",", "."))
    
    with col3:
        num_clientes = df_filtrado['CLIENTE'].nunique()
        st.metric("Clientes", num_clientes)
    
    with col4:
        ticket_medio = total_entradas / num_notas if num_notas > 0 else 0
        st.metric(
            "Ticket Médio",
            f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    
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
        saldo_diario_display['entradas'] = saldo_diario_display['entradas'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        saldo_diario_display['saidas'] = saldo_diario_display['saidas'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        saldo_diario_display['saldo_liquido'] = saldo_diario_display['saldo_liquido'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        saldo_diario_display['saldo_acumulado'] = saldo_diario_display['saldo_acumulado'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
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
        projecoes_display['Média (R$)'] = projecoes_display['Média (R$)'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        projecoes_display['Desvio Padrão'] = projecoes_display['Desvio Padrão'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        st.dataframe(projecoes_display, use_container_width=True)
        
        # Gráfico de projeção mensal
        st.subheader("Projeção Mensal")
        
        # Criar datas futuras baseadas nos padrões
        ultimo_mes = pd.to_datetime(df_filtrado['DATA_CREDITO'].max()).to_period('M')
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

with tab4:
    st.header("Dados Detalhados")
    
    # Mostrar dados filtrados
    df_display = df_filtrado.copy()
    
    # Formatar valores
    df_display['VALORBRUTO'] = df_display['VALORBRUTO'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df_display['VALORLIQUIDO'] = df_display['VALORLIQUIDO'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    
    # Selecionar colunas para exibição
    colunas_exibir = ['EMPRESA', 'COD', 'CLIENTE', 'DATA_EMISSAO', 'DATA_VENCIMENTO', 
                      'DATA_CREDITO', 'VALORBRUTO', 'VALORLIQUIDO']
    
    st.dataframe(
        df_display[colunas_exibir],
        use_container_width=True,
        hide_index=True
    )
    
    # Botão para download
    csv = df_filtrado.to_csv(index=False)
    st.download_button(
        label="📥 Download dos dados filtrados (CSV)",
        data=csv,
        file_name=f"fluxo_caixa_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 10px;'>
        Desenvolvido para análise de fluxo de caixa | 
        💰 Entradas em conta 2 dias úteis após vencimento |
        📅 Considera apenas dias úteis
    </div>
    """,
    unsafe_allow_html=True
)
