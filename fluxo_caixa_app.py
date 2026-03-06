
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import calendar
import re

# Configuração da página
st.set_page_config(
    page_title="Fluxo de Caixa Projetado - Pro Clean",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
FERIADOS_NACIONAIS_2025 = [
    '2025-01-01',  # Confraternização Universal
    '2025-04-18',  # Sexta-feira Santa
    '2025-04-20',  # Páscoa
    '2025-04-21',  # Tiradentes
    '2025-05-01',  # Dia do Trabalho
    '2025-06-19',  # Corpus Christi
    '2025-09-07',  # Independência
    '2025-10-12',  # Nossa Sra. Aparecida
    '2025-11-02',  # Finados
    '2025-11-15',  # Proclamação da República
    '2025-12-25',  # Natal
]

FERIADOS_NACIONAIS_2026 = [
    '2026-01-01',  # Confraternização Universal
    '2026-02-16',  # Carnaval
    '2026-02-17',  # Carnaval
    '2026-04-03',  # Sexta-feira Santa
    '2026-04-05',  # Páscoa
    '2026-04-21',  # Tiradentes
    '2026-05-01',  # Dia do Trabalho
    '2026-06-04',  # Corpus Christi
    '2026-09-07',  # Independência
    '2026-10-12',  # Nossa Sra. Aparecida
    '2026-11-02',  # Finados
    '2026-11-15',  # Proclamação da República
    '2026-12-25',  # Natal
]

FERIADOS = FERIADOS_NACIONAIS_2025 + FERIADOS_NACIONAIS_2026

# Funções utilitárias
def parse_date(date_val):
    """Converte diferentes formatos de data para datetime"""
    if pd.isna(date_val):
        return pd.NaT
    
    if isinstance(date_val, (datetime, pd.Timestamp)):
        return pd.to_datetime(date_val)
    
    if isinstance(date_val, (int, float)):
        try:
            # Trata datas no formato Excel
            return pd.to_datetime('1899-12-30') + timedelta(days=int(date_val))
        except:
            return pd.NaT
    
    date_str = str(date_val).strip()
    
    # Remove timestamp se houver
    if ' ' in date_str:
        date_str = date_str.split(' ')[0]
    
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d/%m/%Y %H:%M:%S']:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue
    
    return pd.NaT

def is_business_day(date, feriados=None):
    """Verifica se a data é dia útil (segunda a sexta, não feriado)"""
    if feriados is None:
        feriados = []
    
    if date.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False
    
    date_str = date.strftime('%Y-%m-%d')
    if date_str in feriados:
        return False
    
    return True

def next_business_day(date, feriados=None):
    """Retorna o próximo dia útil após a data"""
    if feriados is None:
        feriados = []
    
    next_date = date
    while True:
        next_date += timedelta(days=1)
        if is_business_day(next_date, feriados):
            return next_date

def get_receipt_date(due_date, days_lag=2, feriados=None):
    """Calcula a data de recebimento (2 dias após o vencimento, considerando dias úteis)"""
    if feriados is None:
        feriados = []
    
    receipt_date = due_date
    for _ in range(days_lag):
        receipt_date = next_business_day(receipt_date, feriados)
    
    return receipt_date

def create_empresa_filter(df):
    """Cria filtro de empresa para sidebar"""
    empresas = ['TODAS'] + sorted(df['EMPRESA'].unique().tolist())
    return st.sidebar.selectbox('Empresa', empresas)

def create_period_filter(df):
    """Cria filtro de período para sidebar"""
    min_date = df['DTVENCIMENTO'].min()
    max_date = df['DTVENCIMENTO'].max()
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input('Data inicial', min_date)
    with col2:
        end_date = st.date_input('Data final', max_date)
    
    return start_date, end_date

def process_uploaded_file(uploaded_file):
    """Processa arquivo CSV/Excel carregado"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df_new = pd.read_csv(uploaded_file)
        else:
            df_new = pd.read_excel(uploaded_file)
        
        # Mapeia colunas
        column_mapping = {
            'EMPRESA': 'EMPRESA',
            'COD': 'COD',
            'CLIENTE': 'CLIENTE',
            'CNPJ': 'CNPJ',
            'DTEMISSAO': 'DTEMISSAO',
            'DTVENCIMENTO': 'DTVENCIMENTO',
            'VALORBRUTO': 'VALORBRUTO',
            'VALORLIQUIDO': 'VALORLIQUIDO'
        }
        
        # Renomeia colunas se necessário
        df_new.columns = [col.upper().strip() for col in df_new.columns]
        
        # Seleciona apenas colunas relevantes
        available_cols = [col for col in column_mapping.keys() if col in df_new.columns]
        df_new = df_new[available_cols].copy()
        
        # Converte datas
        for date_col in ['DTEMISSAO', 'DTVENCIMENTO']:
            if date_col in df_new.columns:
                df_new[date_col] = df_new[date_col].apply(parse_date)
        
        # Converte valores
        for value_col in ['VALORBRUTO', 'VALORLIQUIDO']:
            if value_col in df_new.columns:
                df_new[value_col] = pd.to_numeric(df_new[value_col], errors='coerce')
        
        return df_new
    except Exception as e:
        st.error(f'Erro ao processar arquivo: {str(e)}')
        return None

def load_sample_data():
    """Carrega dados de exemplo do arquivo"""
    try:
        # Cria um DataFrame com os dados do arquivo anexado
        data = []
        current_section = None
        
        # Simula a leitura do arquivo (na prática, você carregaria o arquivo real)
        # Como o arquivo é grande, vamos usar uma amostra representativa
        sample_clients = [
            '1300 JURUPIS', '14º CARTORIO DA LAPA', '32º CARTORIO DO SOCORRO',
            'ABOUT VILA MARIANA', 'ACQUA PARK BETHAVILLE', 'AD 330 ALTO DA BOA VISTA',
            'ADVANCED OFFICE PEDROSO', 'ÁGUAS DE MARÇO', 'ALBA', 'ALIVE'
        ]
        
        np.random.seed(42)
        
        for client in sample_clients:
            # Gera dados para cada cliente (12 meses)
            for i in range(12):
                base_date = datetime(2025, 1, 1) + timedelta(days=30*i)
                due_date = base_date + timedelta(days=10)
                
                valor_bruto = np.random.uniform(5000, 50000)
                valor_liquido = valor_bruto * np.random.uniform(0.8, 0.95)
                
                data.append({
                    'EMPRESA': 'PRO CLEAN',
                    'COD': np.random.randint(1000, 9999),
                    'CLIENTE': client,
                    'CNPJ': str(np.random.randint(10000000000000, 99999999999999)),
                    'DTEMISSAO': base_date,
                    'DTVENCIMENTO': due_date,
                    'VALORBRUTO': round(valor_bruto, 2),
                    'VALORLIQUIDO': round(valor_liquido, 2)
                })
        
        # Adiciona dados da PRO CLEAN LONDRINA
        for client in ['ARBO & FLORA', 'ASSOCIAÇÃO RURAL', 'ROYAL PARK']:
            for i in range(8):
                base_date = datetime(2025, 3, 1) + timedelta(days=30*i)
                due_date = base_date + timedelta(days=15)
                
                valor_bruto = np.random.uniform(5000, 30000)
                valor_liquido = valor_bruto * np.random.uniform(0.8, 0.95)
                
                data.append({
                    'EMPRESA': 'PRO CLEAN LONDRINA',
                    'COD': np.random.randint(1000, 9999),
                    'CLIENTE': client,
                    'CNPJ': str(np.random.randint(10000000000000, 99999999999999)),
                    'DTEMISSAO': base_date,
                    'DTVENCIMENTO': due_date,
                    'VALORBRUTO': round(valor_bruto, 2),
                    'VALORLIQUIDO': round(valor_liquido, 2)
                })
        
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f'Erro ao carregar dados de exemplo: {str(e)}')
        # Retorna DataFrame mínimo em caso de erro
        return pd.DataFrame(columns=['EMPRESA', 'COD', 'CLIENTE', 'CNPJ', 'DTEMISSAO', 'DTVENCIMENTO', 'VALORBRUTO', 'VALORLIQUIDO'])

@st.cache_data
def load_data():
    """Carrega dados históricos"""
    # Tenta carregar da sessão primeiro
    if 'df_historico' in st.session_state:
        return st.session_state.df_historico.copy()
    
    # Carrega dados de exemplo
    return load_sample_data()

def project_cash_flow(df, projection_months=6):
    """Projeta fluxo de caixa futuro baseado em histórico"""
    if df.empty:
        return pd.DataFrame()
    
    # Identifica periodicidade por cliente
    client_payment_days = {}
    
    for cliente in df['CLIENTE'].unique():
        cliente_df = df[df['CLIENTE'] == cliente].sort_values('DTVENCIMENTO')
        
        if len(cliente_df) > 1:
            # Calcula intervalo médio entre pagamentos
            intervals = []
            for i in range(1, len(cliente_df)):
                days_diff = (cliente_df.iloc[i]['DTVENCIMENTO'] - cliente_df.iloc[i-1]['DTVENCIMENTO']).days
                if days_diff > 0:
                    intervals.append(days_diff)
            
            if intervals:
                avg_interval = np.mean(intervals)
                # Valores mais comuns: 30, 60, 90 dias
                if avg_interval > 45:
                    interval = 60
                elif avg_interval > 25:
                    interval = 30
                else:
                    interval = 15
            else:
                interval = 30
        else:
            interval = 30
        
        # Calcula valor médio por pagamento
        avg_value = cliente_df['VALORLIQUIDO'].mean()
        
        client_payment_days[cliente] = {
            'interval': interval,
            'avg_value': avg_value,
            'last_date': cliente_df['DTVENCIMENTO'].max()
        }
    
    # Projeta próximos meses
    last_date = df['DTVENCIMENTO'].max()
    projections = []
    
    for cliente, info in client_payment_days.items():
        if pd.isna(info['last_date']):
            continue
        
        current_date = info['last_date']
        for _ in range(projection_months):
            current_date += timedelta(days=info['interval'])
            
            # Pula para próximo dia útil se necessário
            if not is_business_day(current_date, FERIADOS):
                current_date = next_business_day(current_date, FERIADOS)
            
            receipt_date = get_receipt_date(current_date, 2, FERIADOS)
            
            projections.append({
                'EMPRESA': df[df['CLIENTE'] == cliente]['EMPRESA'].iloc[0] if not df[df['CLIENTE'] == cliente].empty else 'PRO CLEAN',
                'COD': df[df['CLIENTE'] == cliente]['COD'].iloc[0] if not df[df['CLIENTE'] == cliente].empty else 0,
                'CLIENTE': cliente,
                'CNPJ': df[df['CLIENTE'] == cliente]['CNPJ'].iloc[0] if not df[df['CLIENTE'] == cliente].empty else '',
                'DTEMISSAO': current_date - timedelta(days=10),  # Estimativa
                'DTVENCIMENTO': current_date,
                'DT_RECEBIMENTO': receipt_date,
                'VALORBRUTO': info['avg_value'] * 1.1,  # Estimativa com acréscimo
                'VALORLIQUIDO': info['avg_value'],
                'TIPO': 'PROJETADO'
            })
    
    return pd.DataFrame(projections)

# Interface principal
st.title('💰 Fluxo de Caixa Projetado - Pro Clean')
st.markdown('---')

# Inicializa session state
if 'df_historico' not in st.session_state:
    st.session_state.df_historico = load_data()

if 'df_projecoes' not in st.session_state:
    st.session_state.df_projecoes = pd.DataFrame()

# Sidebar
with st.sidebar:
    st.header('📊 Controles')
    
    # Upload de arquivo
    uploaded_file = st.file_uploader(
        'Carregar base histórica (CSV/Excel)',
        type=['csv', 'xlsx', 'xls'],
        help='Arquivo com colunas: EMPRESA, COD, CLIENTE, CNPJ, DTEMISSAO, DTVENCIMENTO, VALORBRUTO, VALORLIQUIDO'
    )
    
    if uploaded_file:
        new_df = process_uploaded_file(uploaded_file)
        if new_df is not None and not new_df.empty:
            st.session_state.df_historico = new_df
            st.session_state.df_projecoes = pd.DataFrame()  # Limpa projeções
            st.success(f'✅ {len(new_df)} registros carregados!')
    
    st.markdown('---')
    
    # Filtros
    st.subheader('🔍 Filtros')
    
    if not st.session_state.df_historico.empty:
        df_historico = st.session_state.df_historico.copy()
        
        # Filtro empresa
        empresa_filter = create_empresa_filter(df_historico)
        
        # Filtro período
        start_date, end_date = create_period_filter(df_historico)
        
        # Filtro cliente
        clientes = ['TODOS'] + sorted(df_historico['CLIENTE'].unique().tolist())
        cliente_filter = st.selectbox('Cliente', clientes)
        
        st.markdown('---')
        
        # Configurações de projeção
        st.subheader('📈 Projeções')
        projection_months = st.slider('Meses para projetar', 1, 12, 6)
        
        if st.button('🔄 Gerar Projeções', type='primary', use_container_width=True):
            with st.spinner('Calculando projeções...'):
                st.session_state.df_projecoes = project_cash_flow(df_historico, projection_months)
                st.success(f'✅ {len(st.session_state.df_projecoes)} projeções geradas!')
        
        st.markdown('---')
        
        # Ações
        st.subheader('⚙️ Ações')
        
        if st.button('🗑️ Limpar Dados', use_container_width=True):
            st.session_state.df_historico = pd.DataFrame()
            st.session_state.df_projecoes = pd.DataFrame()
            st.rerun()

# Main content
if st.session_state.df_historico.empty:
    st.info('👈 Carregue uma base histórica usando o menu lateral para começar.')
    
    # Botão para carregar dados de exemplo
    if st.button('📋 Carregar dados de exemplo'):
        st.session_state.df_historico = load_sample_data()
        st.rerun()
else:
    df_historico = st.session_state.df_historico.copy()
    
    # Aplica filtros
    df_filtered = df_historico.copy()
    
    if 'empresa_filter' in locals() and empresa_filter != 'TODAS':
        df_filtered = df_filtered[df_filtered['EMPRESA'] == empresa_filter]
    
    if 'start_date' in locals() and 'end_date' in locals():
        df_filtered = df_filtered[
            (df_filtered['DTVENCIMENTO'].dt.date >= start_date) &
            (df_filtered['DTVENCIMENTO'].dt.date <= end_date)
        ]
    
    if 'cliente_filter' in locals() and cliente_filter != 'TODOS':
        df_filtered = df_filtered[df_filtered['CLIENTE'] == cliente_filter]
    
    # Calcula datas de recebimento
    df_filtered['DT_RECEBIMENTO'] = df_filtered['DTVENCIMENTO'].apply(
        lambda x: get_receipt_date(x, 2, FERIADOS)
    )
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        '📊 Dashboard',
        '📋 Dados Históricos',
        '📈 Projeções',
        '📅 Calendário de Pagamentos',
        '📤 Upload Mensal'
    ])
    
    with tab1:
        st.header('Dashboard de Fluxo de Caixa')
        
        # Combina histórico com projeções
        df_combined = df_filtered.copy()
        df_combined['TIPO'] = 'HISTÓRICO'
        
        if not st.session_state.df_projecoes.empty:
            df_proj = st.session_state.df_projecoes.copy()
            
            # Aplica mesmos filtros às projeções
            if empresa_filter != 'TODAS':
                df_proj = df_proj[df_proj['EMPRESA'] == empresa_filter]
            if cliente_filter != 'TODOS':
                df_proj = df_proj[df_proj['CLIENTE'] == cliente_filter]
            
            df_combined = pd.concat([df_combined, df_proj], ignore_index=True)
        
        if not df_combined.empty:
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    'Total Recebido (Histórico)',
                    f'R$ {df_filtered["VALORLIQUIDO"].sum():,.2f}',
                    help='Soma dos valores líquidos históricos'
                )
            
            with col2:
                st.metric(
                    'Total Projetado',
                    f'R$ {df_proj["VALORLIQUIDO"].sum():,.2f}' if not st.session_state.df_projecoes.empty else 'R$ 0,00',
                    help='Soma dos valores líquidos projetados'
                )
            
            with col3:
                st.metric(
                    'Média Mensal',
                    f'R$ {df_filtered.groupby(df_filtered["DTVENCIMENTO"].dt.to_period("M"))["VALORLIQUIDO"].sum().mean():,.2f}',
                    help='Média mensal de recebimentos'
                )
            
            with col4:
                st.metric(
                    'Qtd. Clientes',
                    df_filtered['CLIENTE'].nunique()
                )
            
            st.markdown('---')
            
            # Gráfico de fluxo de caixa
            st.subheader('Fluxo de Caixa por Mês')
            
            df_monthly = df_combined.copy()
            df_monthly['Mês'] = df_monthly['DT_RECEBIMENTO'].dt.to_period('M').astype(str)
            
            monthly_by_type = df_monthly.groupby(['Mês', 'TIPO'])['VALORLIQUIDO'].sum().reset_index()
            
            fig = px.bar(
                monthly_by_type,
                x='Mês',
                y='VALORLIQUIDO',
                color='TIPO',
                title='Fluxo de Caixa Mensal',
                labels={'VALORLIQUIDO': 'Valor (R$)', 'Mês': 'Mês'},
                barmode='group'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Top clientes
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader('Top 10 Clientes por Valor')
                top_clients = df_filtered.groupby('CLIENTE')['VALORLIQUIDO'].sum().sort_values(ascending=False).head(10)
                fig = px.pie(
                    values=top_clients.values,
                    names=top_clients.index,
                    title='Distribuição por Cliente'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader('Fluxo por Empresa')
                company_flow = df_filtered.groupby('EMPRESA')['VALORLIQUIDO'].sum()
                fig = px.bar(
                    x=company_flow.index,
                    y=company_flow.values,
                    title='Total por Empresa',
                    labels={'x': 'Empresa', 'y': 'Valor (R$)'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header('📋 Dados Históricos')
        
        if df_filtered.empty:
            st.warning('Nenhum dado encontrado com os filtros atuais.')
        else:
            # Métricas
            st.subheader('Resumo')
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric('Total Registros', len(df_filtered))
            with col2:
                st.metric('Período', f"{df_filtered['DTVENCIMENTO'].min().strftime('%d/%m/%Y')} - {df_filtered['DTVENCIMENTO'].max().strftime('%d/%m/%Y')}")
            with col3:
                st.metric('Valor Total', f'R$ {df_filtered["VALORLIQUIDO"].sum():,.2f}')
            with col4:
                st.metric('Média por Nota', f'R$ {df_filtered["VALORLIQUIDO"].mean():,.2f}')
            
            st.markdown('---')
            
            # Tabela
            st.subheader('Tabela de Dados')
            
            df_display = df_filtered.copy()
            for col in ['DTEMISSAO', 'DTVENCIMENTO', 'DT_RECEBIMENTO']:
                df_display[col] = df_display[col].dt.strftime('%d/%m/%Y')
            
            df_display['VALORBRUTO'] = df_display['VALORBRUTO'].apply(lambda x: f'R$ {x:,.2f}')
            df_display['VALORLIQUIDO'] = df_display['VALORLIQUIDO'].apply(lambda x: f'R$ {x:,.2f}')
            
            st.dataframe(df_display, use_container_width=True, height=500)
            
            # Download
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                '📥 Download CSV',
                csv,
                'dados_historicos.csv',
                'text/csv'
            )
    
    with tab3:
        st.header('📈 Projeções Futuras')
        
        if st.session_state.df_projecoes.empty:
            st.info('Clique em "Gerar Projeções" no menu lateral para ver as projeções.')
        else:
            df_proj = st.session_state.df_projecoes.copy()
            
            # Aplica filtros
            if empresa_filter != 'TODAS':
                df_proj = df_proj[df_proj['EMPRESA'] == empresa_filter]
            if cliente_filter != 'TODOS':
                df_proj = df_proj[df_proj['CLIENTE'] == cliente_filter]
            
            if df_proj.empty:
                st.warning('Nenhuma projeção encontrada com os filtros atuais.')
            else:
                # Métricas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric('Total Projetado', f'R$ {df_proj["VALORLIQUIDO"].sum():,.2f}')
                with col2:
                    st.metric('Média por Período', f'R$ {df_proj["VALORLIQUIDO"].mean():,.2f}')
                with col3:
                    st.metric('Qtd. Projeções', len(df_proj))
                
                st.markdown('---')
                
                # Gráfico de projeções
                df_proj_monthly = df_proj.copy()
                df_proj_monthly['Mês'] = df_proj_monthly['DT_RECEBIMENTO'].dt.to_period('M').astype(str)
                monthly_proj = df_proj_monthly.groupby('Mês')['VALORLIQUIDO'].sum().reset_index()
                
                fig = px.line(
                    monthly_proj,
                    x='Mês',
                    y='VALORLIQUIDO',
                    title='Projeção Mensal',
                    markers=True,
                    labels={'VALORLIQUIDO': 'Valor Projetado (R$)'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela de projeções
                st.subheader('Detalhamento das Projeções')
                
                df_proj_display = df_proj.copy()
                for col in ['DTEMISSAO', 'DTVENCIMENTO', 'DT_RECEBIMENTO']:
                    df_proj_display[col] = df_proj_display[col].dt.strftime('%d/%m/%Y')
                
                df_proj_display['VALORBRUTO'] = df_proj_display['VALORBRUTO'].apply(lambda x: f'R$ {x:,.2f}')
                df_proj_display['VALORLIQUIDO'] = df_proj_display['VALORLIQUIDO'].apply(lambda x: f'R$ {x:,.2f}')
                
                st.dataframe(df_proj_display, use_container_width=True, height=500)
                
                # Download
                csv = df_proj.to_csv(index=False).encode('utf-8')
                st.download_button(
                    '📥 Download Projeções CSV',
                    csv,
                    'projecoes.csv',
                    'text/csv'
                )
    
    with tab4:
        st.header('📅 Calendário de Pagamentos')
        
        # Prepara dados
        df_payments = df_filtered.copy()
        
        if not st.session_state.df_projecoes.empty:
            df_proj_temp = st.session_state.df_projecoes.copy()
            if empresa_filter != 'TODAS':
                df_proj_temp = df_proj_temp[df_proj_temp['EMPRESA'] == empresa_filter]
            if cliente_filter != 'TODOS':
                df_proj_temp = df_proj_temp[df_proj_temp['CLIENTE'] == cliente_filter]
            df_payments = pd.concat([df_payments, df_proj_temp], ignore_index=True)
        
        # Adiciona status
        today = datetime.now().date()
        
        df_payments['STATUS'] = df_payments['DT_RECEBIMENTO'].apply(
            lambda x: '📅 Pendente' if x.date() > today else '✅ Realizado' if x.date() <= today else '❌ Atrasado'
        )
        
        df_payments['DIAS_ATE_PAGAMENTO'] = (df_payments['DT_RECEBIMENTO'].dt.date - today).dt.days
        
        # Filtros do calendário
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                'Status',
                ['TODOS', '📅 Pendente', '✅ Realizado', '❌ Atrasado']
            )
        
        with col2:
            days_filter = st.number_input('Dias até pagamento', min_value=-30, max_value=90, value=30)
        
        with col3:
            min_value = st.number_input('Valor mínimo (R$)', min_value=0.0, value=0.0)
        
        # Aplica filtros
        if status_filter != 'TODOS':
            df_payments = df_payments[df_payments['STATUS'] == status_filter]
        
        df_payments = df_payments[df_payments['DIAS_ATE_PAGAMENTO'] <= days_filter]
        df_payments = df_payments[df_payments['VALORLIQUIDO'] >= min_value]
        
        df_payments = df_payments.sort_values('DT_RECEBIMENTO')
        
        st.subheader(f'Próximos Pagamentos ({len(df_payments)})')
        
        if df_payments.empty:
            st.info('Nenhum pagamento encontrado com os filtros atuais.')
        else:
            # Formata para exibição
            df_pay_display = df_payments[['DT_RECEBIMENTO', 'EMPRESA', 'CLIENTE', 'VALORLIQUIDO', 'STATUS', 'DIAS_ATE_PAGAMENTO']].copy()
            df_pay_display['DT_RECEBIMENTO'] = df_pay_display['DT_RECEBIMENTO'].dt.strftime('%d/%m/%Y')
            df_pay_display['VALORLIQUIDO'] = df_pay_display['VALORLIQUIDO'].apply(lambda x: f'R$ {x:,.2f}')
            
            st.dataframe(df_pay_display, use_container_width=True, height=500)
    
    with tab5:
        st.header('📤 Upload Mensal de Pagamentos')
        st.markdown('Carregue arquivos com os pagamentos realizados para atualizar a base histórica.')
        
        # Upload de pagamentos
        payment_file = st.file_uploader(
            'Carregar pagamentos realizados (CSV/Excel)',
            type=['csv', 'xlsx', 'xls'],
            key='payment_upload'
        )
        
        if payment_file:
            df_payments_new = process_uploaded_file(payment_file)
            
            if df_payments_new is not None and not df_payments_new.empty:
                st.success(f'✅ {len(df_payments_new)} pagamentos carregados!')
                
                # Mostra preview
                st.subheader('Preview dos dados carregados')
                st.dataframe(df_payments_new.head(10), use_container_width=True)
                
                # Opções de merge
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button('🔄 Substituir base existente', use_container_width=True):
                        st.session_state.df_historico = df_payments_new
                        st.session_state.df_projecoes = pd.DataFrame()
                        st.success('Base substituída com sucesso!')
                        st.rerun()
                
                with col2:
                    if st.button('➕ Mesclar com base existente', use_container_width=True):
                        st.session_state.df_historico = pd.concat([st.session_state.df_historico, df_payments_new], ignore_index=True)
                        st.session_state.df_historico = st.session_state.df_historico.drop_duplicates(
                            subset=['COD', 'DTEMISSAO', 'CLIENTE', 'VALORLIQUIDO'],
                            keep='last'
                        ).reset_index(drop=True)
                        st.session_state.df_projecoes = pd.DataFrame()
                        st.success('Dados mesclados com sucesso!')
                        st.rerun()

# Footer
st.markdown('---')
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Fluxo de Caixa Projetado - Pro Clean | Desenvolvido com Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
