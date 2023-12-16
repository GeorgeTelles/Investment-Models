from datetime import datetime, timedelta
import pandas as pd
import ta
import yfinance as yf

# Lista de ativos
#ativos = ["PETR4.SA"]

df_empresas = pd.read_excel(r'C:\Users\George Telles\Desktop\Pendencias\acoesfiltradas.xlsx', header=0, usecols="A")
ativos = [str(codigo) + '.SA' for codigo in df_empresas['Codigo'].tolist()]

performance_metrics = []
PERIODO_MM1 = 9
PERIODO_MM2 = 21
LUCROMINIMO = 120

for ativo in ativos:
    try:
        data_inicial = "2015-1-1"

        rates_frame = yf.download(ativo, data_inicial)

        # Adiciona o indicador Média Movel no dataframe
        rates_frame['EMA_1'] = ta.trend.sma_indicator(rates_frame['Close'], window=PERIODO_MM1, fillna=False)
        rates_frame['EMA_2'] = ta.trend.sma_indicator(rates_frame['Close'], window=PERIODO_MM2, fillna=False)

        rates_frame['Buy_Signal'] = (rates_frame['EMA_1'] > rates_frame['EMA_2'])
        rates_frame['Sell_Signal'] = (rates_frame['EMA_1'] < rates_frame['EMA_2'])

        # Crie uma coluna 'Position' que será 1 para compras e -1 para vendas
        rates_frame['Position'] = 0
        rates_frame.loc[rates_frame['Buy_Signal'], 'Position'] = 1

        # Calcule a mudança percentual no preço de fechamento
        rates_frame['Market_Return'] = rates_frame['Close'].pct_change()

        # Crie uma coluna 'Strategy_Return' para armazenar os retornos da estratégia
        rates_frame['Strategy_Return'] = 0
        rates_frame['Strategy_Return'] = rates_frame['Strategy_Return'].astype(float)

        position = 0
        entry_date = None
        trade_records = []
        

        for index, row in rates_frame.iterrows():
            if row['Buy_Signal'] and position == 0:
                position = 1
                entry_index = rates_frame.index.get_loc(index) + 1  # Próximo índice após o sinal de compra
                if entry_index < len(rates_frame.index):
                    entry_price = rates_frame.loc[rates_frame.index[entry_index], 'Open']
                    entry_date = rates_frame.index[entry_index]  # Usar a data no próximo índice após o sinal
                else:
                    # Se entry_index for maior que o tamanho do DataFrame, use o último dado disponível
                    entry_price = rates_frame['Open'].iloc[-1]
                    entry_date = rates_frame.index[-1]
            elif position == 1 and row['Sell_Signal']:
                position = 0
                exit_index = rates_frame.index.get_loc(index) + 1  # Próximo índice após o sinal de venda

                if exit_index < len(rates_frame.index):
                    exit_price = rates_frame.loc[rates_frame.index[exit_index], 'Open']
                    exit_date = rates_frame.index[exit_index]
                else:
                    # Se exit_index for maior que o tamanho do DataFrame, use o último dado disponível
                    exit_price = rates_frame['Open'].iloc[-1]
                    exit_date = rates_frame.index[-1]

                strategy_return = (exit_price / entry_price) - 1
                trade_records.append({
                    'Entry_Date': entry_date,
                    'Exit_Date': exit_date,  # Deve ser igual a exit_index
                    'Profit': strategy_return
                })
                rates_frame.at[index, 'Strategy_Return'] = strategy_return

        # Imprima os retornos acumulados da estratégia
        total_return = rates_frame['Strategy_Return'].sum()
        total_trades = len(trade_records)
        winning_trades = len([trade for trade in trade_records if trade['Profit'] > 0])
        losing_trades = len([trade for trade in trade_records if trade['Profit'] <= 0])
        average_gain = sum([trade['Profit'] for trade in trade_records if trade['Profit'] > 0]) / winning_trades if winning_trades > 0 else 0
        average_loss = abs(sum([trade['Profit'] for trade in trade_records if trade['Profit'] < 0]) / losing_trades) if losing_trades > 0 else 0
        average_profit_per_trade = total_return / total_trades if total_trades > 0 else 0
        buy_and_hold_return = (rates_frame['Close'].iloc[-1] / rates_frame['Close'].iloc[0] - 1) * 100

        # if total_return*100 < LUCROMINIMO:
        #     continue
        # if total_return*100 < buy_and_hold_return:
        #     continue

        performance_metrics.append({
            'Ativo': ativo,
            'Retorno': total_return * 100,
            'Total de op': total_trades,
            'Op vencedoras': winning_trades,
            'Op perdedoras': losing_trades,
            'Percentual de op vencedoras': winning_trades / total_trades * 100,
            'Média de ganho por op': average_gain * 100,
            'Média de perda por op': average_loss * 100,
            'Retorno médio por op': average_profit_per_trade * 100,
            'Buy and Hold': buy_and_hold_return,
        })

        # Imprimir informações sobre o desempenho da estratégia
        # print(f'\nAnálise para o ativo {ativo}:')
        # print('Retorno total da estratégia: {:.2f}%'.format(total_return * 100))
        # print(f"Total de operações: {total_trades}")
        # print(f"Operações vencedoras: {winning_trades}")
        # print(f"Operações perdedoras: {losing_trades}")
        # print(f"Percentual de operações vencedoras: {winning_trades / total_trades * 100:.2f}%")
        # print(f"Média de ganho por operação: {average_gain * 100:.2f}%")
        # print(f"Média de perda por operação: {average_loss * 100:.2f}%")
        # print(f"Retorno médio por operação: {average_profit_per_trade * 100:.2f}%")
        # print(f"Retorno usando Buy and Hold: {buy_and_hold_return:.2f}%")

    except Exception as e:
        print(f"Erro ao processar o ativo {ativo}: {str(e)}")
        continue  # Pular para o próximo ativo em caso de erro

    # Criar DataFrame com as métricas de desempenho
performance_df = pd.DataFrame(performance_metrics)

# Exportar DataFrame para Excel
performance_df.to_excel(F"CRUZAMENTO_MMS_{PERIODO_MM1}_{PERIODO_MM2}_D1.xlsx", index=False)
