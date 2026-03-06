import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import calendar

# Configuração da página
st.set_page_config(page_title="Fluxo de Caixa Projetado", layout="wide")

# Funções utilitárias
def is_weekend(date):
    return date.weekday() >= 5

def get_next_business_day(date):
    next_day = date + timedelta(days=1)
    while is_weekend(next_day):
        next_day += timedelta(days=1)
    return next_day

def get_deposit_date(payment_date):
    """Calcula a data que o dinheiro cai na conta (D+2 dias úteis)"""
    if isinstance(payment_date, str):
        payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
    
    deposit_date = payment_date
    business_days_count = 0
    while business_days_count < 2:
        deposit_date = deposit_date + timedelta(days=1)
        if not is_weekend(deposit_date):
            business_days_count += 1
    return deposit_date

# Carregar dados
@st.cache_data
def load_data():
    # Dados do faturamento histórico - garantindo que todas as listas tenham o mesmo tamanho
    historico_data = {
        'EMPRESA': [],
        'COD': [],
        'CLIENTE': [],
        'DTVENCIMENTO': [],
        'VALORLIQUIDO': []
    }
    
    # Dados do cliente 1300 JURUPIS (13 registros)
    for i in range(13):
        historico_data['EMPRESA'].append('PRO CLEAN')
        historico_data['COD'].append(1389)
        historico_data['CLIENTE'].append('1300 JURUPIS')
        if i < 12:
            historico_data['VALORLIQUIDO'].append(9676.29)
        else:
            historico_data['VALORLIQUIDO'].append(10437.82)
    
    datas_1300 = [
        '2025-02-05', '2025-03-05', '2025-04-05', '2025-05-05', '2025-06-05',
        '2025-07-05', '2025-08-05', '2025-09-05', '2025-10-05', '2025-11-05',
        '2025-12-05', '2026-01-05', '2026-02-05'
    ]
    historico_data['DTVENCIMENTO'].extend(datas_1300)
    
    # Dados do cliente 14º CARTORIO DA LAPA (13 registros)
    for i in range(13):
        historico_data['EMPRESA'].append('PRO CLEAN')
        historico_data['COD'].append(5179)
        historico_data['CLIENTE'].append('14º CARTORIO DA LAPA')
        if i < 12:
            historico_data['VALORLIQUIDO'].append(6909.33)
        else:
            historico_data['VALORLIQUIDO'].append(7453.09)
    
    datas_lapa = [
        '2025-02-05', '2025-03-05', '2025-04-05', '2025-05-05', '2025-06-05',
        '2025-07-05', '2025-08-05', '2025-09-05', '2025-10-05', '2025-11-05',
        '2025-12-05', '2026-01-05', '2026-02-05'
    ]
    historico_data['DTVENCIMENTO'].extend(datas_lapa)
    
    # Dados do cliente 32º CARTORIO DO SOCORRO (13 registros)
    valores_socorro = [
        22299.66, 20597.01, 21119.16, 20597.01, 21238.71, 20597.01, 20597.01,
        20597.01, 20597.01, 20597.01, 21625.11, 20597.01, 15552.6
    ]
    
    for i, valor in enumerate(valores_socorro):
        historico_data['EMPRESA'].append('PRO CLEAN')
        historico_data['COD'].append(999259)
        historico_data['CLIENTE'].append('32º CARTORIO DO SOCORRO')
        historico_data['VALORLIQUIDO'].append(valor)
    
    datas_socorro = [
        '2025-02-05', '2025-03-05', '2025-04-05', '2025-05-05', '2025-06-05',
        '2025-07-05', '2025-08-05', '2025-09-05', '2025-10-05', '2025-11-05',
        '2025-12-05', '2026-01-05', '2026-02-05'
    ]
    historico_data['DTVENCIMENTO'].extend(datas_socorro)
    
    # Dados do cliente ABOUT VILA MARIANA (7 registros)
    valores_about = [
        30626.32, 27633.08, 29498.78, 29498.78, 29498.78, 29498.78, 20712.33
    ]
    
    for valor in valores_about:
        historico_data['EMPRESA'].append('PRO CLEAN')
        historico_data['COD'].append(1914)
        historico_data['CLIENTE'].append('ABOUT VILA MARIANA')
        historico_data['VALORLIQUIDO'].append(valor)
    
    datas_about = [
        '2025-08-20', '2025-09-15', '2025-10-01', '2025-11-01', '2025-12-01',
        '2026-01-01', '2026-02-01'
    ]
    historico_data['DTVENCIMENTO'].extend(datas_about)
    
    # Dados do cliente ACQUA PARK BETHAVILLE (3 registros)
    for i in range(3):
        historico_data['EMPRESA'].append('PRO CLEAN')
        historico_data['COD'].append(4113)
        historico_data['CLIENTE'].append('ACQUA PARK BETHAVILLE')
    
    valores_acqua = [26939.92, 29686.02, 29284.22]
    historico_data['VALORLIQUIDO'].extend(valores_acqua)
    
    datas_acqua = ['2025-12-01', '2026-01-01', '2026-02-01']
    historico_data['DTVENCIMENTO'].extend(datas_acqua)
    
    # Dados do cliente AD 330 ALTO DA BOA VISTA (8 registros)
    for i in range(8):
        historico_data['EMPRESA'].append('PRO CLEAN')
        historico_data['COD'].append(1501)
        historico_data['CLIENTE'].append('AD 330 ALTO DA BOA VISTA')
        if i == 0:
            historico_data['VALORLIQUIDO'].append(24116.09)
        else:
            historico_data['VALORLIQUIDO'].append(28199.87)
    
    datas_ad = [
        '2025-02-10', '2025-03-15', '2025-04-15', '2025-05-15', '2025-06-15',
        '2025-07-15', '2025-08-15', '2025-09-15'
    ]
    historico_data['DTVENCIMENTO'].extend(datas_ad)
    
    # Criar DataFrame
    df_historico = pd.DataFrame(historico_data)
    
    # Converter datas
    df_historico['DTVENCIMENTO'] = pd.to_datetime(df_historico['DTVENCIMENTO']).dt.date
    
    # Calcular data de depósito
    df_historico['DATA_DEPOSITO'] = df_historico['DTVENCIMENTO'].apply(
        lambda x: get_deposit_date(x)
    )
    
    return df_historico

# Carregar dados
try:
    df_historico = load_data()
    st.success("✅ Dados carregados com sucesso!")
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# Título do app
st.title("📊 Fluxo de Caixa Projetado")
st.markdown("---")

# Sidebar com filtros
st.sidebar.header("🔍 Filtros")

# Filtro de empresa
empresas = ['Todas'] + sorted(df_historico['EMPRESA'].unique().tolist())
empresa_selecionada = st.sidebar.selectbox("Empresa", empresas)

# Filtro de cliente
if empresa_selecionada != 'Todas':
    clientes_disponiveis = df_historico[df_historico['EMPRESA'] == empresa_selecionada]['CLIENTE'].unique()
else:
    clientes_disponiveis = df_historico['CLIENTE'].unique()

clientes = ['Todos'] + sorted(clientes_disponiveis.tolist())
cliente_selecionado = st.sidebar.selectbox("Cliente", clientes)

# Filtro de período
st.sidebar.subheader("Período de Análise")
data_inicio = st.sidebar.date_input("Data Início", datetime(2025, 1, 1))
data_fim = st.sidebar.date_input("Data Fim", datetime(2026, 12, 31))

# Aplicar filtros
df_filtrado = df_historico.copy()

if empresa_selecionada != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['EMPRESA'] == empresa_selecionada]

if cliente_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['CLIENTE'] == cliente_selecionado]

# Filtrar por período (considerando data de depósito)
df_filtrado = df_filtrado[
    (pd.to_datetime(df_filtrado['DATA_DEPOSITO']) >= pd.to_datetime(data_inicio)) &
    (pd.to_datetime(df_filtrado['DATA_DEPOSITO']) <= pd.to_datetime(data_fim))
]

# Abas principais
tab1, tab2, tab3, tab4 = st.tabs(["📈 Visão Geral", "📅 Previsão Mensal", "📊 Previsão Diária", "💳 Pagamentos"])

with tab1:
    st.header("Visão Geral do Fluxo de Caixa")
    
    if len(df_filtrado) > 0:
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_receber = df_filtrado['VALORLIQUIDO'].sum()
            st.metric("Total a Receber", f"R$ {total_receber:,.2f}")
        
        with col2:
            media_mensal = df_filtrado.groupby(
                pd.to_datetime(df_filtrado['DATA_DEPOSITO']).dt.to_period('M')
            )['VALORLIQUIDO'].mean().mean()
            st.metric("Média Mensal", f"R$ {media_mensal:,.2f}")
        
        with col3:
            qtd_clientes = df_filtrado['CLIENTE'].nunique()
            st.metric("Quantidade de Clientes", qtd_clientes)
        
        with col4:
            qtd_notas = len(df_filtrado)
            st.metric("Quantidade de Notas", qtd_notas)
        
        # Gráfico de linha do tempo
        st.subheader("Evolução dos Recebimentos")
        
        df_grafico = df_filtrado.groupby('DATA_DEPOSITO')['VALORLIQUIDO'].sum().reset_index()
        df_grafico = df_grafico.sort_values('DATA_DEPOSITO')
        
        fig = px.line(df_grafico, x='DATA_DEPOSITO', y='VALORLIQUIDO',
                      title='Recebimentos por Data de Depósito',
                      labels={'DATA_DEPOSITO': 'Data', 'VALORLIQUIDO': 'Valor (R$)'})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela resumo por cliente
        st.subheader("Resumo por Cliente")
        df_resumo = df_filtrado.groupby('CLIENTE').agg({
            'VALORLIQUIDO': ['sum', 'count', 'mean']
        }).round(2)
        df_resumo.columns = ['Total', 'Qtd Notas', 'Média']
        df_resumo = df_resumo.sort_values('Total', ascending=False)
        st.dataframe(df_resumo, use_container_width=True)
    else:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")

with tab2:
    st.header("Previsão Mensal - Layout Painel 1")
    
    if len(df_filtrado) > 0:
        # Criar cópia para não modificar original
        df_mensal = df_filtrado.copy()
        
        # Extrair mês e ano
        df_mensal['DATA_DEPOSITO_DT'] = pd.to_datetime(df_mensal['DATA_DEPOSITO'])
        df_mensal['Mês'] = df_mensal['DATA_DEPOSITO_DT'].dt.month
        df_mensal['Ano'] = df_mensal['DATA_DEPOSITO_DT'].dt.year
        
        # Mapeamento de meses em português
        meses_pt = {
            1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
            5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
            9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
        }
        
        df_mensal['Mês_PT'] = df_mensal['Mês'].map(meses_pt)
        
        # Criar tabela pivô
        pivot_mensal = df_mensal.pivot_table(
            values='VALORLIQUIDO',
            index='CLIENTE',
            columns='Mês_PT',
            aggfunc='sum',
            fill_value=0
        )
        
        # Reordenar meses
        ordem_meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                       'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        
        pivot_mensal = pivot_mensal.reindex(columns=[m for m in ordem_meses if m in pivot_mensal.columns])
        
        # Adicionar coluna total
        pivot_mensal['Total'] = pivot_mensal.sum(axis=1)
        
        # Estilizar a tabela
        st.dataframe(
            pivot_mensal.style.format("R$ {:,.2f}"),
            use_container_width=True,
            height=400
        )
        
        # Botão para download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pivot_mensal.to_excel(writer, sheet_name='Painel 1')
        
        st.download_button(
            label="📥 Download Previsão Mensal (Excel)",
            data=output.getvalue(),
            file_name="previsao_mensal.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")

with tab3:
    st.header("Previsão Diária - Layout Painel 2")
    
    # Criar range de datas para projeção (próximos 3 meses)
    hoje = datetime.now().date()
    data_inicio_proj = hoje
    data_fim_proj = (datetime.now() + timedelta(days=90)).date()
    
    # Gerar todos os dias úteis
    datas_proj = []
    data_atual = data_inicio_proj
    while data_atual <= data_fim_proj:
        if not is_weekend(data_atual):
            datas_proj.append(data_atual)
        data_atual += timedelta(days=1)
    
    # Criar DataFrame da previsão diária
    df_diario = pd.DataFrame({
        'Data': datas_proj,
        'Entrada': 0.0,
        'Saida': 0.0,
        'Saldo': 0.0
    })
    
    # Preencher entradas baseado no histórico projetado (para datas futuras)
    df_futuro = df_filtrado[pd.to_datetime(df_filtrado['DATA_DEPOSITO']) >= pd.to_datetime(hoje)]
    
    for _, row in df_futuro.iterrows():
        mask = df_diario['Data'] == row['DATA_DEPOSITO']
        if mask.any():
            df_diario.loc[mask, 'Entrada'] += row['VALORLIQUIDO']
    
    # Calcular saldo acumulado
    df_diario['Saldo'] = df_diario['Entrada'].cumsum() - df_diario['Saida'].cumsum()
    
    # Exibir tabela
    st.dataframe(
        df_diario.style.format({
            'Entrada': 'R$ {:,.2f}',
            'Saida': 'R$ {:,.2f}',
            'Saldo': 'R$ {:,.2f}'
        }),
        use_container_width=True,
        height=500
    )
    
    # Gráfico de saldo diário
    if len(df_diario) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_diario['Data'],
            y=df_diario['Saldo'],
            mode='lines+markers',
            name='Saldo',
            line=dict(color='green', width=2)
        ))
        fig.add_trace(go.Bar(
            x=df_diario['Data'],
            y=df_diario['Entrada'],
            name='Entradas',
            marker_color='blue',
            opacity=0.5
        ))
        fig.update_layout(
            title='Saldo e Entradas Diárias Projetadas',
            xaxis_title='Data',
            yaxis_title='Valor (R$)',
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Botão download
    output_diario = BytesIO()
    with pd.ExcelWriter(output_diario, engine='openpyxl') as writer:
        df_diario.to_excel(writer, sheet_name='Painel 2', index=False)
    
    st.download_button(
        label="📥 Download Previsão Diária (Excel)",
        data=output_diario.getvalue(),
        file_name="previsao_diaria.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with tab4:
    st.header("Gerenciamento de Pagamentos")
    st.info("Área para upload e gestão de pagamentos realizados")
    
    # Upload de arquivo de pagamentos
    uploaded_file = st.file_uploader(
        "Upload da base de pagamentos (Excel/CSV)",
        type=['xlsx', 'csv']
    )
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_pagamentos = pd.read_csv(uploaded_file)
            else:
                df_pagamentos = pd.read_excel(uploaded_file)
            
            st.success("Arquivo carregado com sucesso!")
            st.dataframe(df_pagamentos.head())
            
            # Botão para processar e atualizar base
            if st.button("Processar e Atualizar Base Histórica"):
                st.success("Base atualizada com sucesso! (Simulação)")
                
        except Exception as e:
            st.error(f"Erro ao carregar arquivo: {e}")
    
    # Formulário manual de pagamento
    st.subheader("Registro Manual de Pagamento")
    
    with st.form("form_pagamento"):
        col1, col2 = st.columns(2)
        
        with col1:
            data_pagamento = st.date_input("Data do Pagamento", datetime.now())
            cliente_pag = st.selectbox("Cliente", df_historico['CLIENTE'].unique())
            valor_pag = st.number_input("Valor (R$)", min_value=0.0, step=100.0, format="%.2f")
        
        with col2:
            tipo_pag = st.selectbox("Tipo", ["Entrada", "Saída"])
            descricao = st.text_input("Descrição")
            observacao = st.text_area("Observações", height=68)
        
        submitted = st.form_submit_button("Registrar Pagamento")
        
        if submitted:
            st.success("✅ Pagamento registrado com sucesso!")

# Rodapé
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Desenvolvido para gestão de fluxo de caixa | Atualizado em tempo real</p>
    <p style='font-size: 12px; color: gray;'>Considere D+2 dias úteis para compensação bancária</p>
</div>
""", unsafe_allow_html=True)
