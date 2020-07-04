# Copyright (c) 2020 Icaro Freire

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import alpaca_trade_api as alpaca

# StocksAPI is the interface controller between our wallet of investiments and Alpaca API
class StocksAPI:
    def __init__(self):
        self.api = alpaca.REST('API-KEY', 'API-SECRET-KEY', 'URL-ENDPOINT')
        self.stocks = {}
        self.hist_data = {}
        return

    # Gets the historical values of opening, closures, highes, lows, volume and timestamp of the specified stock
    def get_history(self, ticker, resolution, start=None, end=None, limit=None):
        barset = self.api.get_barset(ticker, resolution, limit, start, end, None, None)[ticker]
        stocks = { 'o': [], 'c': [], 'h': [], 'l': [], 'v': [], 't': [] }
        for bar in barset:
            stocks['o'].append(bar.o)
            stocks['c'].append(bar.c)
            stocks['h'].append(bar.h)
            stocks['l'].append(bar.l)
            stocks['v'].append(bar.v)
            stocks['t'].append(bar.t)
        return stocks

    def load(self, ticker, resolution, start=None, end=None, limit=None):
        stocks = self.get_history(ticker, resolution, start, end, limit)
        self.hist_data[ticker] = stocks
        return

    # Returns the current price of the specified stock. Usage on realtime mode only.
    def price(self, ticker):
        return 300

# Wallet is the class that controls our money and stocks owned
class Wallet:
    def __init__(self, account=None):
        self.get_account(account)
        self.stocks = {}
        self.paper_trading = True
        return

    # Updates stocks prices
    def update_prices(self, stocks):
        for stock in self.stocks:
            if stock in stocks:
                self.stocks[stock]['current_price'] = stocks[stock].current_price
        return

    # Sync local wallet to Alpaca's
    def get_account(self, account):
        if account != None:
            self.buying_power = float(account.buying_power)
            self.currency = account.currency
            self.equity = float(account.equity)
            self.last_equity = float(account.last_equity)
        else:
            self.buying_power = 0.0
            self.currency = 'USD'
            self.equity = 0.0
            self.last_equity = 0.0
        return

    # Gets the current positions in stocks
    def get_positions(self, positions=None):
        if positions != None:
            for position in positions:
                self.stocks[position.symbol] = {
                    'avg_entry_price': float(position.avg_entry_price),
                    'quantity': float(position.qty),
                    'current_price': float(position.current_price)
                }
        return

    # Returns the position invested in the specified stock
    def position(self, ticker):
        if ticker in self.stocks: return self.stocks[ticker]['quantity'] * self.stocks[ticker]['current_price']
        return

    # Returns the profit made by a transaction 
    def profit(self, ticker):
        if ticker in self.stocks: return self.stocks[ticker]['quantity'] * (self.stocks[ticker]['current_price'] - self.stocks[ticker]['avg_entry_price'])
        return 0.0


    # Gets the total equity of our wallet
    def get_equity(self):
        total = self.buying_power
        for stock in self.stocks: total += self.stocks[stock]['quantity'] * self.stocks[stock]['current_price']
        return total

    # Add the stock bought to our wallet and discounts the transaction money from our buying_power
    def buy(self, ticker, quantity, price):
        if self.buying_power >= quantity * price:
            if ticker in self.stocks:
                self.stocks[ticker]['avg_entry_price'] = (self.stocks[ticker]['quantity'] * self.stocks[ticker]['avg_entry_price'] + quantity * price) / (self.stocks[ticker]['quantity'] + quantity)
                self.stocks[ticker]['quantity'] += quantity
            else: self.stocks[ticker] = {
                'quantity': quantity,
                'avg_entry_price': price,
                'current_price': price
            }
            self.buying_power -= quantity * price
        else: return False
        return

    # Removes the quantity specified from the specified stock and accounts for the money earned in the transaction
    def sell(self, ticker, quantity, price):
        if ticker in self.stocks:
            if self.stocks[ticker]['quantity'] >= quantity:
                self.stocks[ticker]['quantity'] -= quantity
                self.buying_power -= quantity * price
                return
        return False

    # Prints the current wallet to the console
    def show(self):
        print('WALLET')
        print('Money\t{} {:.2f}'.format(self.currency, self.buying_power))
        for stock in self.stocks: print('{}\t{} {:2.2f}\t{}\t'.format(stock, self.currency, self.stocks[stock]['quantity'] * self.stocks[stock]['current_price'], self.stocks[stock]['quantity']))
        print('Equity\t{} {:.2f}'.format(self.currency, self.get_equity()))
        return

# Controls transactions
class TradeAPI:
    def __init__(self):
        return

    def paper_trade(self, wallet, stocks):
        prev_price = stocks['AAPL']['o'][0]
        for price in stocks['AAPL']['o']:
            delta = (price - prev_price) * 100 / prev_price

            
            print(delta)


            if 'AAPL' in wallet.stocks: wallet.stocks['AAPL']['current_price'] = price
            prev_price = price
        return


# Instances controllers
stocks = StocksAPI()
wallet = Wallet()
trade = TradeAPI()

# Sample code
wallet.buying_power = 1000.0
stocks.load('AAPL', 'day', limit=7)
trade.paper_trade(wallet, stocks.hist_data)

wallet.show()