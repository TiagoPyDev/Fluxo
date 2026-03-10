
    # Gráfico de Fluxo de Caixa Mensal
    st.subheader("Evolução do Fluxo de Caixa Mensal")
    
    fig = go.Figure()
    
    # Barras de entradas (sempre positivas) - MAIS GROSSAS
    fig.add_trace(go.Bar(
        x=fluxo['Mês/Ano'],
        y=fluxo['Vl.rateado_entradas'],
        name='Entradas',
        marker_color='green',
        opacity=0.7,
        width=0.6  # Aumentado de 0.3 para 0.6
    ))
    
    # Barras de saídas - MAIS GROSSAS
    fig.add_trace(go.Bar(
        x=fluxo['Mês/Ano'],
        y=fluxo['Saidas_abs'],
        name='Saídas',
        marker_color='red',
        opacity=0.7,
        width=0.6  # Aumentado de 0.3 para 0.6
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
        xaxis=dict(
            tickangle=-45,  # Inclinar os labels para melhor leitura
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title='Entradas e Saídas (R$)',
            side='left',
            tickformat='.2s',  # Formato abreviado (M para milhões, k para milhares)
            tickprefix='R$ '
        ),
        yaxis2=dict(
            title='Saldo Acumulado (R$)',
            overlaying='y',
            side='right',
            tickformat='.2s',
            tickprefix='R$ '
        ),
        legend=dict(
            x=0, 
            y=1.1, 
            orientation='h',
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='gray',
            borderwidth=1
        ),
        hovermode='x unified',
        bargap=0.15,  # Reduzido para dar mais espaço às barras
        bargroupgap=0.1,  # Mantido
        margin=dict(l=60, r=60, t=80, b=80)  # Ajustar margens
    )
    
    st.plotly_chart(fig, use_container_width=True)
