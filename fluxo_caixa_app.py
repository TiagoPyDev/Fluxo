import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Fluxo de Caixa - Pro Clean",
    page_icon="💰",
    layout="wide"
)

# Título principal
st.title("💰 Sistema de Fluxo de Caixa - Pro Clean")
st.markdown("---")

# Funções de carregamento e processamento
@st.cache_data
def load_faturamento(file):
    """Carrega e processa o arquivo de faturamento histórico"""
    df = pd.read_excel(file, sheet_name='Faturamento')
    
    # Converter datas
    df['DTEMISSAO'] = pd.to_datetime(df['DTEMISSAO'])
    df['DTVENCIMENTO'] = pd.to_datetime(df['DTVENCIMENTO'])
    
    # Extrair mês/ano para agrupamentos
    df['MES_ANO'] = df['DTVENCIMENTO'].dt.strftime('%Y-%m')
    df['MES'] = df['DTVENCIMENTO'].dt.month
    df['ANO'] = df['DTVENCIMENTO'].dt.year
    df['DIA'] = df['DTVENCIMENTO'].dt.day
    
    return df

@st.cache_data
def load_layout(file):
    """Carrega o arquivo de layout com as contas"""
    df = pd.read_excel(file, sheet_name='Painel 1')
    # Remover linhas totalmente vazias
    df = df.dropna(how='all')
    return df

def processar_fluxo_real(df_faturamento, df_layout):
    """Processa o fluxo real baseado no layout Painel 1"""
    # Por enquanto, como não temos os valores reais no layout,
    # vamos usar uma estrutura vazia baseada nas contas
    fluxo_real = df_layout.copy()
    
    # Preencher com zeros para os meses
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
             'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    
    for mes in meses:
        if mes not in fluxo_real.columns:
            fluxo_real[mes] = 0.0
    
    # Aqui você pode implementar a lógica para distribuir os valores
    # do faturamento nas respectivas contas do layout
    
    return fluxo_real

def calcular_fluxo_previsto(df_faturamento):
    """Calcula o fluxo previsto baseado no histórico"""
    # Agrupar recebimentos por data de vencimento
    fluxo_diario = df_faturamento.groupby('DTVENCIMENTO').agg({
        'VALORLIQUIDO': 'sum'
    }).reset_index()
    
    fluxo_diario.columns = ['Data', 'Valor_Previsto']
    fluxo_diario = fluxo_diario.sort_values('Data')
    
    # Calcular médias para projeção
    media_mensal = df_faturamento.groupby('MES')['VALORLIQUIDO'].mean()
    
    return fluxo_diario, media_mensal

def criar_estrutura_fluxo_diario():
    """Cria a estrutura base para fluxo diário (similar ao Painel 2)"""
    # Gerar datas de Jan a Mar 2026 (dias úteis)
    datas = []
    data_inicio = datetime(2026, 1, 1)
    data_fim = datetime(2026, 3, 31)
    
    data_atual = data_inicio
    while data_atual <= data_fim:
        # Pular fins de semana (opcional)
        if data_atual.weekday() < 5:  # Segunda a sexta
            datas.append(data_atual)
        data_atual += timedelta(days=1)
    
    df_fluxo = pd.DataFrame({
        'Data': datas,
        'Entrada': 0.0,
        'Saida': 0.0,
        'Saldo': 0.0
    })
    
    return df_fluxo

# Sidebar - Upload de arquivos
with st.sidebar:
    st.header("📁 Upload de Arquivos")
    
    faturamento_file = st.file_uploader(
        "Faturamento Histórico (Faturamento Histórico.xlsx)",
        type=['xlsx']
    )
    
    layout_file = st.file_uploader(
        "Layout (layout.xlsx)",
        type=['xlsx']
    )
    
    st.markdown("---")
    st.header("🔍 Filtros")
    
    if faturamento_file is not None:
        df_faturamento = load_faturamento(faturamento_file)
        
        # Filtros
        empresas = ['Todas'] + sorted(df_faturamento['EMPRESA'].unique().tolist())
        empresa_selecionada = st.selectbox("Empresa", empresas)
        
        if empresa_selecionada != 'Todas':
            df_filtrado = df_faturamento[df_faturamento['EMPRESA'] == empresa_selecionada]
        else:
            df_filtrado = df_faturamento
        
        clientes = ['Todos'] + sorted(df_filtrado['CLIENTE'].unique().tolist())
        cliente_selecionado = st.selectbox("Cliente", clientes)
        
        # Filtro de data
        st.markdown("**Período**")
        data_min = df_faturamento['DTVENCIMENTO'].min().date()
        data_max = df_faturamento['DTVENCIMENTO'].max().date()
        
        data_inicio = st.date_input("Data Inicial", data_min)
        data_fim = st.date_input("Data Final", data_max)

# Abas principais
tab1, tab2, tab3 = st.tabs(["📊 Fluxo Real", "📈 Fluxo Previsto", "📋 Resumo Geral"])

with tab1:
    st.header("Fluxo de Caixa Real")
    
    if layout_file is not None:
        df_layout = load_layout(layout_file)
        fluxo_real = processar_fluxo_real(df_faturamento if faturamento_file else pd.DataFrame(), df_layout)
        
        # Exibir tabela de fluxo real
        st.subheader("Contas por Mês")
        st.dataframe(fluxo_real, use_container_width=True)
        
        # Botão para download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            fluxo_real.to_excel(writer, sheet_name='Fluxo_Real', index=False)
        
        st.download_button(
            label="📥 Download Fluxo Real (Excel)",
            data=output.getvalue(),
            file_name="fluxo_real.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("👈 Faça upload do arquivo 'layout.xlsx' para visualizar o Fluxo Real")

with tab2:
    st.header("Fluxo de Caixa Previsto")
    
    if faturamento_file is not None:
        # Processar dados para previsão
        fluxo_diario, media_mensal = calcular_fluxo_previsto(df_faturamento)
        
        # Aplicar filtros
        if empresa_selecionada != 'Todas':
            df_filtrado = df_faturamento[df_faturamento['EMPRESA'] == empresa_selecionada]
        else:
            df_filtrado = df_faturamento
            
        if cliente_selecionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['CLIENTE'] == cliente_selecionado]
        
        df_filtrado = df_filtrado[
            (df_filtrado['DTVENCIMENTO'].dt.date >= data_inicio) &
            (df_filtrado['DTVENCIMENTO'].dt.date <= data_fim)
        ]
        
        # Métricas resumidas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Recebimentos",
                f"R$ {df_filtrado['VALORLIQUIDO'].sum():,.2f}"
            )
        
        with col2:
            st.metric(
                "Média por Dia",
                f"R$ {df_filtrado['VALORLIQUIDO'].mean():,.2f}"
            )
        
        with col3:
            st.metric(
                "Total Notas",
                f"{len(df_filtrado)}"
            )
        
        with col4:
            st.metric(
                "Clientes Ativos",
                f"{df_filtrado['CLIENTE'].nunique()}"
            )
        
        st.markdown("---")
        
        # Gráfico de linha - Evolução por data
        st.subheader("📅 Evolução Diária dos Recebimentos")
        
        df_diario = df_filtrado.groupby('DTVENCIMENTO')['VALORLIQUIDO'].sum().reset_index()
        df_diario.columns = ['Data', 'Valor']
        
        fig_line = px.line(
            df_diario,
            x='Data',
            y='Valor',
            title='Recebimentos por Data de Vencimento',
            markers=True
        )
        fig_line.update_layout(
            xaxis_title="Data",
            yaxis_title="Valor (R$)",
            hovermode='x'
        )
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Gráfico de barras - Por mês
        st.subheader("📊 Recebimentos por Mês")
        
        df_mensal = df_filtrado.groupby('MES_ANO')['VALORLIQUIDO'].sum().reset_index()
        
        fig_bar = px.bar(
            df_mensal,
            x='MES_ANO',
            y='VALORLIQUIDO',
            title='Total Recebido por Mês',
            text_auto='.2s'
        )
        fig_bar.update_layout(
            xaxis_title="Mês/Ano",
            yaxis_title="Valor (R$)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Tabela de projeção diária
        st.subheader("📋 Projeção Diária de Recebimentos")
        
        # Criar estrutura de fluxo diário
        df_projecao = criar_estrutura_fluxo_diario()
        
        # Preencher com valores históricos (exemplo)
        # Na prática, você usaria modelos de previsão
        ultima_data = df_filtrado['DTVENCIMENTO'].max()
        valor_medio_dia = df_filtrado['VALORLIQUIDO'].mean()
        
        # Exemplo: projetar próximos 3 meses baseado na média
        for idx, row in df_projecao.iterrows():
            if row['Data'] > ultima_data:
                df_projecao.loc[idx, 'Entrada'] = valor_medio_dia * np.random.uniform(0.8, 1.2)
        
        # Calcular saldo acumulado
        df_projecao['Saldo'] = df_projecao['Entrada'].cumsum() - df_projecao['Saida'].cumsum()
        
        st.dataframe(
            df_projecao.style.format({
                'Entrada': 'R$ {:,.2f}',
                'Saida': 'R$ {:,.2f}',
                'Saldo': 'R$ {:,.2f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # Botão para download da projeção
        output_proj = BytesIO()
        with pd.ExcelWriter(output_proj, engine='openpyxl') as writer:
            df_projecao.to_excel(writer, sheet_name='Projecao', index=False)
        
        st.download_button(
            label="📥 Download Projeção Diária (Excel)",
            data=output_proj.getvalue(),
            file_name="projecao_fluxo_caixa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    else:
        st.info("👈 Faça upload do arquivo 'Faturamento Histórico.xlsx' para visualizar o Fluxo Previsto")

with tab3:
    st.header("Resumo Geral")
    
    if faturamento_file is not None:
        # KPIs principais
        st.subheader("📈 Indicadores Principais")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_geral = df_faturamento['VALORLIQUIDO'].sum()
            st.metric("Faturamento Total (Histórico)", f"R$ {total_geral:,.2f}")
        
        with col2:
            media_geral = df_faturamento['VALORLIQUIDO'].mean()
            st.metric("Ticket Médio", f"R$ {media_geral:,.2f}")
        
        with col3:
            num_clientes = df_faturamento['CLIENTE'].nunique()
            st.metric("Total de Clientes", num_clientes)
        
        st.markdown("---")
        
        # Top 10 clientes
        st.subheader("🏆 Top 10 Clientes por Faturamento")
        
        top_clientes = df_faturamento.groupby('CLIENTE')['VALORLIQUIDO'].sum().nlargest(10).reset_index()
        
        fig_top = px.bar(
            top_clientes,
            x='VALORLIQUIDO',
            y='CLIENTE',
            orientation='h',
            title='Top 10 Clientes - Faturamento Total',
            text_auto='.2s'
        )
        fig_top.update_layout(
            xaxis_title="Valor (R$)",
            yaxis_title="Cliente"
        )
        st.plotly_chart(fig_top, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Detalhamento por Cliente")
        
        resumo_clientes = df_faturamento.groupby(['CLIENTE', 'COD']).agg({
            'VALORLIQUIDO': ['sum', 'mean', 'count'],
            'DTVENCIMENTO': ['min', 'max']
        }).round(2)
        
        resumo_clientes.columns = ['Total', 'Média', 'Qtd Notas', 'Primeira Data', 'Última Data']
        resumo_clientes = resumo_clientes.reset_index()
        
        st.dataframe(
            resumo_clientes.style.format({
                'Total': 'R$ {:,.2f}',
                'Média': 'R$ {:,.2f}'
            }),
            use_container_width=True
        )
        
        # Botão para download do resumo
        output_resumo = BytesIO()
        with pd.ExcelWriter(output_resumo, engine='openpyxl') as writer:
            resumo_clientes.to_excel(writer, sheet_name='Resumo_Clientes', index=False)
            df_faturamento.to_excel(writer, sheet_name='Dados_Completos', index=False)
        
        st.download_button(
            label="📥 Download Resumo Completo (Excel)",
            data=output_resumo.getvalue(),
            file_name="resumo_faturamento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("👈 Faça upload do arquivo de faturamento para visualizar o resumo")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido para gestão de fluxo de caixa da Pro Clean | Atualizado em: 06/03/2026")
