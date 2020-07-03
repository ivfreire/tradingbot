# Copyright (c) 2020 Icaro Freire

import sys
import finnhub

# StocksAPI is the interface controller between our wallet of investiments and the Finnhub API
class StocksAPI:
    def __init__(self, apiKey):
        self.configuration = finnhub.Configuration(api_key={ 'token': apiKey })
        print('Using api_key: {} to connect'.format(apiKey))
        self.client = finnhub.DefaultApi(finnhub.ApiClient(self.configuration))
        if self.client: print('Connected to Finnhub API successfully!')

        self.stocks = {}

        return

    # Gets the historical values highes, lows, openings and closures of the specified stock
    def get_history(self, ticker, resolution, fromdate, todate):
        query = self.client.stock_candles(ticker, resolution, fromdate, todate)
        self.stocks[ticker] = query

    # Returns the current price of the specified stock. Usage on realtime mode only.
    def price(self, ticker):
        return 300



# Wallet is the class that controls our money and stocks owned
class Wallet:
    def __init__(self, balance):
        self.balance = balance
        self.stocks = {}
        return

    # Add the stock bought to our wallet and discounts the transaction money from our balance
    def buy(self, ticker, amount, price):
        if self.balance >= amount * price:
            if ticker in self.stocks:
                self.stocks[ticker].avg_price = (self.stocks[ticker].amount * self.stocks[ticker].avg_price + amount * price) / (self.stocks[ticker].amout + amount)
                self.stocks[ticker].amount += amount
            else: self.stocks[ticker] = {
                'amount': amount,
                'avg_price': price
            }
            self.balance -= amount * price
        else: return False
        return

    # Removes the amount specified from the specified stock and accounts for the money earned in the transaction
    def sell(self, ticker, amount, price):
        if self.stocks[ticker].amount >= amount:
            self.stocks[ticker].amount -= amount
            self.balance -= amount * price
            return
        return False

    # Prints the current wallet to the console
    def show(self, stocks):
        print('WALLET')
        print('Money\t${:.2f}'.format(self.balance))
        for stock in self.stocks: print('{}\t{}\t${:2.2f}'.format(stock, self.stocks[stock]['amount'], self.stocks[stock]['amount'] * stocks.price(stock)))
        return

stocks = StocksAPI(sys.argv[1])
wallet = Wallet(1000.0)

wallet.buy('AAPL', 1.0, 300.0)

wallet.show(stocks)

# print(stocks.get_history('AAPL', 'D', 1590988249, 1591852249))