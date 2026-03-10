import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
import io
import re

# Configuração da página - DEVE SER O PRIMEIRO COMANDO STREAMLIT
st.set_page_config(
    page_title="Fluxo de Caixa - Dashboard",
    page_icon="💰",
    layout="wide"
)

# Título principal
st.title("💰 Dashboard de Fluxo de Caixa")
st.markdown("---")

# Saldo inicial
SALDO_INICIAL = 6355160.80  # R$ 6.355.160,80

# Função para limpar e converter valores monetários
def clean_currency(value):
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remover espaços, R$, pontos e converter vírgula para ponto
        value = re.sub(r'[R$\s]', '', value)
        value = value.replace('.', '').replace(',', '.')
        try:
            return float(value)
        except:
            return 0
    return 0

# Função para verificar se é dia útil (considerando feriados nacionais brasileiros)
def is_business_day(date):
    # Verificar se é fim de semana
    if date.weekday() >= 5:  # Sábado (5) ou Domingo (6)
        return False
    
    # Lista de feriados nacionais brasileiros (principais)
    year = date.year
    holidays = [
        # Feriados fixos
        datetime(year, 1, 1).date(),   # Confraternização Universal
        datetime(year, 4, 21).date(),  # Tiradentes
        datetime(year, 5, 1).date(),   # Dia do Trabalho
        datetime(year, 9, 7).date(),   # Independência
        datetime(year, 10, 12).date(), # Nossa Srª Aparecida
        datetime(year, 11, 2).date(),  # Finados
        datetime(year, 11, 15).date(), # Proclamação da República
        datetime(year, 12, 25).date(), # Natal
        
        # Feriados móveis (aproximados)
    ]
    
    # Adicionar Carnaval e Sexta Santa (aproximados - anos específicos)
    if year == 2025:
        holidays.extend([
            datetime(2025, 3, 4).date(),  # Carnaval
            datetime(2025, 3, 5).date(),  # Carnaval
            datetime(2025, 4, 18).date(), # Sexta Santa
        ])
    elif year == 2026:
        holidays.extend([
            datetime(2026, 2, 17).date(), # Carnaval
            datetime(2026, 2, 18).date(), # Carnaval
            datetime(2026, 4, 3).date(),  # Sexta Santa
        ])
    
    return date.date() not in holidays

# Função para carregar dados - CORRIGIDA COMPLETAMENTE
@st.cache_data
def load_data(uploaded_file):
    try:
        if uploaded_file is not None:
            # Tentar ler as abas com diferentes nomes possíveis
            try:
                df_entradas = pd.read_excel(uploaded_file, sheet_name='Entradas')
                st.success("✅ Aba 'Entradas' carregada com sucesso!")
            except:
                try:
                    df_entradas = pd.read_excel(uploaded_file, sheet_name='entradas')
                    st.success("✅ Aba 'entradas' carregada com sucesso!")
                except:
                    st.error("❌ Não foi possível encontrar a aba 'Entradas' no arquivo")
                    return None, None
            
            try:
                df_saidas = pd.read_excel(uploaded_file, sheet_name='Saídas')
                st.success("✅ Aba 'Saídas' carregada com sucesso!")
            except:
                try:
                    df_saidas = pd.read_excel(uploaded_file, sheet_name='saidas')
                    st.success("✅ Aba 'saidas' carregada com sucesso!")
                except:
                    st.error("❌ Não foi possível encontrar a aba 'Saídas' no arquivo")
                    return None, None
            
            # Identificar as colunas corretas
            def find_column(df, possible_names):
                df_cols_lower = {col.lower().strip(): col for col in df.columns}
                for name in possible_names:
                    if name.lower().strip() in df_cols_lower:
                        return df_cols_lower[name.lower().strip()]
                return None
            
            # Para Entradas
            empresa_col_ent = find_column(df_entradas, ['Empresa', 'EMPRESA', 'empresa'])
            valor_col_ent = find_column(df_entradas, ['Vl.rateado', 'VL.RATEADO', 'vl.rateado', 'Valor', 'VALOR', 'valor'])
            data_col_ent = find_column(df_entradas, ['Dt.pagto', 'DT.PAGTO', 'dt.pagto', 'Data', 'DATA', 'data'])
            
            # Para Saídas
            empresa_col_sai = find_column(df_saidas, ['Empresa', 'EMPRESA', 'empresa'])
            valor_col_sai = find_column(df_saidas, ['Vl.rateado', 'VL.RATEADO', 'vl.rateado', 'Valor', 'VALOR', 'valor'])
            data_col_sai = find_column(df_saidas, ['Dt.pagto', 'DT.PAGTO', 'dt.pagto', 'Data', 'DATA', 'data'])
            
            # Verificar se encontrou todas as colunas
            if None in [empresa_col_ent, valor_col_ent, data_col_ent]:
                st.error("❌ Colunas necessárias não encontradas na aba Entradas")
                st.write("Colunas encontradas:", list(df_entradas.columns))
                return None, None
            
            if None in [empresa_col_sai, valor_col_sai, data_col_sai]:
                st.error("❌ Colunas necessárias não encontradas na aba Saídas")
                st.write("Colunas encontradas:", list(df_saidas.columns))
                return None, None
            
            # Renomear colunas para nomes padronizados
            df_entradas = df_entradas.rename(columns={
                empresa_col_ent: 'Empresa',
                valor_col_ent: 'Vl.rateado',
                data_col_ent: 'Dt.pagto'
            })
            
            df_saidas = df_saidas.rename(columns={
                empresa_col_sai: 'Empresa',
                valor_col_sai: 'Vl.rateado',
                data_col_sai: 'Dt.pagto'
            })
            
            # Processar valores
            df_entradas['Vl.rateado'] = df_entradas['Vl.rateado'].apply(clean_currency)
            df_saidas['Vl.rateado'] = df_saidas['Vl.rateado'].apply(clean_currency)
            
            # Processar datas
            df_entradas['Dt.pagto'] = pd.to_datetime(df_entradas['Dt.pagto'], errors='coerce')
            df_saidas['Dt.pagto'] = pd.to_datetime(df_saidas['Dt.pagto'], errors='coerce')
            
            # Remover valores nulos
            df_entradas = df_entradas.dropna(subset=['Dt.pagto', 'Vl.rateado'])
            df_saidas = df_saidas.dropna(subset=['Dt.pagto', 'Vl.rateado'])
            
            # Filtrar valores zero ou muito pequenos
            df_entradas = df_entradas[abs(df_entradas['Vl.rateado']) > 0.01]
            df_saidas = df_saidas[abs(df_saidas['Vl.rateado']) > 0.01]
            
            st.success(f"✅ Dados carregados: {len(df_entradas)} entradas e {len(df_saidas)} saídas")
            
            return df_entradas, df_saidas
            
        else:
            # Dados de exemplo para teste
            st.info("📢 Nenhum arquivo carregado. Mostrando dados de exemplo...")
            
            # Criar dados de exemplo
            dates = pd.date_range(start='2025-01-01', end='2025-06-30', freq='D')
            
            # Entradas de exemplo
            entradas_data = {
                'Empresa': ['Empresa A', 'Empresa B', 'Empresa C', 'Empresa D', 'Empresa E'] * 40,
                'Vl.rateado': np.random.uniform(1000, 50000, 200),
                'Dt.pagto': np.random.choice(dates, 200)
            }
            df_entradas = pd.DataFrame(entradas_data)
            
            # Saídas de exemplo
            saidas_data = {
                'Empresa': ['Fornecedor X', 'Fornecedor Y', 'Fornecedor Z', 'Serviços', 'Impostos'] * 40,
                'Vl.rateado': np.random.uniform(500, 30000, 200),
                'Dt.pagto': np.random.choice(dates, 200)
            }
            df_saidas = pd.DataFrame(saidas_data)
            
            st.success(f"✅ Dados de exemplo gerados: {len(df_entradas)} entradas e {len(df_saidas)} saídas")
            
            return df_entradas, df_saidas
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar arquivo: {str(e)}")
        return None, None

# Sidebar para upload e controles
with st.sidebar:
    st.header("📁 Upload de Dados")
    uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])
    
    st.header("⚙️ Configurações")
    projection_months = st.slider("Meses para projetar (mensal)", 1, 6, 3)
    projection_days = st.slider("Dias para projetar (calendário)", 30, 180, 60)

# Carregar dados
df_entradas, df_saidas = load_data(uploaded_file)

# Main content - SOMENTE EXECUTA SE OS DADOS EXISTIREM
if df_entradas is not None and df_saidas is not None and len(df_entradas) > 0 and len(df_saidas) > 0:
    
    # Filtros do sidebar
    with st.sidebar:
        st.header("📊 Filtros")
        
        # Filtro de período
        min_date = min(df_entradas['Dt.pagto'].min(), df_saidas['Dt.pagto'].min()).date()
        max_date = max(df_entradas['Dt.pagto'].max(), df_saidas['Dt.pagto'].max()).date()
        
        date_range = st.date_input(
            "Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Filtro de empresas
        empresas_entradas = set(df_entradas['Empresa'].unique())
        empresas_saidas = set(df_saidas['Empresa'].unique())
        todas_empresas = sorted(list(empresas_entradas.union(empresas_saidas)))
        
        empresas_selecionadas = st.multiselect(
            "Empresas",
            options=todas_empresas,
            default=[]
        )
        
        # Mostrar estatísticas básicas
        with st.expander("📊 Estatísticas"):
            st.write(f"Total de entradas: {len(df_entradas)}")
            st.write(f"Total de saídas: {len(df_saidas)}")
            st.write(f"Período: {df_entradas['Dt.pagto'].min().date()} a {df_entradas['Dt.pagto'].max().date()}")
    
    # Aplicar filtros
    df_entradas_filtered = df_entradas.copy()
    df_saidas_filtered = df_saidas.copy()
    
    if len(date_range) == 2:
        mask_entradas = (df_entradas_filtered['Dt.pagto'].dt.date >= date_range[0]) & \
                        (df_entradas_filtered['Dt.pagto'].dt.date <= date_range[1])
        mask_saidas = (df_saidas_filtered['Dt.pagto'].dt.date >= date_range[0]) & \
                      (df_saidas_filtered['Dt.pagto'].dt.date <= date_range[1])
        df_entradas_filtered = df_entradas_filtered[mask_entradas]
        df_saidas_filtered = df_saidas_filtered[mask_saidas]
    
    if empresas_selecionadas:
        df_entradas_filtered = df_entradas_filtered[df_entradas_filtered['Empresa'].isin(empresas_selecionadas)]
        df_saidas_filtered = df_saidas_filtered[df_saidas_filtered['Empresa'].isin(empresas_selecionadas)]
    
    # Verificar se ainda há dados após filtros
    if len(df_entradas_filtered) == 0 or len(df_saidas_filtered) == 0:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        st.stop()
    
    # Calcular totais
    total_entradas = df_entradas_filtered['Vl.rateado'].sum()
    total_saidas = df_saidas_filtered['Vl.rateado'].sum()
    saldo_atual = SALDO_INICIAL + total_entradas - abs(total_saidas)
    
    # Criar fluxo de caixa mensal
    df_entradas_filtered['Ano'] = df_entradas_filtered['Dt.pagto'].dt.year
    df_entradas_filtered['Mes'] = df_entradas_filtered['Dt.pagto'].dt.month
    df_entradas_filtered['Mês/Ano'] = df_entradas_filtered['Ano'].astype(str) + '-' + df_entradas_filtered['Mes'].astype(str).str.zfill(2)
    
    df_saidas_filtered['Ano'] = df_saidas_filtered['Dt.pagto'].dt.year
    df_saidas_filtered['Mes'] = df_saidas_filtered['Dt.pagto'].dt.month
    df_saidas_filtered['Mês/Ano'] = df_saidas_filtered['Ano'].astype(str) + '-' + df_saidas_filtered['Mes'].astype(str).str.zfill(2)
    
    entradas_mensal = df_entradas_filtered.groupby(['Ano', 'Mes', 'Mês/Ano'])['Vl.rateado'].sum().reset_index()
    saidas_mensal = df_saidas_filtered.groupby(['Ano', 'Mes', 'Mês/Ano'])['Vl.rateado'].sum().reset_index()
    
    fluxo = pd.merge(
        entradas_mensal[['Ano', 'Mes', 'Mês/Ano', 'Vl.rateado']], 
        saidas_mensal[['Ano', 'Mes', 'Mês/Ano', 'Vl.rateado']], 
        on=['Ano', 'Mes', 'Mês/Ano'], 
        how='outer', 
        suffixes=('_entradas', '_saidas')
    )
    fluxo = fluxo.fillna(0)
    
    # Criar colunas necessárias
    fluxo['Saidas_abs'] = abs(fluxo['Vl.rateado_saidas'])
    fluxo['Saldo'] = fluxo['Vl.rateado_entradas'] - fluxo['Saidas_abs']
    fluxo = fluxo.sort_values(['Ano', 'Mes']).reset_index(drop=True)
    
    # Calcular saldo acumulado
    saldos_acumulados = []
    saldo_acumulado = SALDO_INICIAL
    for _, row in fluxo.iterrows():
        saldo_acumulado = saldo_acumulado + row['Saldo']
        saldos_acumulados.append(saldo_acumulado)
    fluxo['Saldo_Acumulado'] = saldos_acumulados
    fluxo['Projetado'] = False
    
    # KPI Cards
    st.subheader("📈 Indicadores Principais")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Saldo Inicial", f"R$ {SALDO_INICIAL:,.2f}")
    with col2:
        st.metric("Total Entradas", f"R$ {total_entradas:,.2f}")
    with col3:
        st.metric("Total Saídas", f"R$ {abs(total_saidas):,.2f}")
    with col4:
        st.metric("Saldo Atual", f"R$ {saldo_atual:,.2f}")
    with col5:
        st.metric("Saldo Projetado", "R$ 0,00")
    
    st.markdown("---")
    
    # Tabs para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Fluxo Mensal", "📈 Projeção Diária", "🏢 Análise por Empresa", "🔄 Últimas Transações"])
    
    with tab1:
        st.subheader("Evolução do Fluxo de Caixa Mensal")
        
        fig = go.Figure()
        
        # Barras de entradas
        fig.add_trace(go.Bar(
            x=fluxo['Mês/Ano'],
            y=fluxo['Vl.rateado_entradas'],
            name='Entradas',
            marker_color='green',
            opacity=0.7,
            width=0.6
        ))
        
        # Barras de saídas
        fig.add_trace(go.Bar(
            x=fluxo['Mês/Ano'],
            y=fluxo['Saidas_abs'],
            name='Saídas',
            marker_color='red',
            opacity=0.7,
            width=0.6
        ))
        
        # Linha de saldo acumulado
        fig.add_trace(go.Scatter(
            x=fluxo['Mês/Ano'],
            y=fluxo['Saldo_Acumulado'],
            name='Saldo Acumulado',
            marker_color='blue',
            yaxis='y2',
            line=dict(width=3)
        ))
        
        # Linha do saldo inicial
        fig.add_hline(y=SALDO_INICIAL, line_dash="dot", line_color="gray",
                     annotation_text="Saldo Inicial", annotation_position="bottom left")
        
        fig.update_layout(
            barmode='group',
            height=500,
            xaxis_title='Mês/Ano',
            yaxis_title='Valor (R$)',
            xaxis=dict(tickangle=-45),
            yaxis=dict(title='Entradas e Saídas (R$)', side='left'),
            yaxis2=dict(title='Saldo Acumulado (R$)', overlaying='y', side='right'),
            legend=dict(x=0, y=1.1, orientation='h'),
            hovermode='x unified',
            bargap=0.15,
            bargroupgap=0.1
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela
        st.subheader("Detalhamento Mensal")
        fluxo_display = fluxo[['Mês/Ano', 'Vl.rateado_entradas', 'Saidas_abs', 'Saldo', 'Saldo_Acumulado']].copy()
        fluxo_display.columns = ['Mês/Ano', 'Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado']
        
        for col in ['Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado']:
            fluxo_display[col] = fluxo_display[col].apply(lambda x: f"R$ {x:,.2f}")
        
        st.dataframe(fluxo_display, use_container_width=True, hide_index=True)
    
    with tab2:
        st.info("🚧 Projeção Diária em desenvolvimento...")
    
    with tab3:
        st.info("🚧 Análise por Empresa em desenvolvimento...")
    
    with tab4:
        st.subheader("Últimas Transações")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Últimas Entradas**")
            ultimas_entradas = df_entradas_filtered.sort_values('Dt.pagto', ascending=False).head(10)
            ultimas_entradas['Dt.pagto'] = ultimas_entradas['Dt.pagto'].dt.strftime('%d/%m/%Y')
            ultimas_entradas['Vl.rateado'] = ultimas_entradas['Vl.rateado'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(ultimas_entradas[['Empresa', 'Dt.pagto', 'Vl.rateado']], use_container_width=True, hide_index=True)
        
        with col2:
            st.write("**Últimas Saídas**")
            ultimas_saidas = df_saidas_filtered.sort_values('Dt.pagto', ascending=False).head(10)
            ultimas_saidas['Dt.pagto'] = ultimas_saidas['Dt.pagto'].dt.strftime('%d/%m/%Y')
            ultimas_saidas['Vl.rateado'] = ultimas_saidas['Vl.rateado'].apply(lambda x: f"R$ {abs(x):,.2f}")
            st.dataframe(ultimas_saidas[['Empresa', 'Dt.pagto', 'Vl.rateado']], use_container_width=True, hide_index=True)

else:
    # Mensagem quando não há dados
    st.info("👈 Faça upload do arquivo Excel para começar a análise")
    
    with st.expander("📝 Formato esperado do arquivo"):
        st.markdown("""
        O arquivo deve conter duas abas:
        
        **Entradas:**
        - Colunas esperadas: Empresa, Vl.rateado, Dt.pagto
        - A ordem das colunas não importa
        - Os nomes podem ser em maiúsculo, minúsculo ou com acentos
        
        **Saídas:**
        - Colunas esperadas: Empresa, Vl.rateado, Dt.pagto
        
        **Exemplo de dados:**
        | Empresa | Vl.rateado | Dt.pagto |
        |---------|------------|----------|
        | Empresa A | R$ 1.500,00 | 01/01/2025 |
        | Empresa B | R$ 2.300,50 | 02/01/2025 |
        
        **Saldo Inicial:** R$ 6.355.160,80
        """)

# Footer
st.markdown("---")
st.markdown("Desenvolvido para gestão de fluxo de caixa | Saldo inicial: R$ 6.355.160,80")
