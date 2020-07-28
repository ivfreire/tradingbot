import numpy as np
import matplotlib.pyplot as plt
import pandas as pandas
import alpaca_trade_api as tradeapi
# import tensorflow as tf
from threading import Thread
import json, time, importlib, math
from datetime import datetime
import trade_logic as logic
import utils

# Manages market data
class StocksData():
    def __init__(self, api):
        self.api = api
        self.hist_data = {}
        return

    def load_data(self, symbols, timeframe='1Min', limit=None, start=None, end=None, after=None, until=None):
        self.hist_data = self.api.get_barset(symbols=symbols, timeframe=timeframe, limit=limit, start=start, end=end, after=after, until=until) 
        return

    def update_data(self, symbol, timeframe, after):
        if symbol in self.hist_data:
            new_data = self.api.get_barset(symbols=symbol, timeframe=timeframe, after=after)
            self.hist_data[symbol].append(new_data)
        else:
            print('Error! Please, first load the market data for {}.'.format(symbol))
        return

    def data_period(self):
        periods = []
        for symbol in self.hist_data: periods.append(len(self.hist_data[symbol]))
        return max(periods)

    def get_bar(self, symbol, t):
        if symbol in self.hist_data:
            if t < len(self.hist_data[symbol]):
                return self.hist_data[symbol][t]
        return False

# Manages local trading emulation
class LocalTrader():
    def __init__(self, api, tradables):
        self.api = api
        self.tradables = tradables
        self.stocks = StocksData(api)
        self.orders = []
        return

     # Initializes wallet
    def create_wallet(self, buying_power):
        self.buying_power = buying_power
        self.portfolio = {}
        self.hist_equity = []
        return

    # Loads market data from Alpaca
    def load_data(self, timeframe=None, limit=None, start=None, end=None, after=None, until=None):
        self.stocks.load_data(self.tradables, timeframe, limit, start, end, after, until)
        return


    def set_tradables(self, tradables):
        self.tradables = tradables
        return

    def get_equity(self):
        equity = self.buying_power
        for stock in self.portfolio:
            equity += self.portfolio[stock]['quantity'] * self.portfolio[stock]['current_price']
        return equity

    def show_portfolio(self):
        print('Symbol\tQuantity\tCurrent Price\tPosition')
        for symbol in self.portfolio:
            print('{}\t{}\t\t{}\t\t{}'.format(symbol, self.portfolio[symbol]['quantity'], self.portfolio[symbol]['current_price'], self.portfolio[symbol]['quantity'] * self.portfolio[symbol]['current_price']))
        print('BuyPow\t{}'.format(self.buying_power))
        return

    def update_portfolio_prices(self, t):
        for symbol in self.portfolio:
            if symbol in self.stocks.hist_data:
                if t < len(self.stocks.hist_data[symbol]):
                    self.portfolio[symbol]['current_price'] = self.stocks.hist_data[symbol][t].c
        return


    def process_order(self, type, symbol, price, quantity):
        if type == 'buy':
            if self.buying_power >= price * quantity:
                self.buying_power -= price * quantity
                if symbol in self.portfolio:
                    self.portfolio[symbol]['avg_entry_price'] = (self.portfolio[symbol]['avg_entry_price'] * self.portfolio[symbol]['quantity'] + price * quantity) / (self.portfolio[symbol]['quantity'] + quantity)
                    self.portfolio[symbol]['quantity'] += quantity
                    self.portfolio[symbol]['current_price'] = price
                else:
                    self.portfolio[symbol] = {
                        'avg_entry_price': price,
                        'quantity': quantity,
                        'current_price': price
                    }
        elif type == 'sell':
            if symbol in self.portfolio:
                if self.portfolio[symbol]['quantity'] >= quantity:
                    self.buying_power += price * quantity
                    self.portfolio[symbol]['quantity'] -= quantity
                    self.portfolio[symbol]['current_price'] = price
        return

    def bracket_order(self, symbol, price, quantity, take_profit, stop_loss):
        exec_id = len(self.orders)
        self.orders.append(['buy', symbol, price, quantity, 'instant', False, None, exec_id])
        self.orders.append(['sell', symbol, take_profit['limit_price'], quantity, 'conditional', False, 'profit', exec_id + 1])
        self.orders.append(['sell', symbol, stop_loss['limit_price'], quantity, 'conditional', False, 'loss', exec_id + 1])
        return

    def execute_order(self, order):
        self.process_order(order[0], order[1], order[2], order[3])
        for _order in self.orders:
            if _order[7] == order[7] and _order != order: self.orders.remove(_order)
        order[5] = True
        return

    def execute_orders(self, t):
        for order in self.orders:
            if order[5] == False:
                bar = self.stocks.get_bar(order[1], t)
                if bar:
                    price = bar.c
                    if order[4] == 'instant': self.execute_order(order)
                    elif order[4] == 'conditional':
                        if order[6] == 'profit':
                            if price >= order[2]: self.execute_order(order)
                        if order[6] == 'loss':
                            if price <= order[2]: self.execute_order(order)
        return

    def sell_all_positions(self):
        for symbol in self.portfolio:
            stock = self.portfolio[symbol]
            if stock['quantity'] > 0:
                self.execute_order(['sell', symbol, stock['current_price'], stock['quantity'], 'instant', False, None, len(self.orders)])
        return


    def trade(self):
        for t in range(self.stocks.data_period()):
            acts = logic.braket_trading(self.buying_power, self.portfolio, self.stocks, t, (1.04, 0.98))
            for act in acts: self.bracket_order(act['symbol'], act['price'], act['quantity'], take_profit=act['take_profit'], stop_loss=act['stop_loss'])
            self.execute_orders(t)
            self.update_portfolio_prices(t)
            self.hist_equity.append(self.get_equity())
        self.sell_all_positions()
        return


    def result(self):
        return self.get_equity()

# Emulates using real-time market data
class PaperTrader():
    def __init__(self, api, tradables, refresh_rate=60):
        self.api = api
        self.tradables = tradables
        self.refresh_rate = refresh_rate
        self.portfolio = {}
        self.stocks = StocksData(api)
        self.sync()
        self.load()
        return

    def load(self):
        if self.is_open:
            self.stocks.load_data(self.tradables, '1Min', after=self.prev_open)
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
        for position in self.api.list_positions():
            self.portfolio[position.symbol] = {}
            self.portfolio[position.symbol]['avg_entry_price'] = float(position.avg_entry_price)
            self.portfolio[position.symbol]['current_price'] = float(position.current_price)
            self.portfolio[position.symbol]['quantity'] = float(position.qty)
        return

    def trade(self):
        while self.is_open:
            importlib.reload(logic)
            acts = logic.braket_trading(self.buying_power, self.portfolio, self.stocks, -1, (1.02, 0.98))
            for act in acts:
                try:
                    self.api.submit_order(symbol=act['symbol'], qty=act['quantity'], side='buy', type='market', time_in_force='gtc', order_class='bracket', take_profit=act['take_profit'], stop_loss=act['stop_loss'])
                    print('Bought {} stocks of {} for {}'.format(act['quantity'], act['symbol'], act['price']))
                except Exception as e: print('Exception on buying: {}'.format(e))
            self.sync()
            utils.log('{}\t{}'.format(datetime.now().isoformat(), self.equity))
            time.sleep(self.refresh_rate)
        return

# Controls bot's trading logic
class TradingController():
    def __init__(self, api, tradables):
        self.api = api
        self.tradables = tradables
        self.sync_clock()
        return

    def sync_clock(self):
        self.is_open = self.api.get_clock().is_open
        return

    def paper_trade(self):
        utils.log('Market is open')
        utils.log('Started paper trade.')
        paper_trade = PaperTrader(self.api, self.tradables)
        paper_trade.refresh_rate = 1
        paper_trade.trade()
        return

    def local_trade(self):
        utils.log('Market is currently closed.')
        utils.log('Started local trade.')
        local_trade = LocalTrader(self.api, self.tradables)
        local_trade.create_wallet(1000)
        for month in range(1, 13, 1):
            for day in range(1, 31):
                try:
                    local_trade.load_data(
                        timeframe='1Min',
                        start=datetime(year=2019, month=month, day=day, hour=9, minute=30).isoformat() + '-04:00',
                        end=datetime(year=2019, month=month, day=day, hour=16).isoformat() + '-04:00')
                    local_trade.trade()
                    print('{}.{}:\t${:.2f}'.format(month, day, local_trade.get_equity()))
                except Exception as e:
                    print('Exception: {}'.format(e))
        return

    # Trading loop
    def trade(self):
        while True:
            if self.is_open: self.paper_trade()
            else: self.local_trade()
            self.sync_clock()
            time.sleep(180)
        return

# Main controller
class Controller():
    def __init__(self):
        if self.load_config('./config.json'):
            self.api = tradeapi.REST(self.config['auth']['api_key'], self.config['auth']['secret_key'], self.config['auth']['endpoint'])
            utils.log('Logged to Alpaca successfully!')
            self.tradectl = TradingController(self.api, self.config['tradables'])
            self.tradectl.trade()
        else: utils.log('Bot is not setup properly.')
        return

    def load_config(self, path):
        with open(path, 'r') as file:
            try:
                self.config = json.loads(file.read())
                return True
            except Exception as e:
                utils.log('Exception: {}'.format(e))
                return False


controller = Controller()