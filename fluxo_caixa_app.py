import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import traceback

# Configuração da página
st.set_page_config(
    page_title="Fluxo de Caixa Real",
    page_icon="💰",
    layout="wide"
)

# ============================================================================
# ESTRUTURA DO PAINEL (modelo fixo)
# ============================================================================
PAINEL_ESTRUTURA = {
    'SALDO INICIAL': [],
    'RECEITAS TOTAL': [],
    'IMPOSTOS SOBRE VENDAS': [],
    'DESEMBOLSOS FIXOS E VARIÁVEIS': [],
    'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE': [],
    'ENTRADAS/SAÍDAS FINANCEIRAS': [],
    'Transferência entre empresas': [],
    'SALDO FINAL': []
}

# Categorias para análise detalhada (mapeamento de códigos para categorias)
CATEGORIAS_DRE = {
    # Receitas
    '31101001': 'RECEITAS TOTAL',
    '31101004': 'RECEITAS TOTAL',
    
    # Impostos sobre vendas
    '61301010': 'IMPOSTOS SOBRE VENDAS',  # PIS
    '61301011': 'IMPOSTOS SOBRE VENDAS',  # COFINS
    '61301012': 'IMPOSTOS SOBRE VENDAS',  # ISS
    '61301013': 'IMPOSTOS SOBRE VENDAS',  # CSLL
    '61301014': 'IMPOSTOS SOBRE VENDAS',  # IRPJ
    
    # Desembolsos Fixos e Variáveis
    '41101001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Salários
    '41101003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Férias
    '41101004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # 13º Salário
    '41101005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Folga trabalhada
    '41101006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Férias trabalhadas
    '41101007': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Remuneração sócios
    '41101008': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # PLR/Prêmios
    '41101011': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # FGTS
    '41101012': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # INSS
    '41101013': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Rescisão
    '41102001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Vale refeição
    '41102002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Vale transporte
    '41102003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Cesta básica
    '41102004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Plano de saúde
    '41102005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Assistência odontológica
    '41102006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Farmácia
    '41102007': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Cesta básica plus
    '41102008': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Seguro de vida
    '41102009': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Cursos externos
    '41102010': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Cursos internos
    '41102011': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Roupas/Equipamentos
    '41103001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Multa FGTS
    '41103002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Acordos trabalhistas
    '41103003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Indenizações trabalhistas
    '41103004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Depósito recursal
    '41103005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Perícia médica
    '41103006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Despesas audiências
    '41104001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Anúncios
    '41104002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Exames médicos
    '41104004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Pesquisas
    '41105001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Mão de obra terceiros
    '41201001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Energia
    '41201002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Água
    '41202001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Manutenção uniformes
    '41202002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Manutenção máquinas
    '41202003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Manutenção veículos
    '41202004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Manutenção predial
    '41202006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Manutenção rede telefônica
    '41202008': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Materiais consumo
    '41203001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Material limpeza
    '41204001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Aluguéis imóveis
    '41204002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Aluguéis veículos
    '41204003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Aluguel máquinas
    '41204004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Aluguel móveis
    '41205001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Combustíveis
    '41205002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Licenciamento/Seguros
    '41205004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Multas veículos
    '41205005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Monitoramento
    '41205006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Comunicação visual
    '41206001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Certificado/Vistoria
    '41206002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Taxas
    '41206003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Seguro empresarial
    '41206004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Seguro responsabilidade
    '41206005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Contribuição sindical
    '41206006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # IPTU
    '41207001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Motoboy
    '41207002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Correio
    '41207003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Telecomunicações
    '41207005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Nextel/Claro
    '41207007': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Internet
    '41208001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Viagens
    '41208002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Pedágio
    '41208003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Táxi/Estacionamento
    '41208004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Lanches/Refeições
    '41208005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Ajuda de custo
    '41209001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Formação pessoal
    '41209002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Brindes/Doações
    '41209003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Café/Água
    '41209004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Material consumo diversos
    '41209005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Despesas legais
    '41209006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Material escritório
    '41209009': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Bens pequeno valor
    '41210001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Assessoria administrativa
    '41210002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Assessoria contábil
    '41210003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Assessoria jurídica
    '41210004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Assessoria técnica
    '41210005': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Serviços PF
    '41210006': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Serviços PJ
    '41211002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Comissões
    '41212001': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Publicidade
    '41212003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Feiras/Eventos
    '41213002': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Brindes clientes
    '41213003': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # Indenizações clientes
    '41213004': 'DESEMBOLSOS FIXOS E VARIÁVEIS',  # CMV
    
    # Outras entradas/saídas (transferências, aplicações, etc)
    '61301036': 'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
    '61301040': 'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
    '61301042': 'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
    '61301043': 'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
    '61301044': 'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
    '61301057': 'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
    '61301061': 'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
    
    # Transferência entre empresas
    '61301069': 'Transferência entre empresas',
    
    # Entradas/Saídas Financeiras
    '61301022': 'ENTRADAS/SAÍDAS FINANCEIRAS',
    '61301072': 'ENTRADAS/SAÍDAS FINANCEIRAS',
    '61301077': 'ENTRADAS/SAÍDAS FINANCEIRAS',
    '61301019': 'ENTRADAS/SAÍDAS FINANCEIRAS',
    '61301020': 'ENTRADAS/SAÍDAS FINANCEIRAS',
    '61301037': 'ENTRADAS/SAÍDAS FINANCEIRAS',
}

# ============================================================================
# Funções de processamento
# ============================================================================
@st.cache_data
def processar_dados(df_base, empresas_selecionadas, data_inicio, data_fim):
    """
    Processa os dados da base conforme filtros e estrutura do painel
    """
    try:
        # Verificar se as colunas necessárias existem
        colunas_necessarias = ['Empresa', 'Segmento', 'Vl.rateado', 'Mês']
        for col in colunas_necessarias:
            if col not in df_base.columns:
                st.error(f"Coluna '{col}' não encontrada no arquivo. Colunas disponíveis: {list(df_base.columns)}")
                return None, None
        
        # Converter colunas de data
        df_base['Mês'] = pd.to_datetime(df_base['Mês'], errors='coerce')
        
        # Remover linhas com datas inválidas
        df_base = df_base.dropna(subset=['Mês'])
        
        if df_base.empty:
            st.error("Nenhuma data válida encontrada na coluna 'Mês'")
            return None, None
        
        # Aplicar filtros
        df_filtrado = df_base[
            (df_base['Empresa'].isin(empresas_selecionadas)) &
            (df_base['Mês'] >= pd.Timestamp(data_inicio)) &
            (df_base['Mês'] <= pd.Timestamp(data_fim))
        ].copy()
        
        if df_filtrado.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados")
            return None, None
        
        # Extrair mês/ano para agrupamento
        df_filtrado['Ano_Mes'] = df_filtrado['Mês'].dt.to_period('M')
        
        # Lista de meses no período
        meses_periodo = pd.period_range(
            start=pd.Timestamp(data_inicio).to_period('M'),
            end=pd.Timestamp(data_fim).to_period('M'),
            freq='M'
        )
        
        # Inicializar dicionário para resultados
        resultados = {categoria: {mes: 0.0 for mes in meses_periodo} 
                      for categoria in PAINEL_ESTRUTURA.keys()}
        
        # Processar cada linha
        for idx, row in df_filtrado.iterrows():
            try:
                segmento = str(row['Segmento']).strip()
                categoria = CATEGORIAS_DRE.get(segmento, None)
                
                if categoria and categoria in resultados:
                    mes = row['Ano_Mes']
                    if mes in resultados[categoria]:
                        # Garantir que o valor é numérico
                        valor = pd.to_numeric(row['Vl.rateado'], errors='coerce')
                        if pd.notna(valor):
                            resultados[categoria][mes] += valor
            except Exception as e:
                st.warning(f"Erro ao processar linha {idx}: {str(e)[:100]}")
                continue
        
        # Calcular saldo inicial (Janeiro 2025)
        saldo_inicial_janeiro = 6355160.795000029  # Valor do painel
        
        # Calcular saldos acumulados
        saldos_finais = {}
        saldo_acumulado = saldo_inicial_janeiro
        
        for mes in sorted(meses_periodo):
            # Receitas (positivas)
            receitas = resultados['RECEITAS TOTAL'].get(mes, 0.0)
            
            # Despesas (negativas - considerando que já estão negativas na base)
            despesas_totais = (
                resultados['IMPOSTOS SOBRE VENDAS'].get(mes, 0.0) +
                resultados['DESEMBOLSOS FIXOS E VARIÁVEIS'].get(mes, 0.0) +
                resultados['OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE'].get(mes, 0.0) +
                resultados['ENTRADAS/SAÍDAS FINANCEIRAS'].get(mes, 0.0) +
                resultados['Transferência entre empresas'].get(mes, 0.0)
            )
            
            # Calcular saldo do mês
            saldo_mes = receitas + despesas_totais  # despesas já são negativas
            saldo_acumulado += saldo_mes
            saldos_finais[mes] = saldo_acumulado
        
        resultados['SALDO INICIAL'] = {meses_periodo[0]: saldo_inicial_janeiro}
        resultados['SALDO FINAL'] = saldos_finais
        
        return resultados, meses_periodo
        
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        st.error(traceback.format_exc())
        return None, None

def formatar_valor(valor):
    """Formata valor monetário"""
    try:
        if pd.isna(valor) or valor == 0:
            return "R$ 0,00"
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def criar_dataframe_resultados(resultados, meses_periodo):
    """Cria DataFrame com os resultados para exibição"""
    if resultados is None or meses_periodo is None:
        return pd.DataFrame()
    
    dados = []
    
    for categoria in PAINEL_ESTRUTURA.keys():
        linha = {'Categoria': categoria}
        for mes in meses_periodo:
            valor = resultados.get(categoria, {}).get(mes, 0.0)
            linha[str(mes)] = valor
        dados.append(linha)
    
    df_resultados = pd.DataFrame(dados)
    
    # Adicionar linha de totais
    totais = {'Categoria': 'TOTAL'}
    for mes in meses_periodo:
        soma = 0.0
        for categoria in ['RECEITAS TOTAL', 'IMPOSTOS SOBRE VENDAS', 
                          'DESEMBOLSOS FIXOS E VARIÁVEIS', 
                          'OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE',
                          'ENTRADAS/SAÍDAS FINANCEIRAS', 'Transferência entre empresas']:
            soma += resultados.get(categoria, {}).get(mes, 0.0)
        totais[str(mes)] = soma
    
    df_resultados = pd.concat([df_resultados, pd.DataFrame([totais])], ignore_index=True)
    
    return df_resultados

def criar_grafico_fluxo(resultados, meses_periodo):
    """Cria gráfico de fluxo de caixa"""
    if resultados is None or meses_periodo is None:
        return go.Figure()
    
    meses_str = [str(mes) for mes in meses_periodo]
    
    receitas = [resultados['RECEITAS TOTAL'].get(mes, 0.0) for mes in meses_periodo]
    despesas = [
        resultados['IMPOSTOS SOBRE VENDAS'].get(mes, 0.0) +
        resultados['DESEMBOLSOS FIXOS E VARIÁVEIS'].get(mes, 0.0) +
        resultados['OUTRAS ENTRADAS/SAÍDAS QUE NÃO AFETAM O DRE'].get(mes, 0.0) +
        resultados['ENTRADAS/SAÍDAS FINANCEIRAS'].get(mes, 0.0) +
        resultados['Transferência entre empresas'].get(mes, 0.0)
        for mes in meses_periodo
    ]
    
    saldo_final = [resultados['SALDO FINAL'].get(mes, 0.0) for mes in meses_periodo]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Receitas',
        x=meses_str,
        y=receitas,
        marker_color='#2ecc71',
        text=[formatar_valor(v) for v in receitas],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Despesas',
        x=meses_str,
        y=despesas,
        marker_color='#e74c3c',
        text=[formatar_valor(v) for v in despesas],
        textposition='outside'
    ))
    
    fig.add_trace(go.Scatter(
        name='Saldo Final',
        x=meses_str,
        y=saldo_final,
        mode='lines+markers',
        line=dict(color='#3498db', width=3),
        marker=dict(size=8),
        yaxis='y2',
        text=[formatar_valor(v) for v in saldo_final],
        textposition='top center'
    ))
    
    fig.update_layout(
        title='Fluxo de Caixa - Receitas vs Despesas',
        barmode='group',
        xaxis_title='Mês',
        yaxis_title='Valor (R$)',
        yaxis2=dict(
            title='Saldo Final (R$)',
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    return fig

def criar_grafico_saldo(resultados, meses_periodo):
    """Cria gráfico de evolução do saldo"""
    if resultados is None or meses_periodo is None:
        return go.Figure()
    
    meses_str = [str(mes) for mes in meses_periodo]
    saldo_inicial = [resultados['SALDO INICIAL'].get(mes, 0.0) for mes in meses_periodo]
    saldo_final = [resultados['SALDO FINAL'].get(mes, 0.0) for mes in meses_periodo]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        name='Saldo Inicial',
        x=meses_str,
        y=saldo_inicial,
        mode='lines+markers',
        line=dict(color='#f39c12', width=2, dash='dash'),
        marker=dict(size=6),
        text=[formatar_valor(v) for v in saldo_inicial],
        textposition='top center'
    ))
    
    fig.add_trace(go.Scatter(
        name='Saldo Final',
        x=meses_str,
        y=saldo_final,
        mode='lines+markers',
        line=dict(color='#27ae60', width=3),
        marker=dict(size=8),
        text=[formatar_valor(v) for v in saldo_final],
        textposition='top center'
    ))
    
    fig.update_layout(
        title='Evolução do Saldo',
        xaxis_title='Mês',
        yaxis_title='Saldo (R$)',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400
    )
    
    return fig

def exportar_excel(df_resultados):
    """Exporta DataFrame para Excel"""
    if df_resultados.empty:
        return BytesIO().getvalue()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_resultados.to_excel(writer, sheet_name='Fluxo de Caixa', index=False)
    return output.getvalue()

# ============================================================================
# Interface Principal
# ============================================================================
st.title("💰 Fluxo de Caixa Real")
st.markdown("---")

# Inicializar session state
if 'usar_exemplo' not in st.session_state:
    st.session_state['usar_exemplo'] = False

# Sidebar - Filtros e Upload
with st.sidebar:
    st.header("📁 Upload da Base")
    
    uploaded_file = st.file_uploader(
        "Escolha o arquivo Excel com a base de dados",
        type=['xlsx', 'xls'],
        help="Formato esperado: arquivo com colunas Empresa, Segmento, Descrição, Vl.rateado, Valor, Dt.emissao, Mês"
    )
    
    st.markdown("---")
    st.header("🔍 Filtros")
    
    if uploaded_file is not None:
        try:
            # Tentar ler a planilha 'Base'
            df_base = pd.read_excel(uploaded_file, sheet_name='Base')
            
            st.success(f"✅ Arquivo carregado com sucesso!")
            st.info(f"📊 Registros: {len(df_base):,}")
            st.info(f"📋 Colunas: {', '.join(df_base.columns)}")
            
            # Verificar se as colunas necessárias existem
            colunas_necessarias = ['Empresa', 'Segmento', 'Vl.rateado', 'Mês']
            colunas_faltantes = [col for col in colunas_necessarias if col not in df_base.columns]
            
            if colunas_faltantes:
                st.error(f"Colunas faltantes: {', '.join(colunas_faltantes)}")
                st.stop()
            
            # Lista única de empresas
            empresas = sorted(df_base['Empresa'].dropna().unique())
            
            if not empresas:
                st.error("Nenhuma empresa encontrada na coluna 'Empresa'")
                st.stop()
            
            empresas_selecionadas = st.multiselect(
                "Selecione as empresas",
                options=empresas,
                default=empresas
            )
            
            if not empresas_selecionadas:
                st.warning("Selecione pelo menos uma empresa")
                st.stop()
            
            # Filtro de data
            df_base['Mês'] = pd.to_datetime(df_base['Mês'], errors='coerce')
            df_base = df_base.dropna(subset=['Mês'])
            
            if df_base.empty:
                st.error("Nenhuma data válida encontrada na coluna 'Mês'")
                st.stop()
            
            data_min = df_base['Mês'].min().date()
            data_max = df_base['Mês'].max().date()
            
            st.write("Período de análise")
            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input(
                    "Data inicial",
                    value=data_min,
                    min_value=data_min,
                    max_value=data_max
                )
            with col2:
                data_fim = st.date_input(
                    "Data final",
                    value=data_max,
                    min_value=data_min,
                    max_value=data_max
                )
            
            if data_inicio > data_fim:
                st.error("Data inicial não pode ser maior que data final")
                st.stop()
            
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {str(e)}")
            st.error(traceback.format_exc())
            st.stop()
    else:
        st.warning("Por favor, faça o upload do arquivo de base")
        
        st.markdown("---")
        st.info("ℹ️ Use o botão abaixo para demonstração")
        if st.button("Usar dados exemplo"):
            st.session_state['usar_exemplo'] = True
            st.rerun()

# Área Principal
if uploaded_file is not None:
    # Processar dados
    with st.spinner("Processando dados..."):
        resultados, meses_periodo = processar_dados(
            df_base, empresas_selecionadas, data_inicio, data_fim
        )
    
    if resultados is None or meses_periodo is None:
        st.error("Erro ao processar os dados. Verifique o formato do arquivo.")
        st.stop()
    
    # Métricas principais
    st.header("📊 Resumo do Período")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_receitas = sum(resultados['RECEITAS TOTAL'].values())
        st.metric(
            "Total Receitas",
            formatar_valor(total_receitas)
        )
    
    with col2:
        total_despesas = abs(sum(
            resultados['IMPOSTOS SOBRE VENDAS'].values()
        ) + sum(resultados['DESEMBOLSOS FIXOS E VARIÁVEIS'].values()))
        st.metric(
            "Total Despesas",
            formatar_valor(total_despesas)
        )
    
    with col3:
        saldo_inicial = resultados['SALDO INICIAL'].get(meses_periodo[0], 0.0)
        st.metric(
            "Saldo Inicial",
            formatar_valor(saldo_inicial)
        )
    
    with col4:
        saldo_final = resultados['SALDO FINAL'].get(meses_periodo[-1], 0.0)
        variacao = saldo_final - saldo_inicial
        delta_color = "normal" if variacao >= 0 else "inverse"
        st.metric(
            "Saldo Final",
            formatar_valor(saldo_final),
            delta=f"{formatar_valor(variacao)}",
            delta_color=delta_color
        )
    
    st.markdown("---")
    
    # Gráficos
    st.header("📈 Análise Gráfica")
    
    tab1, tab2 = st.tabs(["Receitas vs Despesas", "Evolução do Saldo"])
    
    with tab1:
        fig1 = criar_grafico_fluxo(resultados, meses_periodo)
        st.plotly_chart(fig1, use_container_width=True)
    
    with tab2:
        fig2 = criar_grafico_saldo(resultados, meses_periodo)
        st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    # Tabela de resultados
    st.header("📋 Detalhamento do Fluxo de Caixa")
    
    df_resultados = criar_dataframe_resultados(resultados, meses_periodo)
    
    if not df_resultados.empty:
        # Formatação para exibição
        df_exibicao = df_resultados.copy()
        for col in df_exibicao.columns[1:]:
            df_exibicao[col] = df_exibicao[col].apply(formatar_valor)
        
        st.dataframe(
            df_exibicao,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Categoria": st.column_config.Column("Categoria", width=300)
            }
        )
        
        # Botões de exportação
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            csv = df_resultados.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"fluxo_caixa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            excel_data = exportar_excel(df_resultados)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"fluxo_caixa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Análise detalhada por categoria
        st.markdown("---")
        st.header("🔍 Análise Detalhada por Categoria")
        
        categorias_disponiveis = [c for c in PAINEL_ESTRUTURA.keys() 
                                  if c not in ['SALDO INICIAL', 'SALDO FINAL']]
        
        categoria_selecionada = st.selectbox(
            "Selecione uma categoria para análise detalhada",
            options=categorias_disponiveis
        )
        
        if categoria_selecionada:
            # Filtrar apenas itens da categoria selecionada
            codigos_categoria = [k for k, v in CATEGORIAS_DRE.items() if v == categoria_selecionada]
            
            df_detalhado = df_base[
                (df_base['Empresa'].isin(empresas_selecionadas)) &
                (df_base['Segmento'].astype(str).isin(codigos_categoria)) &
                (pd.to_datetime(df_base['Mês']) >= pd.Timestamp(data_inicio)) &
                (pd.to_datetime(df_base['Mês']) <= pd.Timestamp(data_fim))
            ].copy()
            
            if not df_detalhado.empty:
                df_detalhado['Mês'] = pd.to_datetime(df_detalhado['Mês']).dt.to_period('M')
                df_detalhado['Valor Formatado'] = df_detalhado['Vl.rateado'].apply(formatar_valor)
                
                # Agrupar por mês e descrição
                df_pivot = df_detalhado.pivot_table(
                    values='Vl.rateado',
                    index='Descrição',
                    columns='Mês',
                    aggfunc='sum',
                    fill_value=0
                )
                
                # Formatar valores
                df_pivot_formatado = df_pivot.copy()
                for col in df_pivot_formatado.columns:
                    df_pivot_formatado[col] = df_pivot_formatado[col].apply(formatar_valor)
                
                st.dataframe(
                    df_pivot_formatado,
                    use_container_width=True
                )
                
                # Gráfico da categoria
                if len(df_pivot) > 0:
                    fig_categoria = go.Figure()
                    
                    for descricao in df_pivot.index[:10]:  # Limitar a 10 itens
                        valores = df_pivot.loc[descricao]
                        fig_categoria.add_trace(go.Scatter(
                            name=descricao[:30] + "..." if len(descricao) > 30 else descricao,
                            x=[str(m) for m in df_pivot.columns],
                            y=valores,
                            mode='lines+markers'
                        ))
                    
                    fig_categoria.update_layout(
                        title=f'Evolução - {categoria_selecionada}',
                        xaxis_title='Mês',
                        yaxis_title='Valor (R$)',
                        hovermode='x unified',
                        height=400
                    )
                    
                    st.plotly_chart(fig_categoria, use_container_width=True)
                
            else:
                st.info(f"Nenhum dado encontrado para a categoria {categoria_selecionada} no período selecionado")
    else:
        st.warning("Nenhum resultado para exibir")
    
    # Rodapé
    st.markdown("---")
    st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

elif st.session_state.get('usar_exemplo', False):
    st.info("👈 Por favor, faça o upload do arquivo 'Fluxo.xlsx' para visualizar os dados de exemplo")
    st.session_state['usar_exemplo'] = False

else:
    # Mensagem inicial
    st.info("👈 Faça o upload do arquivo de base no menu lateral para começar")
    
    # Exemplo da estrutura esperada
    with st.expander("📋 Estrutura esperada do arquivo"):
        st.markdown("""
        O arquivo Excel deve conter uma planilha chamada **Base** com as seguintes colunas:
        
        - **Empresa**: Nome da empresa
        - **Segmento**: Código do segmento (mapeado para categorias)
        - **Descrição**: Descrição da transação
        - **Vl.rateado**: Valor rateado da transação
        - **Valor**: Valor original
        - **Dt.emissao**: Data de emissão
        - **Mês**: Mês de referência
        
        ### Exemplo de linhas:
