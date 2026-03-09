import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
import io

# Configuração da página
st.set_page_config(
    page_title="Fluxo de Caixa - Dashboard",
    page_icon="💰",
    layout="wide"
)

# Título principal
st.title("💰 Dashboard de Fluxo de Caixa")
st.markdown("---")

# Função para carregar dados
@st.cache_data
def load_data(uploaded_file):
    try:
        if uploaded_file is not None:
            df_entradas = pd.read_excel(uploaded_file, sheet_name='Entradas')
            df_saidas = pd.read_excel(uploaded_file, sheet_name='Saídas')
        else:
            # Se não houver arquivo, usa os dados de exemplo
            st.warning("Carregando dados de exemplo. Faça upload do seu arquivo para dados reais.")
            return None, None
        
        # Processar datas
        df_entradas['Dt.pagto'] = pd.to_datetime(df_entradas['Dt.pagto'], errors='coerce')
        df_saidas['Dt.pagto'] = pd.to_datetime(df_saidas['Dt.pagto'], errors='coerce')
        
        # Remover valores nulos
        df_entradas = df_entradas.dropna(subset=['Dt.pagto'])
        df_saidas = df_saidas.dropna(subset=['Dt.pagto'])
        
        return df_entradas, df_saidas
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None, None

# Função para criar fluxo de caixa mensal
def create_monthly_cash_flow(df_entradas, df_saidas, projection_months=3):
    if df_entradas is None or df_saidas is None:
        return None
    
    # Criar coluna de mês/ano
    df_entradas['Mês/Ano'] = df_entradas['Dt.pagto'].dt.to_period('M')
    df_saidas['Mês/Ano'] = df_saidas['Dt.pagto'].dt.to_period('M')
    
    # Agrupar por mês
    entradas_mensal = df_entradas.groupby('Mês/Ano')['Vl.rateado'].sum().reset_index()
    saidas_mensal = df_saidas.groupby('Mês/Ano')['Vl.rateado'].sum().reset_index()
    
    # Merge dos dados
    fluxo = pd.merge(entradas_mensal, saidas_mensal, on='Mês/Ano', how='outer', suffixes=('_entradas', '_saidas'))
    fluxo = fluxo.fillna(0)
    
    # Calcular saldo
    fluxo['Saldo'] = fluxo['Vl.rateado_entradas'] - fluxo['Vl.rateado_saidas']
    fluxo['Saldo_Acumulado'] = fluxo['Saldo'].cumsum()
    
    # Ordenar por data
    fluxo = fluxo.sort_values('Mês/Ano')
    fluxo['Mês/Ano_str'] = fluxo['Mês/Ano'].astype(str)
    
    # Projeção para meses futuros
    if len(fluxo) > 0:
        last_month = fluxo['Mês/Ano'].max()
        last_saldo = fluxo['Saldo_Acumulado'].iloc[-1]
        
        # Calcular média dos últimos 3 meses para projeção
        last_3_months = fluxo.tail(3)
        avg_entradas = last_3_months['Vl.rateado_entradas'].mean()
        avg_saidas = last_3_months['Vl.rateado_saidas'].mean()
        
        # Criar meses projetados
        projection = []
        current_saldo = last_saldo
        
        for i in range(1, projection_months + 1):
            next_month = last_month + i
            projected_entradas = avg_entradas
            projected_saidas = avg_saidas
            projected_saldo = projected_entradas - projected_saidas
            current_saldo += projected_saldo
            
            projection.append({
                'Mês/Ano': next_month,
                'Mês/Ano_str': str(next_month),
                'Vl.rateado_entradas': projected_entradas,
                'Vl.rateado_saidas': projected_saidas,
                'Saldo': projected_saldo,
                'Saldo_Acumulado': current_saldo,
                'Projetado': True
            })
        
        df_projection = pd.DataFrame(projection)
        fluxo['Projetado'] = False
        fluxo = pd.concat([fluxo, df_projection], ignore_index=True)
    
    return fluxo

# Função para análise por empresa
def analyze_by_company(df_entradas, df_saidas):
    if df_entradas is None or df_saidas is None:
        return None, None
    
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

# Sidebar para upload e controles
with st.sidebar:
    st.header("📁 Upload de Dados")
    uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])
    
    st.header("⚙️ Configurações")
    projection_months = st.slider("Meses para projetar", 1, 6, 3)
    
    st.header("📊 Filtros")
    
    # Carregar dados
    df_entradas, df_saidas = load_data(uploaded_file)
    
    if df_entradas is not None and df_saidas is not None:
        # Filtro de período
        min_date = min(df_entradas['Dt.pagto'].min(), df_saidas['Dt.pagto'].min())
        max_date = max(df_entradas['Dt.pagto'].max(), df_saidas['Dt.pagto'].max())
        
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
if df_entradas is not None and df_saidas is not None:
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
    
    # Criar fluxo de caixa
    fluxo = create_monthly_cash_flow(df_entradas_filtered, df_saidas_filtered, projection_months)
    
    if fluxo is not None:
        # KPI Cards
        st.subheader("📈 Indicadores Principais")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_entradas = fluxo[~fluxo['Projetado']]['Vl.rateado_entradas'].sum()
            st.metric("Total Entradas (Realizado)", f"R$ {total_entradas:,.2f}")
        
        with col2:
            total_saidas = fluxo[~fluxo['Projetado']]['Vl.rateado_saidas'].sum()
            st.metric("Total Saídas (Realizado)", f"R$ {total_saidas:,.2f}")
        
        with col3:
            saldo_atual = fluxo[~fluxo['Projetado']]['Saldo_Acumulado'].iloc[-1] if len(fluxo[~fluxo['Projetado']]) > 0 else 0
            st.metric("Saldo Atual", f"R$ {saldo_atual:,.2f}")
        
        with col4:
            if len(fluxo[fluxo['Projetado']]) > 0:
                saldo_projetado = fluxo[fluxo['Projetado']]['Saldo_Acumulado'].iloc[-1]
                st.metric("Saldo Projetado", f"R$ {saldo_projetado:,.2f}")
        
        st.markdown("---")
        
        # Gráfico de Fluxo de Caixa
        st.subheader("📊 Evolução do Fluxo de Caixa")
        
        fig = go.Figure()
        
        # Barras de entradas e saídas
        fig.add_trace(go.Bar(
            x=fluxo['Mês/Ano_str'],
            y=fluxo['Vl.rateado_entradas'],
            name='Entradas',
            marker_color='green',
            opacity=0.7
        ))
        
        fig.add_trace(go.Bar(
            x=fluxo['Mês/Ano_str'],
            y=-fluxo['Vl.rateado_saidas'],
            name='Saídas',
            marker_color='red',
            opacity=0.7
        ))
        
        # Linha de saldo acumulado
        fig.add_trace(go.Scatter(
            x=fluxo['Mês/Ano_str'],
            y=fluxo['Saldo_Acumulado'],
            name='Saldo Acumulado',
            marker_color='blue',
            yaxis='y2',
            line=dict(width=3)
        ))
        
        # Linha vertical separando real do projetado
        if len(fluxo[~fluxo['Projetado']]) > 0:
            last_real = fluxo[~fluxo['Projetado']].iloc[-1]['Mês/Ano_str']
            fig.add_vline(x=last_real, line_dash="dash", line_color="orange",
                         annotation_text="Projeção", annotation_position="top right")
        
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
        
        fluxo_display = fluxo[['Mês/Ano_str', 'Vl.rateado_entradas', 'Vl.rateado_saidas', 'Saldo', 'Saldo_Acumulado', 'Projetado']].copy()
        fluxo_display.columns = ['Mês/Ano', 'Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado', 'Projetado']
        
        # Formatação
        for col in ['Entradas', 'Saídas', 'Saldo', 'Saldo Acumulado']:
            fluxo_display[col] = fluxo_display[col].apply(lambda x: f"R$ {x:,.2f}")
        
        fluxo_display['Projetado'] = fluxo_display['Projetado'].apply(lambda x: '✅' if not x else '📅')
        
        st.dataframe(fluxo_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Análise por Empresa
        st.subheader("🏢 Análise por Empresa")
        
        empresas_df = analyze_by_company(df_entradas_filtered, df_saidas_filtered)
        
        if empresas_df is not None and len(empresas_df) > 0:
            # Gráfico de pizza para entradas por empresa
            col1, col2 = st.columns(2)
            
            with col1:
                fig_pie_entradas = px.pie(
                    empresas_df.head(10),
                    values='Total_Entradas',
                    names='Empresa',
                    title='Top 10 Empresas - Entradas',
                    hole=0.4
                )
                st.plotly_chart(fig_pie_entradas, use_container_width=True)
            
            with col2:
                fig_pie_saidas = px.pie(
                    empresas_df.head(10),
                    values='Total_Saidas',
                    names='Empresa',
                    title='Top 10 Empresas - Saídas',
                    hole=0.4
                )
                st.plotly_chart(fig_pie_saidas, use_container_width=True)
            
            # Tabela de empresas
            st.dataframe(
                empresas_df.style.format({
                    'Total_Entradas': 'R$ {:,.2f}',
                    'Total_Saidas': 'R$ {:,.2f}',
                    'Saldo': 'R$ {:,.2f}'
                }),
                use_container_width=True,
                hide_index=True
            )
        
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
        - Empresa (texto)
        - Vl.rateado (número)
        - Dt.pagto (data)
        
        **Saídas:**
        - Empresa (texto)
        - Vl.rateado (número)
        - Dt.pagto (data)
        
        As datas devem estar no formato reconhecível (ex: 2025-08-08 00:00:00)
        """)

# Footer
st.markdown("---")
st.markdown("Desenvolvido para gestão de fluxo de caixa | Atualize mensalmente para melhores resultados")
