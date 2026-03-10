# Função para criar fluxo de caixa mensal com saldo inicial - CORRIGIDA DEFINITIVAMENTE
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
        
        # Calcular saldo do mês (entradas - saídas)
        fluxo['Saldo'] = fluxo['Vl.rateado_entradas'] - fluxo['Vl.rateado_saidas']
        
        # Ordenar por data
        fluxo = fluxo.sort_values(['Ano', 'Mes']).reset_index(drop=True)
        
        # CORREÇÃO DEFINITIVA: Calcular saldo acumulado com saldo inicial
        # Começa com saldo inicial e adiciona o saldo de cada mês
        saldos_acumulados = []
        saldo_acumulado = saldo_inicial  # Inicia com o saldo inicial
        
        for idx, row in fluxo.iterrows():
            # Adiciona o saldo do mês atual (que pode ser positivo ou negativo)
            saldo_acumulado = saldo_acumulado + row['Saldo']
            saldos_acumulados.append(saldo_acumulado)
        
        fluxo['Saldo_Acumulado'] = saldos_acumulados
        
        # Debug - remover em produção
        st.write("Debug - Verificação do cálculo:")
        st.write(f"Saldo inicial: R$ {saldo_inicial:,.2f}")
        
        for i, row in fluxo.iterrows():
            st.write(f"{row['Mês/Ano']}: Entradas: R$ {row['Vl.rateado_entradas']:,.2f}, "
                    f"Saídas: R$ {row['Vl.rateado_saidas']:,.2f}, "
                    f"Saldo mês: R$ {row['Saldo']:,.2f}, "
                    f"Acumulado: R$ {row['Saldo_Acumulado']:,.2f}")
        
        # Projeção para meses futuros
        if len(fluxo) > 0:
            last_year = fluxo['Ano'].iloc[-1]
            last_month = fluxo['Mes'].iloc[-1]
            last_saldo = fluxo['Saldo_Acumulado'].iloc[-1]  # Saldo acumulado até o último mês real
            
            # Calcular média dos últimos 3 meses para projeção
            ultimos_meses = fluxo.tail(min(3, len(fluxo)))
            avg_entradas = ultimos_meses['Vl.rateado_entradas'].mean()
            avg_saidas = ultimos_meses['Vl.rateado_saidas'].mean()
            
            # Criar meses projetados
            projection = []
            current_year = last_year
            current_month = last_month
            current_saldo = last_saldo  # Começa com o saldo do último mês real
            
            for i in range(1, projection_months + 1):
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                
                month_str = f"{current_year}-{str(current_month).zfill(2)}"
                
                projected_entradas = avg_entradas
                projected_saidas = avg_saidas
                projected_saldo = projected_entradas - projected_saidas
                current_saldo = current_saldo + projected_saldo
                
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
        
        # Verificação final do saldo acumulado
        st.write("✅ **Correção aplicada!** O saldo acumulado agora começa com o saldo inicial e soma/subtrai corretamente a cada mês.")
        st.write(f"Saldo inicial: R$ {saldo_inicial:,.2f}")
        st.write(f"Saldo final (real + projeção): R$ {fluxo['Saldo_Acumulado'].iloc[-1]:,.2f}")
        
        return fluxo
    except Exception as e:
        st.error(f"Erro ao criar fluxo de caixa: {e}")
        return None
