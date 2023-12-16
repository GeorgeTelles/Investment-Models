from datetime import datetime, timedelta
import pandas as pd
import ta
import yfinance as yf
import MetaTrader5 as mt5

if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()


ativo = "WIN$N"
PERIODO_MM = 5
PERIODO_RSI = 2
RSI_ENTRADA = 5
RSI_SAIDA = 70
LUCROMINIMO = 120
STOPLOSS = -250

data_inicial = datetime.now()

rates = mt5.copy_rates_from(ativo, mt5.TIMEFRAME_M15, data_inicial, 800000)
 
rates_frame = pd.DataFrame(rates)
rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')

rates_frame.set_index('time', inplace=True)

# Adiciona o indicador SMA e RSI no dataframe
rates_frame['SMA'] = ta.trend.sma_indicator(rates_frame['close'], window=PERIODO_MM, fillna=False)
rates_frame['RSI'] = ta.momentum.rsi(rates_frame['close'], window=PERIODO_RSI, fillna=False)

rates_frame['Buy_Signal'] = (rates_frame['RSI'] < RSI_ENTRADA)
rates_frame['Sell_Signal'] = (rates_frame['close'] > rates_frame['SMA'])

# Crie uma coluna 'Position' que será 1 para compras e -1 para vendas
rates_frame['Position'] = 0
rates_frame.loc[rates_frame['Buy_Signal'], 'Position'] = 1

# Calcule a mudança percentual no preço de fechamento
rates_frame['Market_Return'] = rates_frame['close'].diff()

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
        entry_price = rates_frame.loc[rates_frame.index[entry_index], 'open']
        entry_date = rates_frame.index[entry_index]  # Usar a data no próximo índice após o sinal
    elif position == 1 and row['Sell_Signal']:
        position = 0
        exit_index = rates_frame.index.get_loc(index) + 1  # Próximo índice após o sinal de venda
        exit_price = rates_frame.loc[rates_frame.index[exit_index], 'open']
        exit_date = rates_frame.index[exit_index]
        strategy_return = (exit_price - entry_price)
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
losing_trades = len([trade for trade in trade_records if trade['Profit'] < 0])
average_gain = sum([trade['Profit'] for trade in trade_records if trade['Profit'] > 0]) / winning_trades if winning_trades > 0 else 0
average_loss = abs(sum([trade['Profit'] for trade in trade_records if trade['Profit'] < 0]) / losing_trades) if losing_trades > 0 else 0
average_profit_per_trade = total_return / total_trades if total_trades > 0 else 0
buy_and_hold_return = (rates_frame['close'].iloc[-1] - rates_frame['close'].iloc[0])

# Imprimir informações sobre o desempenho da estratégia
print('Retorno total da estratégia: {:.2f}%'.format(total_return))
print(f"Total de operações: {total_trades}")
print(f"Operações vencedoras: {winning_trades}")
print(f"Operações perdedoras: {losing_trades}")
print(f"Percentual de operações vencedoras: {winning_trades / total_trades * 100:.2f}%")
print(f"Média de ganho por operação: {average_gain:.2f}%")
print(f"Média de perda por operação: {average_loss:.2f}%")
print(f"Retorno médio por operação: {average_profit_per_trade * 100:.2f}%")
print(f"Retorno usando Buy and Hold: {buy_and_hold_return:.2f}")


# Imprimir as datas de compra, venda e o lucro de cada operação
trade_records_df = pd.DataFrame(trade_records)
print(trade_records_df)

# Exportar DataFrames para Excel
trade_records_df.to_excel(f"operaçoes_intra_{ativo}_{RSI_ENTRADA}_{RSI_SAIDA}_M15.xlsx")


