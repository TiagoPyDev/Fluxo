import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Configuração da página
st.set_page_config(
    page_title="Fluxo de Caixa - PRO CLEAN",
    page_icon="💰",
    layout="wide"
)

# Funções de carregamento e processamento
@st.cache_data
def load_data(uploaded_file):
    """Carrega dados do arquivo Excel uploadado"""
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        
        # Carrega as duas abas
        df_faturamento = pd.read_excel(xls, 'Faturamento')
        df_pagamentos = pd.read_excel(xls, 'Pagamentos')
        
        return df_faturamento, df_pagamentos
    return None, None

def process_faturamento(df):
    """Processa a base de faturamento"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Padronizar nomes das colunas
    df.columns = [col.strip().upper() for col in df.columns]
    
    # Converter datas
    date_columns = ['DTEMISSAO', 'DTVENCIMENTO']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Extrair mês/ano para facilitar análises
    if 'DTVENCIMENTO' in df.columns:
        df['MES_VENCIMENTO'] = df['DTVENCIMENTO'].dt.to_period('M')
        df['ANO_MES'] = df['DTVENCIMENTO'].dt.strftime('%Y-%m')
    
    return df

def process_pagamentos(df):
    """Processa a base de pagamentos"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Padronizar nomes das colunas
    df.columns = [col.strip().upper() for col in df.columns]
    
    # Mapear colunas (o arquivo pode ter nomes diferentes)
    col_map = {
        'DESCRIÇÃO': 'DESCRICAO',
        'DT.VENC.': 'DTVENC',
        'DT.PAGTO': 'DTPAGTO',
        'MÊS': 'MES'
    }
    
    df.rename(columns=col_map, inplace=True)
    
    # Converter datas
    date_columns = ['DTVENC', 'DTPAGTO', 'MES']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Criar categorias baseadas nos códigos de segmento
    df['CATEGORIA'] = df['SEGMENTO'].astype(str).str[:4].map({
        '4110': 'SALARIOS E ENCARGOS',
        '4111': 'BENEFÍCIOS',
        '4112': 'ASPECTOS TRABALHISTAS',
        '4113': 'CUSTOS DE ADMISSÃO',
        '4114': 'MÃO DE OBRA TERCEIROS',
        '4120': 'ENERGIAS',
        '4121': 'MANUTENÇÃO',
        '4122': 'MATERIAL DE LIMPEZA',
        '4123': 'ALUGUÉIS',
        '4124': 'DESPESAS COM VEÍCULOS',
        '4125': 'IMPOSTOS, TAXAS E SEGUROS',
        '4126': 'COMUNICAÇÕES',
        '4127': 'VIAGENS E LOCOMOÇÃO',
        '4128': 'ADMINISTRAÇÃO',
        '4129': 'SERVIÇOS CONTRATADOS',
        '4130': 'COMISSÕES',
        '4131': 'DESPESAS COM MARKETING',
        '4132': 'DESPESAS COM CLIENTES',
        '6130': 'CAIXA'
    })
    
    # Classificar transferências especificamente
    mask_transf = df['DESCRICAO'].str.contains('TRANSFERENCIA|CX - TRANSFERÊNCIA', na=False, case=False)
    df.loc[mask_transf, 'CATEGORIA'] = 'CX - TRANSFERÊNCIA'
    
    return df

def create_real_cash_flow(df_pagamentos, df_faturamento, empresas=None, clientes=None, data_inicio=None, data_fim=None):
    """Cria o fluxo de caixa real agregado por categoria"""
    if df_pagamentos is None or df_pagamentos.empty:
        return pd.DataFrame()
    
    df = df_pagamentos.copy()
    
    # Aplicar filtros
    if empresas and len(empresas) > 0:
        df = df[df['EMPRESA'].isin(empresas)]
    
    # Filtrar por data de pagamento
    if 'DTPAGTO' in df.columns and data_inicio and data_fim:
        df = df[(df['DTPAGTO'] >= pd.Timestamp(data_inicio)) & 
                (df['DTPAGTO'] <= pd.Timestamp(data_fim))]
    
    # Extrair mês/ano
    df['MES_ANO'] = df['DTPAGTO'].dt.to_period('M').astype(str)
    
    # Agrupar por categoria e mês
    pivot = pd.pivot_table(
        df,
        values='VALOR',
        index='CATEGORIA',
        columns='MES_ANO',
        aggfunc='sum',
        fill_value=0
    )
    
    # Calcular totais
    pivot['Total'] = pivot.sum(axis=1)
    pivot = pivot.sort_values('Total', ascending=False)
    
    return pivot

def create_projected_cash_flow(df_faturamento, df_pagamentos, projection_days=30):
    """Cria projeção de fluxo de caixa baseada em recebimentos e pagamentos futuros"""
    if df_faturamento is None or df_pagamentos is None:
        return pd.DataFrame()
    
    hoje = datetime.now().date()
    data_limite = hoje + timedelta(days=projection_days)
    
    # Projeção de recebimentos
    recebimentos = df_faturamento.copy()
    if 'DTVENCIMENTO' in recebimentos.columns:
        recebimentos = recebimentos[recebimentos['DTVENCIMENTO'].dt.date <= data_limite]
        recebimentos = recebimentos[recebimentos['DTVENCIMENTO'].dt.date >= hoje]
        
        # Considerar 2 dias para compensação
        recebimentos['DATA_CAIXA'] = recebimentos['DTVENCIMENTO'] + pd.Timedelta(days=2)
        recebimentos['VALOR'] = recebimentos.get('VALORLIQUIDO', recebimentos.get('VALORBRUTO', 0))
        recebimentos['TIPO'] = 'RECEBIMENTO'
        recebimentos['DESCRICAO'] = recebimentos['CLIENTE'].astype(str) + ' - Recebimento'
    
    # Projeção de pagamentos
    pagamentos = df_pagamentos.copy()
    if 'DTVENC' in pagamentos.columns:
        pagamentos = pagamentos[pagamentos['DTVENC'].dt.date <= data_limite]
        pagamentos = pagamentos[pagamentos['DTVENC'].dt.date >= hoje]
        pagamentos['DATA_CAIXA'] = pagamentos['DTVENC']
        pagamentos['VALOR'] = pagamentos['VALOR']
        pagamentos['TIPO'] = 'PAGAMENTO'
        pagamentos['DESCRICAO'] = pagamentos['DESCRICAO']
    
    # Combinar projeções
    projecoes = pd.concat([
        recebimentos[['DATA_CAIXA', 'VALOR', 'TIPO', 'DESCRICAO']] if not recebimentos.empty else pd.DataFrame(),
        pagamentos[['DATA_CAIXA', 'VALOR', 'TIPO', 'DESCRICAO']] if not pagamentos.empty else pd.DataFrame()
    ], ignore_index=True)
    
    if not projecoes.empty:
        projecoes = projecoes.sort_values('DATA_CAIXA')
        projecoes['SALDO_ACUMULADO'] = projecoes['VALOR'].cumsum()
    
    return projecoes

def create_daily_projection(df_faturamento, df_pagamentos, projection_days=30):
    """Cria projeção diária detalhada"""
    projecoes = create_projected_cash_flow(df_faturamento, df_pagamentos, projection_days)
    
    if projecoes.empty:
        return pd.DataFrame()
    
    # Agrupar por dia
    projecoes['DIA'] = projecoes['DATA_CAIXA'].dt.date
    daily = projecoes.groupby('DIA').agg({
        'VALOR': 'sum',
        'TIPO': lambda x: ', '.join(x.unique())
    }).reset_index()
    
    daily.columns = ['Data', 'Valor Projetado', 'Tipos']
    daily = daily.sort_values('Data')
    daily['Saldo Acumulado'] = daily['Valor Projetado'].cumsum()
    
    return daily

# Título principal
st.title("💰 Dashboard de Fluxo de Caixa - PRO CLEAN")
st.markdown("---")

# Sidebar para upload e filtros
with st.sidebar:
    st.header("📁 Upload da Base")
    uploaded_file = st.file_uploader(
        "Escolha o arquivo Base.xlsx",
        type=['xlsx'],
        help="Faça upload do arquivo Excel com as abas Faturamento e Pagamentos"
    )
    
    if uploaded_file:
        st.success("Arquivo carregado com sucesso!")
    
    st.markdown("---")
    st.header("🔍 Filtros")
    
    # Carregar dados se arquivo foi uploadado
    if uploaded_file:
        df_fat, df_pag = load_data(uploaded_file)
        df_fat = process_faturamento(df_fat)
        df_pag = process_pagamentos(df_pag)
        
        # Filtros
        empresas = st.multiselect(
            "Empresa",
            options=df_pag['EMPRESA'].unique() if not df_pag.empty else []
        )
        
        # Data range
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=datetime(2025, 1, 1)
            )
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=datetime.now()
            )
        
        proj_dias = st.slider(
            "Dias de Projeção",
            min_value=7,
            max_value=90,
            value=30,
            step=1
        )
    else:
        st.info("👆 Faça upload do arquivo Base.xlsx para começar")
        empresas = []
        data_inicio = datetime(2025, 1, 1)
        data_fim = datetime.now()
        proj_dias = 30
        df_fat, df_pag = pd.DataFrame(), pd.DataFrame()

# Main content
if uploaded_file and not df_pag.empty:
    # Processar dados com filtros
    real_flow = create_real_cash_flow(
        df_pag, df_fat, 
        empresas=empresas,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    projecoes = create_projected_cash_flow(df_fat, df_pag, proj_dias)
    daily_proj = create_daily_projection(df_fat, df_pag, proj_dias)
    
    # Tabs para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Fluxo Real", 
        "📈 Projeções", 
        "📅 Visão Diária",
        "📋 Detalhamento"
    ])
    
    with tab1:
        st.header("Fluxo de Caixa Real por Categoria")
        
        if not real_flow.empty:
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_saidas = real_flow['Total'].sum()
                st.metric("Total de Saídas", f"R$ {total_saidas:,.2f}")
            with col2:
                num_categorias = len(real_flow)
                st.metric("Categorias", f"{num_categorias}")
            with col3:
                media_mensal = real_flow.iloc[:, :-1].mean().mean()
                st.metric("Média Mensal", f"R$ {media_mensal:,.2f}")
            with col4:
                maior_categoria = real_flow.iloc[0].name if len(real_flow) > 0 else "N/A"
                st.metric("Maior Categoria", maior_categoria)
            
            # Gráfico de barras
            st.subheader("Distribuição por Categoria")
            fig = px.bar(
                real_flow.reset_index(),
                x='CATEGORIA',
                y='Total',
                title="Total de Saídas por Categoria",
                labels={'Total': 'Valor (R$)', 'CATEGORIA': 'Categoria'}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Heatmap mensal
            st.subheader("Heatmap Mensal de Saídas")
            heatmap_data = real_flow.drop('Total', axis=1).T
            fig = px.imshow(
                heatmap_data,
                labels=dict(x="Categoria", y="Mês", color="Valor (R$)"),
                aspect="auto",
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("Tabela Detalhada")
            
            # Formatar valores
            display_df = real_flow.copy()
            for col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"R$ {x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
    
    with tab2:
        st.header("Fluxo de Caixa Projetado")
        
        if not projecoes.empty:
            # Métricas de projeção
            col1, col2, col3 = st.columns(3)
            with col1:
                total_recebimentos = projecoes[projecoes['TIPO'] == 'RECEBIMENTO']['VALOR'].sum()
                st.metric("Total Recebimentos Projetados", f"R$ {total_recebimentos:,.2f}")
            with col2:
                total_pagamentos = projecoes[projecoes['TIPO'] == 'PAGAMENTO']['VALOR'].sum()
                st.metric("Total Pagamentos Projetados", f"R$ {total_pagamentos:,.2f}")
            with col3:
                saldo_projetado = projecoes['VALOR'].sum()
                st.metric("Saldo Projetado", f"R$ {saldo_projetado:,.2f}")
            
            # Gráfico de linha do saldo acumulado
            st.subheader("Evolução do Saldo Projetado")
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=projecoes['DATA_CAIXA'],
                y=projecoes['SALDO_ACUMULADO'],
                mode='lines+markers',
                name='Saldo Acumulado',
                line=dict(color='green', width=2)
            ))
            
            fig.update_layout(
                xaxis_title="Data",
                yaxis_title="Saldo (R$)",
                hovermode='x'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de barras por tipo
            fig = px.bar(
                projecoes,
                x='DATA_CAIXA',
                y='VALOR',
                color='TIPO',
                title="Projeção de Recebimentos e Pagamentos",
                barmode='group',
                color_discrete_map={'RECEBIMENTO': 'green', 'PAGAMENTO': 'red'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma projeção disponível para o período selecionado.")
    
    with tab3:
        st.header("Visão Diária das Projeções")
        
        if not daily_proj.empty:
            # Gráfico de barras diário
            fig = px.bar(
                daily_proj,
                x='Data',
                y='Valor Projetado',
                title="Projeção Diária de Fluxo de Caixa",
                labels={'Valor Projetado': 'Valor (R$)'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela diária
            st.subheader("Detalhamento Diário")
            
            # Formatar valores
            display_daily = daily_proj.copy()
            display_daily['Valor Projetado'] = display_daily['Valor Projetado'].apply(lambda x: f"R$ {x:,.2f}")
            display_daily['Saldo Acumulado'] = display_daily['Saldo Acumulado'].apply(lambda x: f"R$ {x:,.2f}")
            
            st.dataframe(display_daily, use_container_width=True)
        else:
            st.info("Nenhuma projeção diária disponível.")
    
    with tab4:
        st.header("Detalhamento de Transações")
        
        # Mostrar recebimentos
        st.subheader("📥 Recebimentos Futuros")
        recebimentos = projecoes[projecoes['TIPO'] == 'RECEBIMENTO'] if not projecoes.empty else pd.DataFrame()
        if not recebimentos.empty:
            display_rec = recebimentos[['DATA_CAIXA', 'DESCRICAO', 'VALOR']].copy()
            display_rec['VALOR'] = display_rec['VALOR'].apply(lambda x: f"R$ {x:,.2f}")
            display_rec.columns = ['Data Prevista', 'Cliente', 'Valor']
            st.dataframe(display_rec, use_container_width=True)
        else:
            st.info("Nenhum recebimento futuro encontrado.")
        
        # Mostrar pagamentos
        st.subheader("📤 Pagamentos Futuros")
        pagamentos = projecoes[projecoes['TIPO'] == 'PAGAMENTO'] if not projecoes.empty else pd.DataFrame()
        if not pagamentos.empty:
            display_pag = pagamentos[['DATA_CAIXA', 'DESCRICAO', 'VALOR']].copy()
            display_pag['VALOR'] = display_pag['VALOR'].apply(lambda x: f"R$ {x:,.2f}")
            display_pag.columns = ['Data Prevista', 'Descrição', 'Valor']
            st.dataframe(display_pag, use_container_width=True)
        else:
            st.info("Nenhum pagamento futuro encontrado.")
        
        # Estatísticas rápidas
        st.subheader("📊 Estatísticas Rápidas")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Maiores Recebimentos**")
            if not recebimentos.empty:
                top_rec = recebimentos.nlargest(5, 'VALOR')[['DESCRICAO', 'VALOR']]
                top_rec['VALOR'] = top_rec['VALOR'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(top_rec, use_container_width=True)
        
        with col2:
            st.markdown("**Maiores Pagamentos**")
            if not pagamentos.empty:
                top_pag = pagamentos.nlargest(5, 'VALOR')[['DESCRICAO', 'VALOR']]
                top_pag['VALOR'] = top_pag['VALOR'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(top_pag, use_container_width=True)

else:
    # Mensagem inicial quando não há dados
    st.info("👈 Faça upload do arquivo Base.xlsx no menu lateral para visualizar o dashboard")
    
    # Exemplo do layout
    st.markdown("""
    ### 📊 O que este dashboard oferece:
    
    - **Fluxo Real**: Análise detalhada de saídas por categoria e mês
    - **Projeções**: Fluxo de caixa projetado baseado em recebimentos e pagamentos futuros
    - **Visão Diária**: Detalhamento diário das projeções
    - **Filtros**: Filtre por empresa, período e visualize projeções personalizadas
    - **Gráficos Interativos**: Visualizações dinâmicas para melhor análise
    
    ### 📁 Estrutura esperada do arquivo:
    
    O arquivo deve conter duas abas:
    - **Faturamento**: Com colunas EMPRESA, COD, CLIENTE, CNPJ, DTEMISSAO, DTVENCIMENTO, VALORBRUTO, VALORLIQUIDO
    - **Pagamentos**: Com colunas Empresa, Segmento, Descrição, Dt.venc., Valor, Dt.pagto, Mês
    
    Após o upload, todos os dados serão processados automaticamente!
    """)

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido para análise de Fluxo de Caixa - PRO CLEAN")
