import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
import io
import re

# Configuração da página
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

# Função para verificar se é dia útil (segunda a sexta)
def is_business_day(date):
    return date.weekday() < 5  # 0-4 = segunda a sexta

# Função para carregar dados
@st.cache_data
def load_data(uploaded_file):
    try:
        if uploaded_file is not None:
            # Tentar ler as abas com diferentes nomes possíveis
            try:
                df_entradas = pd.read_excel(uploaded_file, sheet_name='Entradas')
            except:
                try:
                    df_entradas = pd.read_excel(uploaded_file, sheet_name='entradas')
                except:
                    st.error("Não foi possível encontrar a aba 'Entradas' no arquivo")
                    return None, None
            
            try:
                df_saidas = pd.read_excel(uploaded_file, sheet_name='Saídas')
            except:
                try:
                    df_saidas = pd.read_excel(uploaded_file, sheet_name='saidas')
                except:
                    st.error("Não foi possível encontrar a aba 'Saídas' no arquivo")
                    return None, None
        else:
            st.warning("Carregando dados de exemplo. Faça upload do seu arquivo para dados reais.")
            return None, None
        
        # Identificar as colunas corretas
        def find_column(df, possible_names):
            df_cols_lower = {col.lower().strip(): col for col in df.columns}
            for name in possible_names:
                if name.lower().strip() in df_cols_lower:
                    return df_cols_lower[name.lower().strip()]
            return None
        
        # Colunas possíveis para empresa
        empresa_col = find_column(df_entradas, ['Empresa', 'EMPRESA', 'empresa'])
        if empresa_col is None:
            st.error("Coluna 'Empresa' não encontrada nos dados")
            return None, None
        
        # Colunas possíveis para valor
        valor_col = find_column(df_entradas, ['Vl.rateado', 'VL.RATEADO', 'vl.rateado', 'Valor', 'VALOR', 'valor'])
        if valor_col is None:
            st.error("Coluna de valor não encontrada nos dados")
            return None, None
        
        # Colunas possíveis para data
        data_col = find_column(df_entradas, ['Dt.pagto', 'DT.PAGTO', 'dt.pagto', 'Data', 'DATA', 'data'])
        if data_col is None:
            st.error("Coluna de data não encontrada nos dados")
            return None, None
        
        # Renomear colunas para nomes padronizados
        df_entradas = df_entradas.rename(columns={
            empresa_col: 'Empresa',
            valor_col: 'Vl.rateado',
            data_col: 'Dt.pagto'
        })
        
        df_saidas = df_saidas.rename(columns={
            empresa_col: 'Empresa',
            valor_col: 'Vl.rateado',
            data_col: 'Dt.pagto'
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
        
        return df_entradas, df_saidas
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        return None, None

# Função para criar fluxo de caixa mensal com saldo inicial
def create_monthly_cash_flow(df_entradas, df_saidas, saldo_inicial, projection_months=3):
    if df_entradas is None or df_saidas is None or len(df_entradas) == 0 or len(df_saidas) == 0:
        return None
    
    try:
        # Criar coluna de mês/ano
        df_entradas['Ano'] = df_entradas['Dt.pagto'].dt.year
        df_entradas['Mes'] = df_entradas['Dt.pagto'].dt.month
        df_entradas['Mês/Ano'] = df_entradas['Ano'].astype(str) + '-' + df_entradas['Mes'].astype(str).str.zfill(2)
        
        df_saidas['Ano'] = df_saidas['Dt.pagto'].dt.year
        df_saidas['Mes'] = df_saidas['Dt.pagto'].dt.month
        df_saidas['Mês/Ano'] = df_saidas['Ano'].astype(str) + '-' + df_saidas['Mes'].astype(str).str.zfill(2)
        
        # Agrupar por mês
        entradas_mensal = df_entradas.groupby(['Ano', 'Mes', 'Mês/Ano'])['Vl.rateado'].sum().reset_index()
        saidas_mensal = df_saidas.groupby(['Ano', 'Mes', 'Mês/Ano'])['Vl.rateado'].sum().reset_index()
        
        # Merge dos dados
        fluxo = pd.merge(
            entradas_mensal[['Ano', 'Mes', 'Mês/Ano', 'Vl.rateado']], 
            saidas_mensal[['Ano', 'Mes', 'Mês/Ano', 'Vl.rateado']], 
            on=['Ano', 'Mes', 'Mês/Ano'], 
            how='outer', 
            suffixes=('_entradas', '_saidas')
        )
        fluxo = fluxo.fillna(0)
        
        # Calcular saldo do mês
        fluxo['Saldo'] = fluxo['Vl.rateado_entradas'] - fluxo['Vl.rateado_saidas']
        
        # Ordenar por data
        fluxo = fluxo.sort_values(['Ano', 'Mes'])
        
        # Calcular saldo acumulado com saldo inicial
        fluxo['Saldo_Acumulado'] = saldo_inicial + fluxo['Saldo'].cumsum()
        
        # Projeção para meses futuros
        if len(fluxo) > 0:
            last_year = fluxo['Ano'].iloc[-1]
            last_month = fluxo['Mes'].iloc[-1]
            last_saldo = fluxo['Saldo_Acumulado'].iloc[-1]
            
            # Calcular média dos últimos 3 meses para projeção
            last_3_months = fluxo.tail(min(3, len(fluxo)))
            avg_entradas = last_3_months['Vl.rateado_entradas'].mean()
            avg_saidas = last_3_months['Vl.rateado_saidas'].mean()
            
            # Criar meses projetados
            projection = []
            current_year = last_year
            current_month = last_month
            current_saldo = last_saldo
            
            for i in range(1, projection_months + 1):
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                
                month_str = f"{current_year}-{str(current_month).zfill(2)}"
                
                projected_entradas = avg_entradas
                projected_saidas = avg_saidas
                projected_saldo = projected_entradas - projected_saidas
                current_saldo += projected_saldo
                
                projection.append({
                    'Ano': current_year,
                    'Mes': current_month,
                    'Mês/Ano': month_str,
                    'Vl.rateado_entradas': projected_entradas,
                    'Vl.rateado_saidas': projected_saidas,
                    'Saldo': projected_saldo,
                    'Saldo_Acumulado': current_saldo,
                    'Projetado': True
                })
            
            df_projection = pd.DataFrame(projection)
            fluxo['Projetado'] = False
            fluxo = pd.concat([fluxo, df_projection], ignore_index=True)
        else:
            fluxo['Projetado'] = False
        
        return fluxo
    except Exception as e:
        st.error(f"Erro ao criar fluxo de caixa: {e}")
        return None

# Função para criar projeção diária (apenas dias úteis)
def create_daily_projection(df_entradas, df_saidas, saldo_atual, days_to_project=30):
    if df_entradas is None or df_saidas is None:
        return None
    
    try:
        # Adicionar dia da semana aos dados históricos
        df_entradas['Dia_Semana'] = df_entradas['Dt.pagto'].dt.dayofweek
        df_entradas['Dia_Util'] = df_entradas['Dia_Semana'].apply(lambda x: x < 5)
        
        df_saidas['Dia_Semana'] = df_saidas['Dt.pagto'].dt.dayofweek
        df_saidas['Dia_Util'] = df_saidas['Dia_Semana'].apply(lambda x: x < 5)
        
        # Calcular médias por dia da semana (apenas dias úteis)
        entradas_por_dia = df_entradas[df_entradas['Dia_Util']].groupby('Dia_Semana')['Vl.rateado'].mean()
        saidas_por_dia = df_saidas[df_saidas['Dia_Util']].groupby('Dia_Semana')['Vl.rateado'].mean()
        
        # Preencher dias sem dados com a média geral de dias úteis
        media_geral_entradas = df_entradas[df_entradas['Dia_Util']]['Vl.rateado'].mean()
        media_geral_saidas = df_saidas[df_saidas['Dia_Util']]['Vl.rateado'].mean()
        
        for dia in range(5):  # 0-4 (segunda a sexta)
            if dia not in entradas_por_dia.index:
                entradas_por_dia[dia] = media_geral_entradas
            if dia not in saidas_por_dia.index:
                saidas_por_dia[dia] = media_geral_saidas
        
        # Última data nos dados
        last_date = max(df_entradas['Dt.pagto'].max(), df_saidas['Dt.pagto'].max())
        
        # Criar projeção diária (apenas dias úteis)
        projection_daily = []
        current_date = last_date + timedelta(days=1)
        current_saldo = saldo_atual
        days_added = 0
        
        dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        
        while days_added < days_to_project:
            # Pular fins de semana
            if is_business_day(current_date):
                dia_semana = current_date.weekday()
                
                entradas_dia = entradas_por_dia[dia_semana]
                saidas_dia = saidas_por_dia[dia_semana]
                
                saldo_dia = entradas_dia - saidas_dia
                current_saldo += saldo_dia
                
                projection_daily.append({
                    'Data': current_date,
                    'Dia_Semana': dias_semana[dia_semana],
                    'Entradas_Projetadas': entradas_dia,
                    'Saidas_Projetadas': saidas_dia,
                    'Saldo_Dia': saldo_dia,
                    'Saldo_Acumulado': current_saldo
                })
                
                days_added += 1
            
            current_date += timedelta(days=1)
        
        return pd.DataFrame(projection_daily)
    except Exception as e:
        st.error(f"Erro ao criar projeção diária: {e}")
        return None

# Função para análise por empresa
def analyze_by_company(df_entradas, df_saidas):
    if df_entradas is None or df_saidas is None:
        return None
    
    try:
        # Entradas por empresa
        entradas_empresa = df_entradas.groupby('Empresa')['Vl.rateado'].agg(['sum', 'count']).reset_index()
        entradas_empresa.columns = ['Empresa', 'Total_Entradas', 'Qtd_Entradas']
        
        # Saídas por empresa
        saidas_empresa = df_saidas.groupby('Empresa')['Vl.rateado'].agg(['sum', 'count']).reset_index()
        saidas_empresa.columns = ['Empresa', 'Total_Saidas', 'Qtd_Saidas']
        
        # Merge
        empresas = pd.merge(entradas_empresa, saidas_empresa, on='Empresa', how='outer').fillna(0)
        empresas['Saldo'] = empresas['Total_Entradas'] - empresas['Total_Saidas']
        
        return empresas.sort_values('Saldo', ascending=False)
    except Exception as e:
        st.error(f"Erro na análise por empresa: {e}")
        return None

# Sidebar para upload e controles
with st.sidebar:
    st.header("📁 Upload de Dados")
    uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])
    
    st.header("⚙️ Configurações")
    projection_months = st.slider("Meses para projetar (mensal)", 1, 6, 3)
    projection_days = st.slider("Dias úteis para projetar", 5, 90, 30)
    
    st.header("📊 Filtros")
    
    # Carregar dados
    df_entradas, df_saidas = load_data(uploaded_file)
    
    if df_entradas is not None and df_saidas is not None and len(df_entradas) > 0 and len(df_saidas) > 0:
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

# Main content
if df_entradas is not None and df_saidas is not None and len(df_entradas) > 0 and len(df_saidas) > 0:
    # Aplicar filtros se selecionados
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
    
    # Mostrar estatísticas básicas
    with st.sidebar.expander("📊 Estatísticas"):
        st.write(f"Total de entradas: {len(df_entradas_filtered)}")
        st.write(f"Total de saídas: {len(df_saidas_filtered)}")
        st.write(f"Período: {df_entradas_filtered['Dt.pagto'].min().date()} a {df_entradas_filtered['Dt.pagto'].max().date()}")
    
    # Calcular saldo atual (considerando saldo inicial)
    total_entradas = df_entradas_filtered['Vl.rateado'].sum()
    total_saidas = df_saidas_filtered['Vl.rateado'].sum()
    saldo_atual = SALDO_INICIAL + total_entradas - total_saidas
    
    # Criar fluxo de caixa mensal
    fluxo = create_monthly_cash_flow(df_entradas_filtered, df_saidas_filtered, SALDO_INICIAL, projection_months)
    
    # Criar projeção diária (apenas dias úteis)
    projecao_diaria = create_daily_projection(df_entradas_filtered, df_saidas_filtered, saldo_atual, projection_days)
    
    if fluxo is not None and len(fluxo) > 0:
        # KPI Cards
        st.subheader("📈 Indicadores Principais")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Saldo Inicial", f"R$ {SALDO_INICIAL:,.2f}")
        
        with col2:
            st.metric("Total Entradas", f"R$ {total_entradas:,.2f}")
        
        with col3:
            st.metric("Total Saídas", f"R$ {total_saidas:,.2f}")
        
        with col4:
            st.metric("Saldo Atual", f"R$ {saldo_atual:,.2f}")
        
        with col5:
            if projecao_diaria is not None and len(projecao_diaria) > 0:
                saldo_projetado = projecao_diaria['Saldo_Acumulado'].iloc[-1]
                dias_projetados = len(projecao_diaria)
                st.metric(f"Saldo Projetado ({dias_projetados} dias)", f"R$ {saldo_projetado:,.2f}")
            else:
                st.metric("Saldo Projetado", "R$ 0,00")
        
        st.markdown("---")
        
        # Tabs para diferentes visualizações
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Fluxo Mensal", "📈 Projeção Diária (Dias Úteis)", "🏢 Análise por Empresa", "🔄 Últimas Transações"])
        
        with tab1:
            # Gráfico de Fluxo de Caixa Mensal
            st.subheader("Evolução do Fluxo de Caixa Mensal")
            
            fig = go.Figure()
            
            # Barras de entradas e saídas
            fig.add_trace(go.Bar(
                x=fluxo['Mês/Ano'],
                y=fluxo['Vl.rateado_entradas'],
                name='Entradas',
                marker_color='green',
                opacity=0.7
            ))
            
            fig.add_trace(go.Bar(
                x=fluxo['Mês/Ano'],
                y=-fluxo['Vl.rateado_saidas'],
                name='Saídas',
                marker_color='red',
                opacity=0.7
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
            
            # Adicionar linha para saldo inicial
            fig.add_hline(y=SALDO_INICIAL, line_dash="dot", line_color="gray",
                         annotation_text="Saldo Inicial", annotation_position="bottom left")
            
            # Adicionar anotação para separar real do projetado
            if 'Projetado' in fluxo.columns and len(fluxo[~fluxo['Projetado']]) > 0:
                last_real_x = fluxo[~fluxo['Projetado']].iloc[-1]['Mês/Ano']
                
                fig.add_shape(
                    type="line",
                    x0=last_real_x,
                    y0=0,
                    x1=last_real_x,
                    y1=1,
                    yref="paper",
                    line=dict(color="orange", width=2, dash="dash"),
                )
                
                fig.add_annotation(
                    x=last_real_x,
                    y=1,
                    yref="paper",
                    text="Início da Projeção",
                    showarrow=True,
                    arrowhead=2,
                    ax=40,
                    ay=-30,
                    font=dict(size=12, color="orange")
                )
            
            fig.update_layout(
                barmode='group',
                height=500,
                xaxis_title='Mês/Ano',
                yaxis_title='Valor (R$)',
                yaxis2=dict(
                    title='Saldo Acumulado (R$)',
                    overlaying='y',
                    side='right'
                ),
                legend=dict(x=0, y=1.1, orientation='h'),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela de Fluxo de Caixa Mensal
            st.subheader("Detalhamento Mensal")
            
            fluxo_display = fluxo[['Mês/Ano', 'Vl.rateado_entradas', 'Vl.rateado_saidas', 'Saldo', 'Saldo_Acumulado']].copy()
            fluxo_display.columns = ['Mês/Ano', 'Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado']
            
            if 'Projetado' in fluxo.columns:
                fluxo_display['Status'] = fluxo['Projetado'].apply(lambda x: '📅 Projetado' if x else '✅ Realizado')
            
            for col in ['Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado']:
                fluxo_display[col] = fluxo_display[col].apply(lambda x: f"R$ {x:,.2f}")
            
            st.dataframe(fluxo_display, use_container_width=True, hide_index=True)
        
        with tab2:
            if projecao_diaria is not None and len(projecao_diaria) > 0:
                st.subheader(f"Projeção Diária para os Próximos {len(projecao_diaria)} Dias Úteis")
                
                # Gráfico de projeção diária
                fig_daily = go.Figure()
                
                fig_daily.add_trace(go.Scatter(
                    x=projecao_diaria['Data'],
                    y=projecao_diaria['Saldo_Acumulado'],
                    name='Saldo Projetado',
                    mode='lines+markers',
                    line=dict(color='blue', width=2),
                    marker=dict(size=6)
                ))
                
                # Adicionar linha do saldo atual
                fig_daily.add_hline(y=saldo_atual, line_dash="dot", line_color="green",
                                   annotation_text="Saldo Atual", annotation_position="bottom left")
                
                fig_daily.update_layout(
                    title='Evolução do Saldo - Projeção Diária (Dias Úteis)',
                    xaxis_title='Data',
                    yaxis_title='Saldo (R$)',
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_daily, use_container_width=True)
                
                # Gráfico de barras para entradas e saídas projetadas por dia
                fig_daily_bars = go.Figure()
                
                fig_daily_bars.add_trace(go.Bar(
                    x=projecao_diaria['Data'],
                    y=projecao_diaria['Entradas_Projetadas'],
                    name='Entradas Projetadas',
                    marker_color='green',
                    opacity=0.7
                ))
                
                fig_daily_bars.add_trace(go.Bar(
                    x=projecao_diaria['Data'],
                    y=-projecao_diaria['Saidas_Projetadas'],
                    name='Saídas Projetadas',
                    marker_color='red',
                    opacity=0.7
                ))
                
                fig_daily_bars.update_layout(
                    title='Entradas e Saídas Projetadas por Dia Útil',
                    xaxis_title='Data',
                    yaxis_title='Valor (R$)',
                    height=400,
                    barmode='group',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_daily_bars, use_container_width=True)
                
                # Resumo da projeção
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_entradas_proj = projecao_diaria['Entradas_Projetadas'].sum()
                    st.metric("Total Entradas Projetadas", f"R$ {total_entradas_proj:,.2f}")
                
                with col2:
                    total_saidas_proj = projecao_diaria['Saidas_Projetadas'].sum()
                    st.metric("Total Saídas Projetadas", f"R$ {total_saidas_proj:,.2f}")
                
                with col3:
                    media_entradas_dia = projecao_diaria['Entradas_Projetadas'].mean()
                    st.metric("Média Entradas/Dia", f"R$ {media_entradas_dia:,.2f}")
                
                with col4:
                    media_saidas_dia = projecao_diaria['Saidas_Projetadas'].mean()
                    st.metric("Média Saídas/Dia", f"R$ {media_saidas_dia:,.2f}")
                
                # Tabela de projeção diária
                st.subheader("Detalhamento da Projeção Diária")
                
                daily_display = projecao_diaria.copy()
                daily_display['Data'] = daily_display['Data'].dt.strftime('%d/%m/%Y')
                
                for col in ['Entradas_Projetadas', 'Saidas_Projetadas', 'Saldo_Dia', 'Saldo_Acumulado']:
                    daily_display[col] = daily_display[col].apply(lambda x: f"R$ {x:,.2f}")
                
                st.dataframe(daily_display, use_container_width=True, hide_index=True)
            else:
                st.info("Não foi possível gerar a projeção diária.")
        
        with tab3:
            st.subheader("Análise por Empresa")
            
            empresas_df = analyze_by_company(df_entradas_filtered, df_saidas_filtered)
            
            if empresas_df is not None and len(empresas_df) > 0:
                # Gráfico de barras para saldo por empresa
                empresas_top = empresas_df.nlargest(15, 'Saldo')
                
                fig_empresas = px.bar(
                    empresas_top,
                    x='Empresa',
                    y='Saldo',
                    title='Saldo por Empresa (Top 15)',
                    color='Saldo',
                    color_continuous_scale=['red', 'yellow', 'green']
                )
                fig_empresas.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_empresas, use_container_width=True)
                
                # Gráfico de pizza para entradas por empresa
                col1, col2 = st.columns(2)
                
                with col1:
                    empresas_top_entradas = empresas_df.nlargest(10, 'Total_Entradas')
                    fig_pie_entradas = px.pie(
                        empresas_top_entradas,
                        values='Total_Entradas',
                        names='Empresa',
                        title='Top 10 Empresas - Entradas',
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie_entradas, use_container_width=True)
                
                with col2:
                    empresas_top_saidas = empresas_df.nlargest(10, 'Total_Saidas')
                    fig_pie_saidas = px.pie(
                        empresas_top_saidas,
                        values='Total_Saidas',
                        names='Empresa',
                        title='Top 10 Empresas - Saídas',
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie_saidas, use_container_width=True)
                
                # Tabela de empresas
                with st.expander("Ver todas as empresas"):
                    empresas_display = empresas_df.copy()
                    empresas_display['Total_Entradas'] = empresas_display['Total_Entradas'].apply(lambda x: f"R$ {x:,.2f}")
                    empresas_display['Total_Saidas'] = empresas_display['Total_Saidas'].apply(lambda x: f"R$ {x:,.2f}")
                    empresas_display['Saldo'] = empresas_display['Saldo'].apply(lambda x: f"R$ {x:,.2f}")
                    
                    st.dataframe(empresas_display, use_container_width=True, hide_index=True)
        
        with tab4:
            st.subheader("Últimas Transações")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Últimas Entradas**")
                ultimas_entradas = df_entradas_filtered.sort_values('Dt.pagto', ascending=False).head(20)
                ultimas_entradas['Dt.pagto'] = ultimas_entradas['Dt.pagto'].dt.strftime('%d/%m/%Y')
                ultimas_entradas['Vl.rateado'] = ultimas_entradas['Vl.rateado'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(ultimas_entradas, use_container_width=True, hide_index=True)
            
            with col2:
                st.write("**Últimas Saídas**")
                ultimas_saidas = df_saidas_filtered.sort_values('Dt.pagto', ascending=False).head(20)
                ultimas_saidas['Dt.pagto'] = ultimas_saidas['Dt.pagto'].dt.strftime('%d/%m/%Y')
                ultimas_saidas['Vl.rateado'] = ultimas_saidas['Vl.rateado'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(ultimas_saidas, use_container_width=True, hide_index=True)
        
        # Botão para download dos dados processados
        st.markdown("---")
        
        # Preparar dados para download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            fluxo.to_excel(writer, sheet_name='Fluxo_Mensal', index=False)
            if projecao_diaria is not None:
                projecao_diaria.to_excel(writer, sheet_name='Projecao_Diaria', index=False)
            if empresas_df is not None:
                empresas_df.to_excel(writer, sheet_name='Analise_Empresas', index=False)
            df_entradas_filtered.head(1000).to_excel(writer, sheet_name='Entradas', index=False)
            df_saidas_filtered.head(1000).to_excel(writer, sheet_name='Saidas', index=False)
        
        st.download_button(
            label="📥 Download Dados Processados",
            data=output.getvalue(),
            file_name=f"fluxo_caixa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👈 Faça upload do arquivo Excel para começar a análise")
    
    # Exemplo de como deve ser o arquivo
    with st.expander("📝 Formato esperado do arquivo"):
        st.markdown("""
        O arquivo deve conter duas abas:
        
        **Entradas:**
        - Empresa (texto) - Nome da empresa
        - Vl.rateado (número) - Valor da transação (pode ser com R$, pontos e vírgulas)
        - Dt.pagto (data) - Data do pagamento
        
        **Saídas:**
        - Empresa (texto) - Nome da empresa
        - Vl.rateado (número) - Valor da transação
        - Dt.pagto (data) - Data do pagamento
        
        **Saldo Inicial:** R$ 6.355.160,80 (configurado no sistema)
        
        As datas podem estar em diversos formatos (ex: 2025-08-08, 08/08/2025, etc.)
        """)

# Footer
st.markdown("---")
st.markdown("Desenvolvido para gestão de fluxo de caixa | Saldo inicial: R$ 6.355.160,80")
