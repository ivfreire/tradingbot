# Copyright (c) 2020 Icaro Freire

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import time
import datetime
import alpaca_trade_api as alpaca

# Machine-Learning controller   - Still under development
class NeuralNetwork:
    def __init__(self, inputs, layers, nodes, outputs):
        self.inputs = np.zeros(inputs)
        self.nodes = np.zeros((layers, nodes))
        self.outputs = np.zeros(outputs)

        self.biases = [np.zeros(inputs), np.zeros((layers, nodes)), np.zeros(outputs)]

        self.links = []
        self.links.append(np.zeros((inputs, nodes)))
        for i in range(layers - 1): self.links.append(np.zeros((nodes, nodes)))
        self.links.append(np.zeros((nodes, outputs)))

        return

# StocksAPI is the interface controller between the wallet of investiments and Alpaca API
class StocksAPI:
    def __init__(self, api_key, api_secret_key, endpoit):
        self.api = alpaca.REST(api_key, api_secret_key, endpoit)
        self.stocks = {}
        self.hist_data = {}

        self.clock(self.api.get_clock())

        if self.is_open:
            today = datetime.date.today()
            self.prev_open = pd.Timestamp(year=today.year, month=today.month, day=today.day, hour=9, minute=30, tz='US/Eastern').isoformat()
            print(self.prev_open)

        return

    # Get the market hours
    def clock(self, clock):
        self.is_open = clock.is_open
        self.next_open = clock.next_open
        self.next_close = clock.next_close
        return

    # Updates stocks
    def update(self):
        self.clock(self.api.get_clock())
        return

    # Emits a bracket order to Alpaca API
    def bracket_order(self, ticker, quantity, lifetime, take_profit, stop_loss):
        self.api.submit_order(
            symbol=ticker,
            qty=quantity,
            side='buy',
            type='market',
            order_class='bracket',
            time_in_force=lifetime,
            take_profit=take_profit,
            stop_loss=stop_loss
            )
        return

    # Gets the historical values of opening, closures, highes, lows, volume and timestamp of the specified stock
    def get_history(self, ticker, resolution, start=None, end=None, limit=None, after=None, until=None):
        barset = self.api.get_barset(ticker, resolution, limit, start, end, after, until)[ticker]
        stocks = { 'o': [], 'c': [], 'h': [], 'l': [], 'v': [], 't': [] }
        for bar in barset:
            stocks['o'].append(bar.o)
            stocks['c'].append(bar.c)
            stocks['h'].append(bar.h)
            stocks['l'].append(bar.l)
            stocks['v'].append(bar.v)
            stocks['t'].append(bar.t)
        return stocks

    # Load historical data
    def load(self, ticker, resolution, start=None, end=None, limit=None, after=None, until=None):
        stocks = self.get_history(ticker, resolution, start, end, limit, after, until)
        self.hist_data[ticker] = stocks
        return

    # Returns the current price of the specified stock. Usage on realtime mode only.
    def price(self, ticker):
        return 300

# Wallet is the class that controls the balance and stocks owned
class Wallet:
    def __init__(self, account=None):
        self.get_account(account)
        self.stocks = {}
        self.paper_trading = True

        self.tradable = []
        return

    # Updates wallet during paper or live trading
    def update(self, api):
        self.get_account(api.get_account())
        self.get_watchlists(api)
        self.get_position(self.tradable, api)
        return

    # Updates stocks prices
    def update_prices(self, stocks):
        for stock in self.stocks:
            if stock in stocks: self.stocks[stock]['current_price'] = stocks[stock].current_price
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

    # Gets the watchlist stocks on Alpaca
    def get_watchlists(self, api):
        self.watchlists = []
        watchlists = api.get_watchlists()
        for wl in watchlists:
            self.watchlists.append(api.get_watchlist(wl.id))
            watchlist = self.watchlists[-1]
            for asset in watchlist.assets: self.tradable.append(asset['symbol'])
        return

    # Gets the current positions in stocks
    def get_position(self, tickers=None, api=None):
        if tickers != None:
            for ticker in tickers:
                position = api.get_position(ticker)
                self.stocks[ticker] = {
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
            if self.stocks[ticker]['quantity'] < quantity: quantity = self.stocks[ticker]['quantity']
            self.stocks[ticker]['quantity'] -= quantity
            self.buying_power += quantity * price
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
        self.refresh_rate = 60
        return

    def mov_avg(self, arr, width, n):
        value = 0.0
        if width > n: width = n
        if width == 0: width = 1
        for i in range(width): value += arr[n - i] / width
        return value
    def is_inc(self, arr, n):
        if n > 0:
            if arr[n] > arr[n - 1]: return True
        return False
    def crossed(self, arr, _arr, i):
        if i > 0:
            diff = arr[i] - _arr[i]
            _diff = arr[i - 1] - _arr[i - 1]
            if np.sign(diff) != np.sign(_diff): return True
        return False

    # Trades using historical market data
    def local_trade(self, wallet, stocks):
        return

    # Emulates trading
    def paper_trade(self, stocks):
        if stocks.is_open:
            print('Stocks market is currently open until {}.'.format(stocks.next_close))
            wallet = Wallet(stocks.api.get_account())
            wallet.get_watchlists(stocks.api)
            while stocks.is_open:
                for ticker in wallet.tradable:
                    stocks.load(ticker, 'minute', after=stocks.prev_open)
                    if ticker not in wallet.stocks:
                        stocks.bracket_order(
                            ticker,
                            100,
                            'day',
                            {
                                'limit_price': str(stocks.hist_data[ticker]['c'][-1] * 1.05)
                            },
                            {
                                'limit_price': str(stocks.hist_data[ticker]['c'][-1] / 1.05),
                                'stop_price': str(stocks.hist_data[ticker]['c'][-1] / 1.01) 
                            })
                stocks.update()
                wallet.update(stocks.api)
                time.sleep(self.refresh_rate)
        else: print('Stocks market is currently closed! You can use local trade instead or wait utill {} to start paper-trading! :)'.format(stocks.next_open))
        return


stocks = StocksAPI('API-KEY', 'API-SECRET-KEY', 'URL-ENDPOINT')
trade = TradeAPI()

trade.paper_trade(stocks)