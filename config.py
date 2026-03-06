# config.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import holidays

# Configurações
FERIADOS_BR = holidays.Brazil()
DIAS_UTEIS = list(range(5))  # 0-4 = segunda a sexta
DIAS_PARA_CREDITO = 2  # Dias após pagamento para dinheiro cair na conta

# Cores para gráficos
CORES = {
    'entradas': '#2E8B57',  # Verde
    'saidas': '#DC143C',     # Vermelho
    'saldo': '#1E3A8A',      # Azul escuro
    'saldo_zero': '#9CA3AF'   # Cinza
}
