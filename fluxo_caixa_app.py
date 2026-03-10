with tab1:
    # Gráfico de Fluxo de Caixa Mensal
    st.subheader("Evolução do Fluxo de Caixa Mensal")
    
    fig = go.Figure()
    
    # Verificar se as saídas estão negativas para o gráfico
    media_saidas = fluxo['Vl.rateado_saidas'].mean()
    
    # Barras de entradas (sempre positivas)
    fig.add_trace(go.Bar(
        x=fluxo['Mês/Ano'],
        y=fluxo['Vl.rateado_entradas'],
        name='Entradas',
        marker_color='green',
        opacity=0.7,
        width=0.3  # Largura das barras
    ))
    
    # Barras de saídas - AGORA POSITIVAS para ficarem lado a lado com entradas
    if media_saidas < 0:
        # Se saídas estão negativas, usar valor absoluto para mostrar para cima
        fig.add_trace(go.Bar(
            x=fluxo['Mês/Ano'],
            y=abs(fluxo['Vl.rateado_saidas']),
            name='Saídas',
            marker_color='red',
            opacity=0.7,
            width=0.3  # Largura das barras
        ))
    else:
        # Se saídas já estão positivas, mostrar como estão
        fig.add_trace(go.Bar(
            x=fluxo['Mês/Ano'],
            y=fluxo['Vl.rateado_saidas'],
            name='Saídas',
            marker_color='red',
            opacity=0.7,
            width=0.3  # Largura das barras
        ))
    
    # Linha de saldo acumulado (pode ficar no eixo direito ou esquerdo)
    fig.add_trace(go.Scatter(
        x=fluxo['Mês/Ano'],
        y=fluxo['Saldo_Acumulado'],
        name='Saldo Acumulado',
        marker_color='blue',
        yaxis='y2',  # Manter no eixo direito para não misturar escalas
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
        barmode='group',  # Barras lado a lado (group) em vez de empilhadas
        height=500,
        xaxis_title='Mês/Ano',
        yaxis_title='Valor de Entradas e Saídas (R$)',
        yaxis2=dict(
            title='Saldo Acumulado (R$)',
            overlaying='y',
            side='right'
        ),
        legend=dict(
            x=0, 
            y=1.1, 
            orientation='h',
            bgcolor='rgba(255,255,255,0.8)'
        ),
        hovermode='x unified',
        bargap=0.2,  # Espaço entre grupos de barras
        bargroupgap=0.1  # Espaço entre barras dentro do mesmo grupo
    )
    
    st.plotly_chart(fig, use_container_width=True)
