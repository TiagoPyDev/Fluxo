import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar

# Configuração da página
st.set_page_config(
    page_title="Fluxo de Caixa - PRO CLEAN",
    page_icon="💰",
    layout="wide"
)

# Funções de carregamento e processamento
@st.cache_data(ttl=60)
def load_data(uploaded_file):
    """Carrega dados do arquivo Excel uploadado"""
    if uploaded_file is not None:
        try:
            xls = pd.ExcelFile(uploaded_file)
            
            # Carrega as duas abas
            df_faturamento = pd.read_excel(xls, 'Faturamento')
            df_pagamentos = pd.read_excel(xls, 'Pagamentos')
            
            return df_faturamento, df_pagamentos
        except Exception as e:
            st.error(f"Erro ao carregar arquivo: {e}")
            return None, None
    return None, None

def process_faturamento(df):
    """Processa a base de faturamento"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Padronizar nomes das colunas
    df.columns = [str(col).strip().upper() for col in df.columns]
    
    # Mapear possíveis nomes de colunas
    col_map = {
        'DTEMISSAO': 'DTEMISSAO',
        'DT EMISSÃO': 'DTEMISSAO',
        'DATA EMISSÃO': 'DTEMISSAO',
        'DTVENCIMENTO': 'DTVENCIMENTO',
        'DT VENCIMENTO': 'DTVENCIMENTO',
        'DATA VENCIMENTO': 'DTVENCIMENTO',
        'VALORBRUTO': 'VALORBRUTO',
        'VALOR BRUTO': 'VALORBRUTO',
        'VALORLIQUIDO': 'VALORLIQUIDO',
        'VALOR LIQUIDO': 'VALORLIQUIDO',
        'VALOR LÍQUIDO': 'VALORLIQUIDO',
        'CLIENTE': 'CLIENTE',
        'EMPRESA': 'EMPRESA'
    }
    
    # Renomear colunas baseado no mapa
    for old_col, new_col in col_map.items():
        if old_col in df.columns and new_col not in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)
    
    # Converter datas
    if 'DTEMISSAO' in df.columns:
        df['DTEMISSAO'] = pd.to_datetime(df['DTEMISSAO'], errors='coerce')
    if 'DTVENCIMENTO' in df.columns:
        df['DTVENCIMENTO'] = pd.to_datetime(df['DTVENCIMENTO'], errors='coerce')
    
    # Usar VALORLIQUIDO se disponível, senão VALORBRUTO
    if 'VALORLIQUIDO' in df.columns:
        df['VALOR_RECEBER'] = pd.to_numeric(df['VALORLIQUIDO'], errors='coerce').fillna(0)
    elif 'VALORBRUTO' in df.columns:
        df['VALOR_RECEBER'] = pd.to_numeric(df['VALORBRUTO'], errors='coerce').fillna(0)
    else:
        valor_cols = [col for col in df.columns if 'VALOR' in col]
        if valor_cols:
            df['VALOR_RECEBER'] = pd.to_numeric(df[valor_cols[0]], errors='coerce').fillna(0)
        else:
            df['VALOR_RECEBER'] = 0
    
    # Garantir que temos CLIENTE
    if 'CLIENTE' not in df.columns:
        df['CLIENTE'] = 'NÃO INFORMADO'
    
    return df

def process_pagamentos(df):
    """Processa a base de pagamentos de forma robusta"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Padronizar nomes das colunas
    df.columns = [str(col).strip().upper() for col in df.columns]
    
    # Mapear possíveis nomes de colunas
    col_map = {
        'EMPRESA': 'EMPRESA',
        'SEGMENTO': 'SEGMENTO',
        'DESCRIÇÃO': 'DESCRICAO',
        'DESCRICAO': 'DESCRICAO',
        'DESCR': 'DESCRICAO',
        'DT.VENC.': 'DTVENC',
        'DT VENC': 'DTVENC',
        'DTVENC': 'DTVENC',
        'DATA VENCIMENTO': 'DTVENC',
        'DT.PAGTO': 'DTPAGTO',
        'DT PAGTO': 'DTPAGTO',
        'DTPAGTO': 'DTPAGTO',
        'DATA PAGAMENTO': 'DTPAGTO',
        'VALOR': 'VALOR',
        'MÊS': 'MES_REF',
        'MES': 'MES_REF'
    }
    
    # Renomear colunas
    for old_col, new_col in col_map.items():
        if old_col in df.columns and new_col not in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)
    
    # Garantir colunas essenciais
    if 'EMPRESA' not in df.columns:
        df['EMPRESA'] = 'PRO CLEAN'
    
    if 'DESCRICAO' not in df.columns:
        desc_cols = [col for col in df.columns if 'DESCR' in col]
        if desc_cols:
            df.rename(columns={desc_cols[0]: 'DESCRICAO'}, inplace=True)
        else:
            df['DESCRICAO'] = 'SEM DESCRIÇÃO'
    
    if 'SEGMENTO' not in df.columns:
        df['SEGMENTO'] = 0
    
    # Converter datas
    if 'DTVENC' in df.columns:
        df['DTVENC'] = pd.to_datetime(df['DTVENC'], errors='coerce')
    else:
        df['DTVENC'] = pd.NaT
    
    if 'DTPAGTO' in df.columns:
        df['DTPAGTO'] = pd.to_datetime(df['DTPAGTO'], errors='coerce')
    else:
        df['DTPAGTO'] = pd.NaT
    
    # Garantir que VALOR é numérico
    if 'VALOR' in df.columns:
        df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0)
    else:
        valor_cols = [col for col in df.columns if 'VALOR' in col]
        if valor_cols:
            df['VALOR'] = pd.to_numeric(df[valor_cols[0]], errors='coerce').fillna(0)
        else:
            df['VALOR'] = 0
    
    return df

def calculate_monthly_flow(df_fat, df_pag, data_inicio=None, data_fim=None):
    """Calcula fluxo mensal de entradas e saídas"""
    
    resultado = pd.DataFrame()
    
    # Processar entradas (faturamento)
    if not df_fat.empty and 'DTVENCIMENTO' in df_fat.columns:
        entradas = df_fat.copy()
        
        # Aplicar filtros de data
        if data_inicio and data_fim and not entradas.empty:
            entradas = entradas[
                (entradas['DTVENCIMENTO'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                (entradas['DTVENCIMENTO'].dt.date <= pd.Timestamp(data_fim).date())
            ]
        
        if not entradas.empty:
            entradas['MES_ANO'] = entradas['DTVENCIMENTO'].dt.to_period('M').astype(str)
            entradas_mensal = entradas.groupby('MES_ANO').agg({
                'VALOR_RECEBER': 'sum'
            }).reset_index()
            entradas_mensal.columns = ['MES_ANO', 'ENTRADAS']
            entradas_mensal = entradas_mensal.sort_values('MES_ANO')
            resultado = entradas_mensal
    
    # Processar saídas (pagamentos)
    if not df_pag.empty:
        saidas = df_pag.copy()
        
        # Aplicar filtros de data
        if data_inicio and data_fim:
            if 'DTPAGTO' in saidas.columns and saidas['DTPAGTO'].notna().any():
                saidas = saidas[
                    (saidas['DTPAGTO'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                    (saidas['DTPAGTO'].dt.date <= pd.Timestamp(data_fim).date())
                ]
                saidas['MES_ANO'] = saidas['DTPAGTO'].dt.to_period('M').astype(str)
            elif 'DTVENC' in saidas.columns and saidas['DTVENC'].notna().any():
                saidas = saidas[
                    (saidas['DTVENC'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                    (saidas['DTVENC'].dt.date <= pd.Timestamp(data_fim).date())
                ]
                saidas['MES_ANO'] = saidas['DTVENC'].dt.to_period('M').astype(str)
        
        if not saidas.empty and 'MES_ANO' in saidas.columns:
            saidas_mensal = saidas.groupby('MES_ANO').agg({
                'VALOR': 'sum'
            }).reset_index()
            saidas_mensal.columns = ['MES_ANO', 'SAIDAS']
            saidas_mensal['SAIDAS'] = saidas_mensal['SAIDAS'].abs()
            
            # Merge com resultado
            if resultado.empty:
                resultado = saidas_mensal
            else:
                resultado = pd.merge(resultado, saidas_mensal, on='MES_ANO', how='outer')
    
    if resultado.empty:
        return pd.DataFrame()
    
    # Preencher NaN com 0
    resultado = resultado.fillna(0)
    
    # Calcular saldo
    if 'ENTRADAS' in resultado.columns and 'SAIDAS' in resultado.columns:
        resultado['SALDO'] = resultado['ENTRADAS'] - resultado['SAIDAS']
    elif 'ENTRADAS' in resultado.columns:
        resultado['SALDO'] = resultado['ENTRADAS']
        resultado['SAIDAS'] = 0
    elif 'SAIDAS' in resultado.columns:
        resultado['SALDO'] = -resultado['SAIDAS']
        resultado['ENTRADAS'] = 0
    
    # Ordenar por mês
    resultado = resultado.sort_values('MES_ANO')
    
    return resultado

def calculate_projected_monthly_flow(df_fat, df_pag, data_inicio=None, data_fim=None):
    """
    Calcula fluxo mensal PROJETADO baseado nas datas de vencimento
    Recebimentos: data de vencimento + 2 dias
    Pagamentos: data de vencimento
    """
    
    resultado = pd.DataFrame()
    
    # Projetar recebimentos futuros
    if not df_fat.empty and 'DTVENCIMENTO' in df_fat.columns:
        recebimentos = df_fat.copy()
        
        # Aplicar data de caixa (vencimento + 2 dias)
        recebimentos['DATA_CAIXA'] = recebimentos['DTVENCIMENTO'] + pd.Timedelta(days=2)
        
        # Aplicar filtros de data
        if data_inicio and data_fim and not recebimentos.empty:
            recebimentos = recebimentos[
                (recebimentos['DATA_CAIXA'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                (recebimentos['DATA_CAIXA'].dt.date <= pd.Timestamp(data_fim).date())
            ]
        
        if not recebimentos.empty:
            recebimentos['MES_ANO'] = recebimentos['DATA_CAIXA'].dt.to_period('M').astype(str)
            recebimentos_mensal = recebimentos.groupby('MES_ANO').agg({
                'VALOR_RECEBER': 'sum'
            }).reset_index()
            recebimentos_mensal.columns = ['MES_ANO', 'ENTRADAS_PROJ']
            recebimentos_mensal = recebimentos_mensal.sort_values('MES_ANO')
            resultado = recebimentos_mensal
    
    # Projetar pagamentos futuros
    if not df_pag.empty and 'DTVENC' in df_pag.columns:
        pagamentos = df_pag.copy()
        
        # Usar data de vencimento para pagamentos
        pagamentos['DATA_CAIXA'] = pagamentos['DTVENC']
        
        # Aplicar filtros de data
        if data_inicio and data_fim:
            pagamentos = pagamentos[
                (pagamentos['DATA_CAIXA'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                (pagamentos['DATA_CAIXA'].dt.date <= pd.Timestamp(data_fim).date())
            ]
        
        if not pagamentos.empty:
            pagamentos['MES_ANO'] = pagamentos['DATA_CAIXA'].dt.to_period('M').astype(str)
            pagamentos_mensal = pagamentos.groupby('MES_ANO').agg({
                'VALOR': 'sum'
            }).reset_index()
            pagamentos_mensal.columns = ['MES_ANO', 'SAIDAS_PROJ']
            pagamentos_mensal['SAIDAS_PROJ'] = pagamentos_mensal['SAIDAS_PROJ'].abs()
            
            # Merge com resultado
            if resultado.empty:
                resultado = pagamentos_mensal
                resultado.rename(columns={'SAIDAS_PROJ': 'SAIDAS_PROJ'}, inplace=True)
            else:
                resultado = pd.merge(resultado, pagamentos_mensal, on='MES_ANO', how='outer')
    
    if resultado.empty:
        return pd.DataFrame()
    
    # Preencher NaN com 0
    resultado = resultado.fillna(0)
    
    # Garantir que temos ambas as colunas
    if 'ENTRADAS_PROJ' not in resultado.columns:
        resultado['ENTRADAS_PROJ'] = 0
    if 'SAIDAS_PROJ' not in resultado.columns:
        resultado['SAIDAS_PROJ'] = 0
    
    # Calcular saldo projetado
    resultado['SALDO_PROJ'] = resultado['ENTRADAS_PROJ'] - resultado['SAIDAS_PROJ']
    
    # Ordenar por mês
    resultado = resultado.sort_values('MES_ANO')
    
    return resultado

def calculate_daily_projection(df_fat, df_pag, data_inicio=None, data_fim=None):
    """Calcula projeção diária detalhada"""
    
    projecoes = []
    
    # Recebimentos projetados
    if not df_fat.empty and 'DTVENCIMENTO' in df_fat.columns:
        recebimentos = df_fat.copy()
        recebimentos['DATA_EFETIVA'] = recebimentos['DTVENCIMENTO'] + pd.Timedelta(days=2)
        recebimentos['TIPO'] = 'RECEBIMENTO'
        recebimentos['VALOR'] = recebimentos['VALOR_RECEBER']
        recebimentos['DESCRICAO'] = recebimentos['CLIENTE'].astype(str)
        
        # Aplicar filtros de data
        if data_inicio and data_fim:
            recebimentos = recebimentos[
                (recebimentos['DATA_EFETIVA'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                (recebimentos['DATA_EFETIVA'].dt.date <= pd.Timestamp(data_fim).date())
            ]
        
        if not recebimentos.empty:
            projecoes.append(recebimentos[['DATA_EFETIVA', 'TIPO', 'VALOR', 'DESCRICAO']])
    
    # Pagamentos projetados
    if not df_pag.empty and 'DTVENC' in df_pag.columns:
        pagamentos = df_pag.copy()
        pagamentos['DATA_EFETIVA'] = pagamentos['DTVENC']
        pagamentos['TIPO'] = 'PAGAMENTO'
        pagamentos['VALOR'] = pagamentos['VALOR'].abs()
        pagamentos['DESCRICAO'] = pagamentos['DESCRICAO'].fillna('Pagamento')
        
        # Aplicar filtros de data
        if data_inicio and data_fim:
            pagamentos = pagamentos[
                (pagamentos['DATA_EFETIVA'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                (pagamentos['DATA_EFETIVA'].dt.date <= pd.Timestamp(data_fim).date())
            ]
        
        if not pagamentos.empty:
            projecoes.append(pagamentos[['DATA_EFETIVA', 'TIPO', 'VALOR', 'DESCRICAO']])
    
    # Combinar projeções
    if projecoes:
        df_proj = pd.concat(projecoes, ignore_index=True)
        df_proj = df_proj.sort_values('DATA_EFETIVA')
        
        # Calcular valor líquido e saldo acumulado
        df_proj['VALOR_LIQUIDO'] = df_proj.apply(
            lambda x: x['VALOR'] if x['TIPO'] == 'RECEBIMENTO' else -x['VALOR'], 
            axis=1
        )
        df_proj['SALDO_ACUMULADO'] = df_proj['VALOR_LIQUIDO'].cumsum()
        
        return df_proj
    else:
        return pd.DataFrame()

def create_category_summary(df_pag, data_inicio=None, data_fim=None):
    """Cria resumo por categoria para gráfico de pizza"""
    if df_pag.empty:
        return pd.DataFrame()
    
    df = df_pag.copy()
    
    # Aplicar filtros de data
    if data_inicio and data_fim:
        if 'DTPAGTO' in df.columns and df['DTPAGTO'].notna().any():
            df = df[
                (df['DTPAGTO'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                (df['DTPAGTO'].dt.date <= pd.Timestamp(data_fim).date())
            ]
        elif 'DTVENC' in df.columns and df['DTVENC'].notna().any():
            df = df[
                (df['DTVENC'].dt.date >= pd.Timestamp(data_inicio).date()) & 
                (df['DTVENC'].dt.date <= pd.Timestamp(data_fim).date())
            ]
    
    if df.empty:
        return pd.DataFrame()
    
    # Criar categorias baseadas nos códigos de segmento
    df['SEGMENTO_STR'] = df['SEGMENTO'].astype(str).str[:4]
    
    categoria_map = {
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
    }
    
    df['CATEGORIA'] = df['SEGMENTO_STR'].map(categoria_map).fillna('OUTROS')
    
    # Identificar transferências
    if 'DESCRICAO' in df.columns:
        mask_transf = df['DESCRICAO'].str.contains('TRANSFERENCIA|CX - TRANSFERÊNCIA', na=False, case=False)
        df.loc[mask_transf, 'CATEGORIA'] = 'CX - TRANSFERÊNCIA'
    
    # Agrupar por categoria
    resumo = df.groupby('CATEGORIA').agg({
        'VALOR': lambda x: x.abs().sum()
    }).reset_index()
    
    resumo = resumo.sort_values('VALOR', ascending=False)
    
    return resumo

# Título principal
st.title("💰 Fluxo de Caixa - PRO CLEAN")
st.markdown("---")

# Sidebar para upload e filtros
with st.sidebar:
    st.header("📁 Upload da Base")
    uploaded_file = st.file_uploader(
        "Escolha o arquivo Base.xlsx",
        type=['xlsx'],
        key="file_uploader"
    )
    
    if uploaded_file:
        with st.spinner("Carregando dados..."):
            df_fat_raw, df_pag_raw = load_data(uploaded_file)
            
            if df_fat_raw is not None:
                df_fat = process_faturamento(df_fat_raw)
                df_pag = process_pagamentos(df_pag_raw)
                
                st.success("✅ Dados carregados!")
                
                # Mostrar estatísticas básicas
                st.markdown("---")
                st.header("📊 Estatísticas")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Faturamento", f"{len(df_fat)} registros")
                with col2:
                    st.metric("Pagamentos", f"{len(df_pag)} registros")
                
                # Filtros
                st.markdown("---")
                st.header("🔍 Filtros")
                
                # Filtro de empresa
                empresas = ['Todas']
                if not df_pag.empty and 'EMPRESA' in df_pag.columns:
                    empresas.extend(sorted(df_pag['EMPRESA'].unique().tolist()))
                
                empresa_selecionada = st.selectbox("Empresa", empresas)
                
                # Filtro de período
                st.subheader("Período de Análise")
                
                # Datas mínimas e máximas
                min_date = datetime(2025, 1, 1).date()
                max_date = datetime.now().date() + timedelta(days=90)
                
                col1, col2 = st.columns(2)
                with col1:
                    data_inicio = st.date_input(
                        "Data Início",
                        value=datetime(2025, 1, 1).date(),
                        min_value=min_date,
                        max_value=max_date
                    )
                with col2:
                    data_fim = st.date_input(
                        "Data Fim",
                        value=datetime.now().date() + timedelta(days=60),
                        min_value=min_date,
                        max_value=max_date
                    )
            else:
                st.error("Erro ao processar o arquivo. Verifique o formato.")
                st.stop()
    else:
        st.info("👆 Faça upload do arquivo Base.xlsx")
        st.stop()

# Main content
if not df_fat.empty or not df_pag.empty:
    # Aplicar filtro de empresa
    df_pag_filtrado = df_pag.copy()
    if empresa_selecionada != 'Todas' and not df_pag.empty and 'EMPRESA' in df_pag.columns:
        df_pag_filtrado = df_pag[df_pag['EMPRESA'] == empresa_selecionada]
    
    # Calcular fluxo REAL mensal
    fluxo_real = calculate_monthly_flow(
        df_fat, df_pag_filtrado,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    # Calcular fluxo PROJETADO mensal (baseado em vencimentos)
    fluxo_projetado = calculate_projected_monthly_flow(
        df_fat, df_pag_filtrado,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    # Calcular projeção diária
    projecao_diaria = calculate_daily_projection(
        df_fat, df_pag_filtrado,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    # Calcular resumo por categoria
    resumo_categorias = create_category_summary(
        df_pag_filtrado,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    # Layout em duas colunas para métricas principais
    st.header("📈 Visão Geral")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_entradas_real = fluxo_real['ENTRADAS'].sum() if not fluxo_real.empty else 0
        st.metric(
            "💰 Entradas Realizadas",
            f"R$ {total_entradas_real:,.2f}"
        )
    
    with col2:
        total_saidas_real = fluxo_real['SAIDAS'].sum() if not fluxo_real.empty else 0
        st.metric(
            "💸 Saídas Realizadas",
            f"R$ {total_saidas_real:,.2f}"
        )
    
    with col3:
        total_entradas_proj = fluxo_projetado['ENTRADAS_PROJ'].sum() if not fluxo_projetado.empty else 0
        st.metric(
            "📊 Entradas Projetadas",
            f"R$ {total_entradas_proj:,.2f}"
        )
    
    with col4:
        total_saidas_proj = fluxo_projetado['SAIDAS_PROJ'].sum() if not fluxo_projetado.empty else 0
        st.metric(
            "📉 Saídas Projetadas",
            f"R$ {total_saidas_proj:,.2f}"
        )
    
    st.markdown("---")
    
    # Tabs para separar Fluxo Real e Projetado
    tab1, tab2, tab3 = st.tabs(["📊 Fluxo Real", "🔮 Fluxo Projetado", "📅 Visão Diária"])
    
    with tab1:
        st.header("Fluxo de Caixa Realizado")
        
        if not fluxo_real.empty:
            fig_real = go.Figure()
            
            # Barras de entradas
            fig_real.add_trace(go.Bar(
                x=fluxo_real['MES_ANO'],
                y=fluxo_real['ENTRADAS'],
                name='Entradas Realizadas',
                marker_color='#2E86AB',
                text=fluxo_real['ENTRADAS'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='outside'
            ))
            
            # Barras de saídas
            fig_real.add_trace(go.Bar(
                x=fluxo_real['MES_ANO'],
                y=fluxo_real['SAIDAS'],
                name='Saídas Realizadas',
                marker_color='#A23B72',
                text=fluxo_real['SAIDAS'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='outside'
            ))
            
            # Linha de saldo
            fig_real.add_trace(go.Scatter(
                x=fluxo_real['MES_ANO'],
                y=fluxo_real['SALDO'],
                name='Saldo Realizado',
                mode='lines+markers',
                line=dict(color='#F18F01', width=3),
                marker=dict(size=8),
                yaxis='y2'
            ))
            
            fig_real.update_layout(
                barmode='group',
                xaxis_title="Mês",
                yaxis_title="Valor (R$)",
                yaxis2=dict(
                    title="Saldo (R$)",
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified',
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_real, use_container_width=True)
            
            # Tabela
            with st.expander("📋 Ver detalhamento mensal - Realizado"):
                tabela_real = fluxo_real.copy()
                for col in ['ENTRADAS', 'SAIDAS', 'SALDO']:
                    if col in tabela_real.columns:
                        tabela_real[col] = tabela_real[col].apply(lambda x: f'R$ {x:,.2f}')
                st.dataframe(tabela_real, use_container_width=True)
        else:
            st.info("ℹ️ Nenhum dado realizado encontrado para o período selecionado.")
    
    with tab2:
        st.header("Fluxo de Caixa Projetado")
        st.caption("Projeção baseada em: Recebimentos = vencimento + 2 dias | Pagamentos = vencimento")
        
        if not fluxo_projetado.empty:
            fig_proj = go.Figure()
            
            # Barras de entradas projetadas
            fig_proj.add_trace(go.Bar(
                x=fluxo_projetado['MES_ANO'],
                y=fluxo_projetado['ENTRADAS_PROJ'],
                name='Entradas Projetadas',
                marker_color='#2E86AB',
                text=fluxo_projetado['ENTRADAS_PROJ'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='outside'
            ))
            
            # Barras de saídas projetadas
            fig_proj.add_trace(go.Bar(
                x=fluxo_projetado['MES_ANO'],
                y=fluxo_projetado['SAIDAS_PROJ'],
                name='Saídas Projetadas',
                marker_color='#A23B72',
                text=fluxo_projetado['SAIDAS_PROJ'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='outside'
            ))
            
            # Linha de saldo projetado
            fig_proj.add_trace(go.Scatter(
                x=fluxo_projetado['MES_ANO'],
                y=fluxo_projetado['SALDO_PROJ'],
                name='Saldo Projetado',
                mode='lines+markers',
                line=dict(color='#F18F01', width=3, dash='dot'),
                marker=dict(size=8),
                yaxis='y2'
            ))
            
            fig_proj.update_layout(
                barmode='group',
                xaxis_title="Mês",
                yaxis_title="Valor (R$)",
                yaxis2=dict(
                    title="Saldo Projetado (R$)",
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified',
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_proj, use_container_width=True)
            
            # Tabela
            with st.expander("📋 Ver detalhamento mensal - Projetado"):
                tabela_proj = fluxo_projetado.copy()
                for col in ['ENTRADAS_PROJ', 'SAIDAS_PROJ', 'SALDO_PROJ']:
                    if col in tabela_proj.columns:
                        tabela_proj[col] = tabela_proj[col].apply(lambda x: f'R$ {x:,.2f}')
                st.dataframe(tabela_proj, use_container_width=True)
        else:
            st.info("ℹ️ Nenhuma projeção encontrada para o período selecionado.")
    
    with tab3:
        st.header("📅 Projeção Diária")
        
        if not projecao_diaria.empty:
            # Gráfico de projeção diária
            proj_diario = projecao_diaria.groupby('DATA_EFETIVA').agg({
                'VALOR_LIQUIDO': 'sum'
            }).reset_index()
            proj_diario['SALDO_ACUM'] = proj_diario['VALOR_LIQUIDO'].cumsum()
            
            fig_diario = go.Figure()
            
            # Barras de fluxo diário
            colors = ['#2E86AB' if x > 0 else '#A23B72' for x in proj_diario['VALOR_LIQUIDO']]
            
            fig_diario.add_trace(go.Bar(
                x=proj_diario['DATA_EFETIVA'],
                y=proj_diario['VALOR_LIQUIDO'],
                name='Fluxo Diário',
                marker_color=colors,
                text=proj_diario['VALOR_LIQUIDO'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='outside'
            ))
            
            # Linha de saldo acumulado
            fig_diario.add_trace(go.Scatter(
                x=proj_diario['DATA_EFETIVA'],
                y=proj_diario['SALDO_ACUM'],
                name='Saldo Acumulado',
                mode='lines+markers',
                line=dict(color='#F18F01', width=3),
                yaxis='y2'
            ))
            
            fig_diario.update_layout(
                xaxis_title="Data",
                yaxis_title="Valor (R$)",
                yaxis2=dict(
                    title="Saldo Acumulado (R$)",
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig_diario, use_container_width=True)
            
            # Métricas da projeção
            col_proj1, col_proj2, col_proj3 = st.columns(3)
            with col_proj1:
                rec_projetado = projecao_diaria[projecao_diaria['TIPO'] == 'RECEBIMENTO']['VALOR'].sum()
                st.metric("📥 Recebimentos", f"R$ {rec_projetado:,.2f}")
            with col_proj2:
                pag_projetado = projecao_diaria[projecao_diaria['TIPO'] == 'PAGAMENTO']['VALOR'].sum()
                st.metric("📤 Pagamentos", f"R$ {pag_projetado:,.2f}")
            with col_proj3:
                saldo_projetado = rec_projetado - pag_projetado
                st.metric("⚖️ Saldo Projetado", f"R$ {saldo_projetado:,.2f}")
            
            # Tabela de projeção diária
            with st.expander("📋 Ver detalhamento diário"):
                display_proj = projecao_diaria[['DATA_EFETIVA', 'TIPO', 'DESCRICAO', 'VALOR']].copy()
                display_proj.columns = ['Data', 'Tipo', 'Descrição', 'Valor']
                display_proj['Valor'] = display_proj['Valor'].apply(lambda x: f'R$ {x:,.2f}')
                st.dataframe(display_proj, use_container_width=True)
        else:
            st.info("ℹ️ Nenhuma projeção diária disponível para o período.")
    
    st.markdown("---")
    
    # Gráfico de pizza de categorias (ocupando largura total)
    st.header("🥧 Distribuição de Saídas por Categoria")
    
    if not resumo_categorias.empty:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Top 8 categorias + outros
            top_categorias = resumo_categorias.head(8).copy()
            if len(resumo_categorias) > 8:
                outros_valor = resumo_categorias.iloc[8:]['VALOR'].sum()
                if outros_valor > 0:
                    outros_row = pd.DataFrame({'CATEGORIA': ['OUTROS'], 'VALOR': [outros_valor]})
                    top_categorias = pd.concat([top_categorias, outros_row], ignore_index=True)
            
            fig_pizza = px.pie(
                top_categorias,
                values='VALOR',
                names='CATEGORIA',
                title="Distribuição por Categoria",
                hole=0.3
            )
            fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
            fig_pizza.update_layout(height=500)
            
            st.plotly_chart(fig_pizza, use_container_width=True)
        
        with col2:
            # Tabela de categorias
            st.subheader("Detalhamento por Categoria")
            display_cat = resumo_categorias.copy()
            display_cat['VALOR'] = display_cat['VALOR'].apply(lambda x: f'R$ {x:,.2f}')
            display_cat['%'] = (resumo_categorias['VALOR'] / resumo_categorias['VALOR'].sum() * 100).apply(lambda x: f'{x:.1f}%')
            st.dataframe(display_cat, use_container_width=True)
    else:
        st.info("ℹ️ Nenhum dado de categoria disponível.")
    
    st.markdown("---")
    
    # Rodapé com informações
    st.markdown(f"""
    **Período analisado:** {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}  
    **Empresa:** {empresa_selecionada}  
    **Projeção baseada em:** Recebimentos (vencimento + 2 dias) | Pagamentos (vencimento)
    """)

else:
    st.warning("⚠️ Nenhum dado disponível para análise.")

# Rodapé
st.markdown("---")
st.markdown("Dashboard de Fluxo de Caixa - PRO CLEAN | Atualizado em tempo real")
