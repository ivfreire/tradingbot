import numpy as np
import matplotlib.pyplot as plt
import pandas as pandas
import alpaca_trade_api as tradeapi
# import tensorflow as tf
from threading import Thread
import json, time, importlib, math
from datetime import datetime
import trade_logic as logic

# Manages market data
class StocksData():
    def __init__(self, api):
        self.api = api
        self.hist_data = {}
        return

    def download_data(self, ticker, res, limit=None, start=None, end=None, after=None, until=None):
        barset = self.api.get_barset(ticker, timeframe=res, limit=limit, start=start, end=end, after=after, until=until)
        stocks = { 'o': [], 'c': [], 'h': [], 'l': [], 'v': [], 't': [] }
        for bar in barset[ticker]:
            stocks['o'].append(bar.o)
            stocks['c'].append(bar.c)
            stocks['h'].append(bar.h)
            stocks['l'].append(bar.l)
            stocks['v'].append(bar.v)
            stocks['t'].append(bar.t)
        return stocks

    def load_data(self, ticker, res, limit=None, start=None, end=None, after=None, until=None):
        self.hist_data[ticker] = self.download_data(ticker, res, limit=limit, start=start, end=end, after=after, until=until)
        return

    def update_data(self, ticker, res, after):
        stocks = self.download_data(ticker, res, after=after)
        self.hist_data[ticker]['o'] += stocks['o']
        self.hist_data[ticker]['c'] += stocks['c']
        self.hist_data[ticker]['h'] += stocks['h']
        self.hist_data[ticker]['l'] += stocks['l']
        self.hist_data[ticker]['v'] += stocks['v']
        self.hist_data[ticker]['t'] += stocks['t']
        return

# Manages local trading emulation
class LocalTrader():
    def __init__(self, api, tradables):
        self.api = api
        self.tradables = tradables
        self.stocks = StocksData(api)
        self.orders = []
        self.create_wallet(1000.0)
        return

     # Initializes wallet
    def create_wallet(self, buying_power):
        self.buying_power = buying_power
        self.equity = buying_power
        self.portfolio = {}
        return

    # Loads market data from Alpaca
    def load_data(self, limit=None, start=None, end=None, after=None, until=None):
        for ticker in self.tradables:
            self.stocks.load_data(ticker, '1Min', limit=limit)
        return


    def get_equity(self):
        equity = 0.0
        for stock in self.portfolio:
            equity += self.portfolio[stock]['quantity'] * self.portfolio[stock]['current_price']
        return equity

    def process_order(self, type, ticker, price, quantity):
        if type == 'buy':
            if self.buying_power >= price * quantity:
                self.buying_power -= price * quantity
                if ticker in self.portfolio:
                    self.portfolio[ticker]['avg_entry_price'] = (self.portfolio[ticker]['avg_entry_price'] * self.portfolio[ticker]['quantity'] + price * quantity) / (self.portfolio[ticker]['quantity'] + quantity)
                    self.portfolio[ticker]['quantity'] += quantity
                    self.portfolio[ticker]['current_price'] = price
                else:
                    self.portfolio[ticker] = {
                        'avg_entry_price': price,
                        'quantity': quantity,
                        'current_price': price
                    }
        elif type == 'sell':
            if ticker in self.portfolio:
                if self.portfolio[ticker]['quantity'] >= quantity:
                    self.buying_power += price * quantity
                    self.portfolio[ticker]['quantity'] -= quantity
                    self.portfolio[ticker]['current_price'] = price
        return

    def bracket_order(self, ticker, price, quantity, take_profit, stop_loss):
        exec_id = len(self.orders)
        self.orders.append(['buy', ticker, price, quantity, 'instant', False, None, exec_id])
        self.orders.append(['sell', ticker, take_profit['limit_price'], quantity, 'conditional', False, 'profit', exec_id + 1])
        self.orders.append(['sell', ticker, stop_loss['limit_price'], quantity, 'conditional', False, 'loss', exec_id + 1])
        return

    def execute_order(self, order):
        self.process_order(order[0], order[1], order[2], order[3])
        for _order in self.orders:
            if _order[7] == order[7]: self.orders.remove(_order)
        order[5] = True
        return

    def execute_orders(self, t):
        for order in self.orders:
            if order[5] == False:
                price = self.stocks.hist_data[order[1]]['c'][t]
                if order[4] == 'instant': self.execute_order(order)
                elif order[4] == 'conditional':
                    if order[6] == 'profit':
                        if price >= order[2]: self.execute_order(order)
                    if order[6] == 'loss':
                        if price <= order[2]: self.execute_order(order)
        return


    def trade(self):
        for t in range(len(self.stocks.hist_data[self.tradables[0]]['t'])):
            for ticker in self.tradables:
                price = self.stocks.hist_data[ticker]['c'][t]
                if self.buying_power > 0:
                    self.bracket_order(
                        ticker,
                        price,
                        self.buying_power / (len(self.tradables) * price),
                        take_profit={
                            'limit_price': price * 1.001
                        },
                        stop_loss={
                            'stop_price': price * 0.99,
                            'limit_price': price * 0.98
                        }
                    )
            self.execute_orders(t)
        return

    def result(self):
        return self.get_equity()

# Emulates using real-time market data
class PaperTrader():
    def __init__(self, api, tradables):
        self.api = api
        self.tradables = tradables
        self.portfolio = {}
        self.stocks = StocksData(api)
        self.sync()
        return

    def sync(self):
        self.sync_account()
        self.sync_clock()
        self.sync_equity()
        return

    def sync_account(self):
        account = self.api.get_account()
        self.buying_power = float(account.buying_power)
        self.equity = float(account.equity)
        self.currency = account.currency
        return

    def sync_clock(self):
        clock = self.api.get_clock()
        self.is_open = clock.is_open
        self.next_open = clock.next_open
        self.next_close = clock.next_close
        today = datetime.today()
        self.prev_open = datetime(year=today.year, month=today.month, day=today.day, hour=9, minute=30)
        return

    def sync_equity(self):
        for ticker in self.tradables:
            try:
                position = self.api.get_position(ticker)
                self.portfolio[ticker] = {}
                self.portfolio[ticker]['avg_entry_price'] = float(position.avg_entry_price)
                self.portfolio[ticker]['current_price'] = float(position.current_price)
                self.portfolio[ticker]['quantity'] = float(position.qty)
            except Exception as e:
                print('Exception: {}'.format(e))
        return

    def trade(self):
        for ticker in self.tradables: self.stocks.load_data(ticker, '1Min', after=self.prev_open)

        while self.is_open:
            for ticker in self.tradables:
                self.stocks.update_data(ticker, '1Min', after=self.stocks.hist_data[ticker]['t'][-1].isoformat())
                price = self.stocks.hist_data[ticker]['c'][-1]
                if self.buying_power > 0:
                    qty = math.floor(self.buying_power / (len(self.tradables) * price))
                    if qty > 0:
                        try:
                            self.api.submit_order(
                                symbol=ticker,
                                qty=qty,
                                side='buy',
                                type='market',
                                time_in_force='gtc',
                                take_profit={
                                    'limit_price': price * 1.01
                                },
                                stop_loss={
                                    'stop_price': price * 0.99,
                                    'limit_price': price * 0.98
                                }
                            )
                            print('Bought {} stocks of {} for {} each.'.format(qty, ticker, price))
                        except Exception as e:
                            print('Exception: {}'.format(e))
            self.sync()
            print('Equity: {}'.format(self.equity))
            time.sleep(60)
        return

# Controls bot's trading logic
class TradingController():
    def __init__(self, api, tradables):
        self.api = api
        self.tradables = tradables
        self.sync()
        return

    def sync(self):
        self.is_open = self.api.get_clock().is_open
        return

    def trade(self):
        try:
            if self.is_open:
                paper_trade = PaperTrader(self.api, self.tradables)
                paper_trade.trade()
            else:
                local_trade = LocalTrader(self.api, self.tradables)
                local_trade.load_data(limit=350)
                local_trade.trade()
                print(local_trade.result())
        except Exception as e:
            print('Exception: {}'.format(e))
        return

# Main controller
class Controller():
    def __init__(self):
        if self.load_config('./config.json'):
            self.api = tradeapi.REST(self.config['auth']['api_key'], self.config['auth']['secret_key'], self.config['auth']['endpoint'])
            print('Logged to Alpaca successfully!')
            self.tradectl = TradingController(self.api, self.config['tradables'])
            self.tradectl.trade()
        else: print('Bot is not setup properly.')
        return

    def load_config(self, path):
        with open(path, 'r') as file:
            try:
                self.config = json.loads(file.read())
                return True
            except Exception as e:
                print('Exception: {}'.format(e))
                return False


controller = Controller()