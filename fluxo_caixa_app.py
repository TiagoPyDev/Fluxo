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
        
        # Mostrar as colunas encontradas para debug
        st.sidebar.write("Colunas encontradas - Entradas:", list(df_entradas.columns))
        st.sidebar.write("Colunas encontradas - Saídas:", list(df_saidas.columns))
        
        # Identificar as colunas corretas (ignorando espaços e diferenças de maiúsculas/minúsculas)
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
        
        # Filtrar valores zero ou muito pequenos (opcional)
        df_entradas = df_entradas[abs(df_entradas['Vl.rateado']) > 0.01]
        df_saidas = df_saidas[abs(df_saidas['Vl.rateado']) > 0.01]
        
        return df_entradas, df_saidas
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        return None, None

# Função para criar fluxo de caixa mensal
def create_monthly_cash_flow(df_entradas, df_saidas, projection_months=3):
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
        
        # Calcular saldo
        fluxo['Saldo'] = fluxo['Vl.rateado_entradas'] - fluxo['Vl.rateado_saidas']
        
        # Ordenar por data
        fluxo = fluxo.sort_values(['Ano', 'Mes'])
        fluxo['Saldo_Acumulado'] = fluxo['Saldo'].cumsum()
        
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
            
            for i in range(1, projection_months + 1):
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                
                month_str = f"{current_year}-{str(current_month).zfill(2)}"
                
                projected_entradas = avg_entradas
                projected_saidas = avg_saidas
                projected_saldo = projected_entradas - projected_saidas
                last_saldo += projected_saldo
                
                projection.append({
                    'Ano': current_year,
                    'Mes': current_month,
                    'Mês/Ano': month_str,
                    'Vl.rateado_entradas': projected_entradas,
                    'Vl.rateado_saidas': projected_saidas,
                    'Saldo': projected_saldo,
                    'Saldo_Acumulado': last_saldo,
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
    projection_months = st.slider("Meses para projetar", 1, 6, 3)
    
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
    
    # Criar fluxo de caixa
    fluxo = create_monthly_cash_flow(df_entradas_filtered, df_saidas_filtered, projection_months)
    
    if fluxo is not None and len(fluxo) > 0:
        # KPI Cards
        st.subheader("📈 Indicadores Principais")
        col1, col2, col3, col4 = st.columns(4)
        
        dados_reais = fluxo[~fluxo['Projetado']] if 'Projetado' in fluxo.columns else fluxo
        
        with col1:
            total_entradas = dados_reais['Vl.rateado_entradas'].sum()
            st.metric("Total Entradas (Realizado)", f"R$ {total_entradas:,.2f}")
        
        with col2:
            total_saidas = dados_reais['Vl.rateado_saidas'].sum()
            st.metric("Total Saídas (Realizado)", f"R$ {total_saidas:,.2f}")
        
        with col3:
            if len(dados_reais) > 0:
                saldo_atual = dados_reais['Saldo_Acumulado'].iloc[-1]
            else:
                saldo_atual = 0
            st.metric("Saldo Atual", f"R$ {saldo_atual:,.2f}")
        
        with col4:
            if 'Projetado' in fluxo.columns and len(fluxo[fluxo['Projetado']]) > 0:
                saldo_projetado = fluxo[fluxo['Projetado']]['Saldo_Acumulado'].iloc[-1]
                st.metric("Saldo Projetado", f"R$ {saldo_projetado:,.2f}")
            else:
                st.metric("Saldo Projetado", "R$ 0,00")
        
        st.markdown("---")
        
        # Gráfico de Fluxo de Caixa
        st.subheader("📊 Evolução do Fluxo de Caixa")
        
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
        
        # Linha vertical separando real do projetado
        if 'Projetado' in fluxo.columns and len(fluxo[~fluxo['Projetado']]) > 0:
            last_real = fluxo[~fluxo['Projetado']].iloc[-1]['Mês/Ano']
            fig.add_vline(x=last_real, line_dash="dash", line_color="orange",
                         annotation_text="Início da Projeção", annotation_position="top right")
        
        fig.update_layout(
            barmode='group',
            title='Fluxo de Caixa Mensal',
            xaxis_title='Mês/Ano',
            yaxis_title='Valor (R$)',
            yaxis2=dict(
                title='Saldo Acumulado (R$)',
                overlaying='y',
                side='right'
            ),
            height=500,
            legend=dict(x=0, y=1.1, orientation='h'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela de Fluxo de Caixa
        st.subheader("📋 Detalhamento Mensal")
        
        fluxo_display = fluxo[['Mês/Ano', 'Vl.rateado_entradas', 'Vl.rateado_saidas', 'Saldo', 'Saldo_Acumulado']].copy()
        fluxo_display.columns = ['Mês/Ano', 'Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado']
        
        # Adicionar coluna de status se existir
        if 'Projetado' in fluxo.columns:
            fluxo_display['Status'] = fluxo['Projetado'].apply(lambda x: '📅 Projetado' if x else '✅ Realizado')
        
        # Formatação
        for col in ['Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado']:
            fluxo_display[col] = fluxo_display[col].apply(lambda x: f"R$ {x:,.2f}")
        
        st.dataframe(fluxo_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Análise por Empresa
        st.subheader("🏢 Análise por Empresa")
        
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
        
        st.markdown("---")
        
        # Últimas transações
        st.subheader("🔄 Últimas Transações")
        
        tab1, tab2 = st.tabs(["Últimas Entradas", "Últimas Saídas"])
        
        with tab1:
            ultimas_entradas = df_entradas_filtered.sort_values('Dt.pagto', ascending=False).head(20)
            ultimas_entradas['Dt.pagto'] = ultimas_entradas['Dt.pagto'].dt.strftime('%d/%m/%Y')
            ultimas_entradas['Vl.rateado'] = ultimas_entradas['Vl.rateado'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(ultimas_entradas, use_container_width=True, hide_index=True)
        
        with tab2:
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
        
        As datas podem estar em diversos formatos (ex: 2025-08-08, 08/08/2025, etc.)
        """)

# Footer
st.markdown("---")
st.markdown("Desenvolvido para gestão de fluxo de caixa | Atualize mensalmente para melhores resultados")
