import math
import matplotlib.pyplot as plt

def moving_average(barset, pos, width):
	avg = 0.0
	if width > pos: width = pos + 1
	for i in range(width):
		avg += barset[pos - i].c / width
	return avg

def ma_function(barset, pos, width, ma_width):
	avgs = []
	if width > pos: width = pos + 1
	for i in range(width):
		avgs.append(moving_average(barset, pos - i, ma_width))
	return avgs[::-1]

def is_crescent(arr):
	for i in range(len(arr) - 1):
		if arr[i + 1] < arr[i]: return False 
	return True


# Trades using limit price logic
def braket_trading(buying_power, portfolio, stocks, t, limits):
	acts = []
	for symbol in stocks.hist_data:
		barset = stocks.hist_data[symbol]
		if t < len(barset):
			price = barset[t].c
			if buying_power > 0 and math.floor(buying_power / (len(stocks.hist_data) * price)) > 0 and is_crescent(ma_function(barset, t, 10, 30)):
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