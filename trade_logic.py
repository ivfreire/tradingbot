import math
import matplotlib.pyplot as plt

def is_crescent(arr, pos, width):
	if width > pos: width = pos + 1
	for i in range(width):
		if arr[pos - i].c <= arr[pos - i - 1].c: return False
	return True

# Trades using limit price logic
def braket_trading(buying_power, portfolio, stocks, t, limits):
	acts = []
	for symbol in stocks.hist_data:
		barset = stocks.hist_data[symbol]
		if t < len(barset):
			price = barset[t].c
			if buying_power > 0 and math.floor(buying_power / (len(stocks.hist_data) * price)) > 0:
				acts.append({
					'symbol':	symbol,
					'price':	price,
					'quantity': math.floor(buying_power / (len(stocks.hist_data) * price)),
					'take_profit': { 
						'limit_price': price * limits[0]
					},
					'stop_loss': {
						'limit_price': price * limits[1] * 0.98,
						'stop_price': price * limits[1]
					}
				})
	return acts