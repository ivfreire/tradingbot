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
        try:
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
        except Exception as e:
            print('Exception: {}'.format(e))
        return

    def load_data(self, ticker, res, limit=None, start=None, end=None, after=None, until=None):
        self.hist_data[ticker] = self.download_data(ticker, res, limit=None, start=None, end=None, after=None, until=None)
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

'''
    ORDER(
        type,
        limit_price,
        execution
    )
'''
# Controls bot's trading logic
class TradingController(Thread):
    def __init__(self, api, tradables):
        super(TradingController, self).__init__()
        self.api = api
        self.tradables = tradables
        self.portfolio = {}
        self.orders = []
        self.stocks = StocksData(api)
        self.local_trading = False
        self.sync()
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

    def sync(self):
        self.sync_account()
        self.sync_clock()
        self.sync_equity()
        return

    def local_order(self, type, ticker, price, quantity):
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

    '''
        take_profit
            limit_price
        stop_loss
            stop_price
            limit_price
    '''
    def local_bracket(self, ticker, price, quantity, specs):
        exec_id = len(self.orders)
        self.orders.append(['buy', ticker, price, quantity, 'instant', False, None, exec_id])
        self.orders.append(['sell', ticker, specs['take_profit']['limit_price'], quantity, 'conditional', False, 'profit', exec_id + 1])
        self.orders.append(['sell', ticker, specs['stop_loss']['limit_price'], quantity, 'conditional', False, 'loss', exec_id + 1])
        return

    def execute_orders(self, t):
        for order in self.orders:
            if order[5] == False:
                if order[4] == 'instant':
                    self.local_order(order[0], order[1], order[2], order[3])
                    order[5] = True
                elif order[4] == 'conditional':
                    if order[6] == 'loss':
                        if self.stocks.hist_data[order[1]]['c'][t] <= order[2]:
                            self.local_order(order[0], order[1], order[2], order[3])
                            order[5] = True
                    if order[6] == 'profit':
                        if self.stocks.hist_data[order[1]]['c'][t] >= order[2]:
                            self.local_order(order[0], order[1], order[2], order[3])
                            order[5] = True
                    '''for i in range(len(self.orders)):
                        if order[7] == self.orders[i][7]: print(order[7])'''

        return

    def paper_trade(self):
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
                                    'limit_price': price * 1.005
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
            time.sleep(60)

        return

    def local_trade(self):
        self.local_trading = True

        limit = 350
        for ticker in self.tradables: self.stocks.load_data(ticker, '1Min', limit=limit)

        for t in range(len(self.stocks.hist_data[self.tradables[0]]['t'])):
            for ticker in self.tradables:
                price = self.stocks.hist_data[ticker]['c'][t]
                if self.buying_power > 0:
                    self.local_bracket(
                        ticker,
                        price,
                        self.buying_power / (len(self.tradables) * price),
                        {
                            'take_profit': {
                                'limit_price': price * 1.01
                            },
                            'stop_loss': {
                                'stop_price': price * 0.99,
                                'limit_price': price * 0.98
                            }
                        }
                    )
            self.execute_orders(t)
            print(self.orders)
        return

    def run(self):
        while self.is_alive:
            try:
                if self.is_open:
                    self.paper_trade()
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
            self.tradectl.start()
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

    def close(self):
        self.tradectl.join()

controller = Controller()
controller.close()