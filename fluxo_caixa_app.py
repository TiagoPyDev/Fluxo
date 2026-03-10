# Função para criar fluxo de caixa mensal com saldo inicial - CORRIGIDA
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
        
        # IMPORTANTE: Verificar o sinal das saídas
        media_saidas = fluxo['Vl.rateado_saidas'].mean()
        
        # Calcular o saldo do mês considerando o sinal correto
        if media_saidas > 0:
            # Saídas estão positivas - precisamos subtrair
            fluxo['Saldo'] = fluxo['Vl.rateado_entradas'] - fluxo['Vl.rateado_saidas']
            st.info(f"📊 Saídas detectadas como valores POSITIVOS (média: R$ {media_saidas:,.2f})")
        else:
            # Saídas já estão negativas - podemos somar diretamente
            fluxo['Saldo'] = fluxo['Vl.rateado_entradas'] + fluxo['Vl.rateado_saidas']
            st.info(f"📊 Saídas detectadas como valores NEGATIVOS (média: R$ {media_saidas:,.2f})")
        
        # Para o gráfico, vamos manter os valores originais de saídas
        # Mas vamos adicionar uma coluna com valores absolutos para uso futuro
        fluxo['Saidas_abs'] = abs(fluxo['Vl.rateado_saidas'])
        
        # Ordenar por data
        fluxo = fluxo.sort_values(['Ano', 'Mes']).reset_index(drop=True)
        
        # Calcular saldo acumulado com saldo inicial
        saldos_acumulados = []
        saldo_acumulado = saldo_inicial
        
        for _, row in fluxo.iterrows():
            saldo_acumulado = saldo_acumulado + row['Saldo']
            saldos_acumulados.append(saldo_acumulado)
        
        fluxo['Saldo_Acumulado'] = saldos_acumulados
        
        # Projeção para meses futuros
        if len(fluxo) > 0:
            last_year = fluxo['Ano'].iloc[-1]
            last_month = fluxo['Mes'].iloc[-1]
            last_saldo = fluxo['Saldo_Acumulado'].iloc[-1]
            
            # Calcular média dos últimos 3 meses para projeção
            ultimos_meses = fluxo.tail(min(3, len(fluxo)))
            avg_entradas = ultimos_meses['Vl.rateado_entradas'].mean()
            avg_saidas = ultimos_meses['Vl.rateado_saidas'].mean()
            
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
                
                # Calcular saldo projetado da mesma forma que o histórico
                if media_saidas > 0:
                    projected_saldo = projected_entradas - projected_saidas
                else:
                    projected_saldo = projected_entradas + projected_saidas
                
                current_saldo = current_saldo + projected_saldo
                
                projection.append({
                    'Ano': current_year,
                    'Mes': current_month,
                    'Mês/Ano': month_str,
                    'Vl.rateado_entradas': projected_entradas,
                    'Vl.rateado_saidas': projected_saidas,
                    'Saidas_abs': abs(projected_saidas),  # Adicionar valor absoluto
                    'Saldo': projected_saldo,
                    'Saldo_Acumulado': current_saldo,
                    'Projetado': True
                })
            
            df_projection = pd.DataFrame(projection)
            fluxo['Projetado'] = False
            fluxo['Saidas_abs'] = abs(fluxo['Vl.rateado_saidas'])  # Garantir que todos tenham
            fluxo = pd.concat([fluxo, df_projection], ignore_index=True)
        else:
            fluxo['Projetado'] = False
            fluxo['Saidas_abs'] = abs(fluxo['Vl.rateado_saidas'])
        
        return fluxo
    except Exception as e:
        st.error(f"Erro ao criar fluxo de caixa: {e}")
        return None
