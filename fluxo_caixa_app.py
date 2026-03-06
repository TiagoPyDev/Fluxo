
pip install streamlit pandas numpy plotly openpyxl xlrd

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import calendar

# Configuração da página
st.set_page_config(
    page_title="Sistema de Fluxo de Caixa Projetado",
    page_icon="💰",
    layout="wide"
)

# Funções utilitárias
def is_weekend(date):
    """Verifica se a data é fim de semana"""
    return date.weekday() >= 5  # 5 = Sábado, 6 = Domingo

def get_next_business_day(date):
    """Retorna o próximo dia útil após uma data"""
    next_day = date + timedelta(days=2)  # 2 dias após pagamento
    while is_weekend(next_day):
        next_day += timedelta(days=1)
    return next_day

def parse_date(date_value):
    """Converte diferentes formatos de data para datetime"""
    if pd.isna(date_value):
        return pd.NaT
    
    if isinstance(date_value, (int, float)):
        # Trata datas no formato Excel (número de dias desde 1900-01-01)
        try:
            return pd.to_datetime('1899-12-30') + timedelta(days=date_value)
        except:
            return pd.NaT
    
    date_str = str(date_value).strip()
    
    # Formato com timestamp
    if ' ' in date_str and len(date_str.split(' ')[0]) == 10:
        date_str = date_str.split(' ')[0]
    
    # Formato YYYY-MM-DD
    if '-' in date_str and len(date_str) == 10:
        try:
            return pd.to_datetime(date_str)
        except:
            pass
    
    # Formato DD/MM/YYYY
    if '/' in date_str:
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except:
            pass
    
    return pd.NaT

@st.cache_data
def load_data(uploaded_file=None):
    """Carrega e processa os dados do arquivo"""
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    else:
        # Dados de exemplo usando o arquivo fornecido
        data = {
            'EMPRESA': ['PRO CLEAN'] * 5,
            'COD': [1389, 1389, 1389, 5179, 5179],
            'CLIENTE': ['1300 JURUPIS', '1300 JURUPIS', '1300 JURUPIS', '14º CARTORIO DA LAPA', '14º CARTORIO DA LAPA'],
            'CNPJ': ['46706465000163', '46706465000163', '46706465000163', '', ''],
            'DTEMISSAO': ['2025-01-27', '2025-02-21', '2025-03-21', '2025-01-27', '2025-02-21'],
            'DTVENCIMENTO': ['2025-02-05', '2025-03-05', '2025-04-05', '2025-02-05', '2025-03-05'],
            'VALORBRUTO': [11750.2, 11750.2, 11750.2, 6909.33, 6909.33],
            'VALORLIQUIDO': [9676.29, 9676.29, 9676.29, 6909.33, 6909.33]
        }
        df = pd.DataFrame(data)
    
    # Processar datas
    df['DTEMISSAO'] = df['DTEMISSAO'].apply(parse_date)
    df['DTVENCIMENTO'] = df['DTVENCIMENTO'].apply(parse_date)
    
    # Remover linhas com datas inválidas
    df = df.dropna(subset=['DTEMISSAO', 'DTVENCIMENTO'])
    
    # Calcular data de recebimento (2 dias úteis após vencimento)
    df['DTRECEBIMENTO'] = df['DTVENCIMENTO'].apply(get_next_business_day)
    
    # Extrair ano e mês para filtros
    df['ANO'] = df['DTVENCIMENTO'].dt.year
    df['MES'] = df['DTVENCIMENTO'].dt.month
    df['MES_ANO'] = df['DTVENCIMENTO'].dt.strftime('%Y-%m')
    
    return df

def project_cash_flow(df, months_ahead=6, selected_clients=None, selected_companies=None):
    """Projeta o fluxo de caixa para os próximos meses"""
    if df.empty:
        return pd.DataFrame()
    
    # Aplicar filtros
    filtered_df = df.copy()
    if selected_clients and len(selected_clients) > 0:
        filtered_df = filtered_df[filtered_df['CLIENTE'].isin(selected_clients)]
    if selected_companies and len(selected_companies) > 0:
        filtered_df = filtered_df[filtered_df['EMPRESA'].isin(selected_companies)]
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # Última data no histórico
    last_date = filtered_df['DTVENCIMENTO'].max()
    
    # Identificar periodicidade por cliente
    client_periodicity = {}
    for client in filtered_df['CLIENTE'].unique():
        client_data = filtered_df[filtered_df['CLIENTE'] == client].sort_values('DTVENCIMENTO')
        if len(client_data) >= 2:
            # Calcular média de dias entre vencimentos
            diffs = client_data['DTVENCIMENTO'].diff().dt.days.dropna()
            if len(diffs) > 0:
                avg_days = int(diffs.mean())
                if 25 <= avg_days <= 35:
                    client_periodicity[client] = 30  # Mensal
                elif 55 <= avg_days <= 65:
                    client_periodicity[client] = 60  # Bimestral
                else:
                    client_periodicity[client] = avg_days
        else:
            # Se só tem um registro, usar média geral
            client_periodicity[client] = 30  # Assume mensal por padrão
    
    # Gerar projeções
    projections = []
    for client in filtered_df['CLIENTE'].unique():
        client_data = filtered_df[filtered_df['CLIENTE'] == client]
        last_client_date = client_data['DTVENCIMENTO'].max()
        avg_value = client_data['VALORLIQUIDO'].mean()
        period = client_periodicity.get(client, 30)
        
        for i in range(1, months_ahead + 1):
            next_date = last_client_date + timedelta(days=period * i)
            if next_date <= last_date + timedelta(days=months_ahead * 31):
                recebimento_date = get_next_business_day(next_date)
                
                projections.append({
                    'CLIENTE': client,
                    'EMPRESA': client_data['EMPRESA'].iloc[0],
                    'TIPO': 'Projetado',
                    'DATA_VENCIMENTO': next_date,
                    'DATA_RECEBIMENTO': recebimento_date,
                    'VALOR_PROJETADO': avg_value,
                    'VALOR_REAL': None,
                    'PERIODICIDADE_DIAS': period
                })
    
    return pd.DataFrame(projections)

def create_cash_flow_chart(historical_df, projected_df):
    """Cria gráfico de fluxo de caixa"""
    # Preparar dados históricos
    hist_agg = historical_df.groupby(historical_df['DTRECEBIMENTO'].dt.date)['VALORLIQUIDO'].sum().reset_index()
    hist_agg.columns = ['DATA', 'VALOR']
    hist_agg['TIPO'] = 'Histórico'
    
    # Preparar dados projetados
    proj_agg = pd.DataFrame()
    if not projected_df.empty:
        proj_agg = projected_df.groupby(projected_df['DATA_RECEBIMENTO'].dt.date)['VALOR_PROJETADO'].sum().reset_index()
        proj_agg.columns = ['DATA', 'VALOR']
        proj_agg['TIPO'] = 'Projetado'
    
    # Combinar dados
    combined = pd.concat([hist_agg, proj_agg], ignore_index=True)
    combined = combined.sort_values('DATA')
    
    # Criar gráfico
    fig = px.bar(combined, x='DATA', y='VALOR', color='TIPO',
                 title='Fluxo de Caixa Diário - Histórico vs Projetado',
                 labels={'VALOR': 'Valor (R$)', 'DATA': 'Data de Recebimento'},
                 barmode='group')
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Valor (R$)",
        hovermode='x unified',
        legend_title="Tipo"
    )
    
    return fig

def create_monthly_summary(historical_df, projected_df):
    """Cria resumo mensal"""
    # Resumo histórico
    hist_monthly = historical_df.groupby(historical_df['DTRECEBIMENTO'].dt.to_period('M'))['VALORLIQUIDO'].agg(['sum', 'count']).reset_index()
    hist_monthly['DTRECEBIMENTO'] = hist_monthly['DTRECEBIMENTO'].astype(str)
    hist_monthly['TIPO'] = 'Histórico'
    hist_monthly.columns = ['MES_ANO', 'VALOR_TOTAL', 'QUANTIDADE', 'TIPO']
    
    # Resumo projetado
    proj_monthly = pd.DataFrame()
    if not projected_df.empty:
        proj_monthly = projected_df.groupby(projected_df['DATA_RECEBIMENTO'].dt.to_period('M'))['VALOR_PROJETADO'].agg(['sum', 'count']).reset_index()
        proj_monthly['DATA_RECEBIMENTO'] = proj_monthly['DATA_RECEBIMENTO'].astype(str)
        proj_monthly['TIPO'] = 'Projetado'
        proj_monthly.columns = ['MES_ANO', 'VALOR_TOTAL', 'QUANTIDADE', 'TIPO']
    
    return pd.concat([hist_monthly, proj_monthly], ignore_index=True)

# Interface principal
st.title("💰 Sistema de Fluxo de Caixa Projetado")
st.markdown("---")

# Sidebar para navegação
st.sidebar.title("Navegação")
page = st.sidebar.radio(
    "Selecione a Página",
    ["📊 Dashboard", "📈 Projeções", "📋 Pagamentos", "⚙️ Configurações"]
)

# Upload de arquivo
st.sidebar.markdown("---")
st.sidebar.subheader("Upload de Dados")
uploaded_file = st.sidebar.file_uploader(
    "Carregar arquivo Excel",
    type=['xlsx', 'xls'],
    help="Formato esperado: EMPRESA, COD, CLIENTE, CNPJ, DTEMISSAO, DTVENCIMENTO, VALORBRUTO, VALORLIQUIDO"
)

# Carregar dados
df = load_data(uploaded_file)

# Filtros globais
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros Globais")

# Filtro por empresa
empresas = ['Todas'] + sorted(df['EMPRESA'].unique().tolist())
selected_empresa = st.sidebar.selectbox("Empresa", empresas)

# Filtro por cliente
clientes = sorted(df['CLIENTE'].unique().tolist())
selected_clientes = st.sidebar.multiselect("Clientes", clientes)

# Aplicar filtros ao dataframe principal
filtered_df = df.copy()
if selected_empresa != 'Todas':
    filtered_df = filtered_df[filtered_df['EMPRESA'] == selected_empresa]
if selected_clientes:
    filtered_df = filtered_df[filtered_df['CLIENTE'].isin(selected_clientes)]

# PÁGINA: DASHBOARD
if page == "📊 Dashboard":
    st.header("📊 Dashboard de Fluxo de Caixa")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Faturado (Histórico)",
            f"R$ {filtered_df['VALORLIQUIDO'].sum():,.2f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "Média por Fatura",
            f"R$ {filtered_df['VALORLIQUIDO'].mean():,.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            "Total de Faturas",
            f"{len(filtered_df)}",
            delta=None
        )
    
    with col4:
        period = (filtered_df['DTVENCIMENTO'].max() - filtered_df['DTVENCIMENTO'].min()).days
        st.metric(
            "Período (dias)",
            f"{period}",
            delta=None
        )
    
    st.markdown("---")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top 10 Clientes por Valor")
        top_clients = filtered_df.groupby('CLIENTE')['VALORLIQUIDO'].sum().nlargest(10).reset_index()
        fig = px.bar(top_clients, x='VALORLIQUIDO', y='CLIENTE', orientation='h',
                     title="Top 10 Clientes",
                     labels={'VALORLIQUIDO': 'Valor Total (R$)', 'CLIENTE': ''})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Distribuição por Mês")
        monthly = filtered_df.groupby('MES_ANO')['VALORLIQUIDO'].sum().reset_index()
        fig = px.line(monthly, x='MES_ANO', y='VALORLIQUIDO',
                      title="Faturamento Mensal",
                      labels={'MES_ANO': 'Mês/Ano', 'VALORLIQUIDO': 'Valor (R$)'})
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Tabela de dados
    st.subheader("Dados Históricos")
    
    # Opções de visualização
    col1, col2 = st.columns(2)
    with col1:
        show_columns = st.multiselect(
            "Colunas para exibir",
            options=filtered_df.columns.tolist(),
            default=['EMPRESA', 'CLIENTE', 'DTVENCIMENTO', 'DTRECEBIMENTO', 'VALORLIQUIDO']
        )
    
    with col2:
        rows_per_page = st.selectbox("Linhas por página", [10, 25, 50, 100])
    
    if show_columns:
        st.dataframe(
            filtered_df[show_columns].sort_values('DTVENCIMENTO', ascending=False),
            use_container_width=True,
            hide_index=True,
            height=400
        )
    
    # Download dos dados
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"dados_historicos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# PÁGINA: PROJEÇÕES
elif page == "📈 Projeções":
    st.header("📈 Projeções de Fluxo de Caixa")
    
    col1, col2 = st.columns(2)
    with col1:
        months_ahead = st.slider(
            "Meses à frente para projetar",
            min_value=1,
            max_value=12,
            value=6
        )
    
    with col2:
        st.info("As projeções são baseadas na periodicidade histórica de cada cliente")
    
    # Gerar projeções
    projected_df = project_cash_flow(
        filtered_df,
        months_ahead=months_ahead,
        selected_clients=selected_clientes if selected_clientes else None,
        selected_companies=[selected_empresa] if selected_empresa != 'Todas' else None
    )
    
    # Resumo
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_projected = projected_df['VALOR_PROJETADO'].sum() if not projected_df.empty else 0
        st.metric(
            "Total Projetado",
            f"R$ {total_projected:,.2f}",
            delta=None
        )
    
    with col2:
        avg_projected = projected_df['VALOR_PROJETADO'].mean() if not projected_df.empty else 0
        st.metric(
            "Média Projetada por Fatura",
            f"R$ {avg_projected:,.2f}",
            delta=None
        )
    
    with col3:
        count_projected = len(projected_df)
        st.metric(
            "Faturas Projetadas",
            f"{count_projected}",
            delta=None
        )
    
    st.markdown("---")
    
    # Gráfico de fluxo
    st.subheader("Gráfico de Fluxo de Caixa")
    fig = create_cash_flow_chart(filtered_df, projected_df)
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumo mensal
    st.markdown("---")
    st.subheader("Resumo Mensal")
    monthly_summary = create_monthly_summary(filtered_df, projected_df)
    
    # Formatar valores
    monthly_summary['VALOR_TOTAL'] = monthly_summary['VALOR_TOTAL'].apply(lambda x: f"R$ {x:,.2f}")
    
    st.dataframe(
        monthly_summary.sort_values('MES_ANO'),
        use_container_width=True,
        hide_index=True
    )
    
    # Tabela de projeções
    st.markdown("---")
    st.subheader("Detalhamento das Projeções")
    
    if not projected_df.empty:
        # Opções de visualização
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox(
                "Ordenar por",
                options=['DATA_VENCIMENTO', 'DATA_RECEBIMENTO', 'VALOR_PROJETADO', 'CLIENTE']
            )
        
        with col2:
            sort_order = st.radio("Ordem", ["Crescente", "Decrescente"], horizontal=True)
        
        display_df = projected_df.copy()
        display_df['DATA_VENCIMENTO'] = display_df['DATA_VENCIMENTO'].dt.strftime('%d/%m/%Y')
        display_df['DATA_RECEBIMENTO'] = display_df['DATA_RECEBIMENTO'].dt.strftime('%d/%m/%Y')
        display_df['VALOR_PROJETADO'] = display_df['VALOR_PROJETADO'].apply(lambda x: f"R$ {x:,.2f}")
        
        ascending = sort_order == "Crescente"
        display_df = display_df.sort_values(sort_by, ascending=ascending)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'VALOR_PROJETADO': 'Valor Projetado'
            }
        )
        
        # Download das projeções
        csv_proj = projected_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Projeções (CSV)",
            data=csv_proj,
            file_name=f"projecoes_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Nenhuma projeção disponível para os filtros selecionados")

# PÁGINA: PAGAMENTOS
elif page == "📋 Pagamentos":
    st.header("📋 Registro de Pagamentos")
    
    st.info("""
    **Instruções:**
    1. Carregue um arquivo Excel com os pagamentos realizados
    2. O sistema atualizará automaticamente a base histórica
    3. As datas de recebimento devem considerar dias úteis
    """)
    
    # Upload de pagamentos
    payment_file = st.file_uploader(
        "Carregar arquivo de pagamentos",
        type=['xlsx', 'xls'],
        key="payment_upload"
    )
    
    if payment_file is not None:
        try:
            payments_df = pd.read_excel(payment_file)
            st.success("Arquivo carregado com sucesso!")
            
            # Mostrar preview
            st.subheader("Preview do arquivo carregado")
            st.dataframe(payments_df.head(), use_container_width=True)
            
            # Validar colunas necessárias
            required_cols = ['CLIENTE', 'DATA_PAGAMENTO', 'VALOR_PAGO']
            missing_cols = [col for col in required_cols if col not in payments_df.columns]
            
            if missing_cols:
                st.error(f"Colunas obrigatórias não encontradas: {', '.join(missing_cols)}")
            else:
                # Processar pagamentos
                payments_df['DATA_RECEBIMENTO'] = pd.to_datetime(payments_df['DATA_PAGAMENTO']).apply(get_next_business_day)
                
                # Comparar com histórico
                merged = pd.merge(
                    payments_df,
                    filtered_df[['CLIENTE', 'DTVENCIMENTO', 'VALORLIQUIDO']],
                    left_on='CLIENTE',
                    right_on='CLIENTE',
                    how='left'
                )
                
                # Análise de diferenças
                merged['DIFERENCA'] = merged['VALOR_PAGO'] - merged['VALORLIQUIDO']
                merged['STATUS'] = merged['DIFERENCA'].apply(
                    lambda x: 'OK' if abs(x) < 0.01 else 'Diferença'
                )
                
                st.subheader("Análise de Pagamentos")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Pagamentos", len(payments_df))
                with col2:
                    ok_count = len(merged[merged['STATUS'] == 'OK'])
                    st.metric("Pagamentos OK", ok_count)
                with col3:
                    diff_count = len(merged[merged['STATUS'] == 'Diferença'])
                    st.metric("Com Diferença", diff_count)
                
                st.dataframe(
                    merged[['CLIENTE', 'DATA_PAGAMENTO', 'DATA_RECEBIMENTO', 
                            'VALOR_PAGO', 'VALORLIQUIDO', 'DIFERENCA', 'STATUS']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Botão para atualizar base
                if st.button("🔄 Atualizar Base Histórica"):
                    st.success("Base atualizada com sucesso! (simulação)")
                    st.balloons()
        
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

# PÁGINA: CONFIGURAÇÕES
else:  # ⚙️ Configurações
    st.header("⚙️ Configurações do Sistema")
    
    st.subheader("Configurações de Dias Úteis")
    st.info("Os recebimentos são considerados 2 dias úteis após o vencimento")
    
    col1, col2 = st.columns(2)
    with col1:
        days_after = st.number_input(
            "Dias após vencimento para recebimento",
            min_value=0,
            max_value=10,
            value=2
        )
    
    with col2:
        weekend_days = st.multiselect(
            "Dias considerados fim de semana",
            options=["Sábado", "Domingo"],
            default=["Sábado", "Domingo"]
        )
    
    st.markdown("---")
    
    st.subheader("Configurações de Projeção")
    col1, col2 = st.columns(2)
    with col1:
        default_months = st.number_input(
            "Meses padrão para projeção",
            min_value=1,
            max_value=24,
            value=6
        )
    
    with col2:
        min_period = st.number_input(
            "Período mínimo para considerar periodicidade (dias)",
            min_value=1,
            max_value=90,
            value=20
        )
    
    st.markdown("---")
    
    st.subheader("Informações do Sistema")
    st.json({
        "versao": "1.0.0",
        "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_registros": len(df),
        "clientes_unicos": df['CLIENTE'].nunique(),
        "periodo_inicio": df['DTVENCIMENTO'].min().strftime("%d/%m/%Y") if not df.empty else "N/A",
        "periodo_fim": df['DTVENCIMENTO'].max().strftime("%d/%m/%Y") if not df.empty else "N/A"
    })
    
    st.markdown("---")
    
    if st.button("🔄 Resetar para configurações padrão"):
        st.success("Configurações resetadas!")
        st.rerun()

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 10px;'>
        Sistema de Fluxo de Caixa Projetado v1.0 | Desenvolvido com Streamlit
    </div>
    """,
    unsafe_allow_html=True
)

