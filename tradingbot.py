# Copyright (c) 2020 Icaro Freire

import alpaca_trade_api as tradeapi

# StocksAPI is the interface controller between our wallet of investiments and the Alpaca API
class StocksAPI:
    def __init__(self):
        self.api = tradeapi.REST('API-KEY', 'API-SECRET-KEY', 'URL')
        self.stocks = {}
        return

    # Gets the historical values highes, lows, openings and closures of the specified stock
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
        self.stocks[ticker] = stocks
        return

    # Returns the current price of the specified stock. Usage on realtime mode only.
    def price(self, ticker):
        return 300



# Wallet is the class that controls our money and stocks owned
class Wallet:
    def __init__(self, account):
        self.get_account(account)
        self.stocks = {}
        return

    # Updates local wallet from the Alpaca API
    def get_account(self, account):
        self.buying_power = account.buying_power
        self.currency = account.currency
        self.equity = account.equity
        self.last_equity = account.last_equity
        return

    # Add the stock bought to our wallet and discounts the transaction money from our buying_power
    def buy(self, ticker, amount, price):
        if self.buying_power >= amount * price:
            if ticker in self.stocks:
                self.stocks[ticker].avg_price = (self.stocks[ticker].amount * self.stocks[ticker].avg_price + amount * price) / (self.stocks[ticker].amout + amount)
                self.stocks[ticker].amount += amount
            else: self.stocks[ticker] = {
                'amount': amount,
                'avg_price': price
            }
            self.buying_power -= amount * price
        else: return False
        return

    # Removes the amount specified from the specified stock and accounts for the money earned in the transaction
    def sell(self, ticker, amount, price):
        if self.stocks[ticker].amount >= amount:
            self.stocks[ticker].amount -= amount
            self.buying_power -= amount * price
            return
        return False

    # Paper-trading
    def paper_trade(self, stocks):

        

        return

    # Prints the current wallet to the console
    def show(self, stocks):
        print('WALLET')
        print('Money\t${:.2f}'.format(self.balance))
        for stock in self.stocks: print('{}\t{}\t${:2.2f}'.format(stock, self.stocks[stock]['amount'], self.stocks[stock]['amount'] * stocks.price(stock)))
        return




stocks = StocksAPI()
wallet = Wallet(stocks.api.get_account())

stocks.load('AAPL', 'day', limit=30)
wallet.paper_trade(stocks.stocks)