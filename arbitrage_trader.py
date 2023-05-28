import time
import datetime
import json
import websocket

from binance_client import client, margin_send_market_buy_order, margin_send_market_sell_order

BTCUSDT_LISTEN_KEY = client.new_isolated_margin_listen_key("BTCUSDT")["listenKey"]
BTCBUSD_LISTEN_KEY = client.new_isolated_margin_listen_key("BTCBUSD")["listenKey"]

class Arbitrageur:
    def __init__(self):
        self.THRESHOLD = 1.2
        self.QTY = 0.001
        self.BTCUSDT_BORROWED = 0.025
        self.BTCBUSD_BORROWED = 0.025

	self.busdusdt = 1

        self.btcusdt_bid = None
        self.btcusdt_ask = None
        self.btcbusd_bid = None
        self.btcbusd_ask = None

        self.btcusdt_trade = None
        self.btcbusd_trade = None
        self.btcusdt_trade_real = None
        self.btcbusd_trade_real = None

        self.btcusdt_bid_amount = None
        self.btcusdt_ask_amount = None
        self.btcbusd_bid_amount = None
        self.btcbusd_ask_amount = None

        self.ready = False

        self.buying_btcusdt = False
        self.selling_btcusdt = False

	self.last_traded_time = 0

    def message_handler(self, message):
        message = json.loads(message)

        if "e" not in message.keys():
            if message["s"] == "BTCUSDT":
                self.btcusdt_bid = float(message['b'])
                self.btcusdt_ask = float(message['a'])
            elif message["s"] == "BTCBUSD":
                self.btcbusd_bid = float(message['b'])
                self.btcbusd_ask = float(message['a'])

            if not self.ready:
                if self.btcusdt_bid is not None and self.btcusdt_ask is not None and self.btcbusd_bid is not None and self.btcbusd_ask is not None:
                    self.ready = True

            else:
                buytime = False
                selltime = False

		buygap = self.btcbusd_bid * self.busdusdt - self.btcusdt_ask
                if buygap >= self.THRESHOLD:
                    buytime = True

                sellgap = self.btcbusd_ask * self.busdusdt - self.btcusdt_bid
                if sellgap <= -self.THRESHOLD:
                    selltime = True

                if buytime and selltime:
                    if buygap > -sellgap:
                        selltime = False
                    else:
                        buytime = False

                now = time.time()

                if buytime:
                    if now > self.last_traded_time + 10 and not self.buying_btcusdt:
                        qty = round(self.QTY * 2, 5) if self.selling_btcusdt else self.QTY
                        margin_send_market_buy_order("BTCUSDT", qty)
                        margin_send_market_sell_order("BTCBUSD", qty)

                        self.btcusdt_trade = self.btcusdt_ask
                        self.btcbusd_trade = self.btcbusd_bid
                        self.buying_btcusdt = True
                        self.selling_btcusdt = False
                        self.last_traded_time = now

                elif selltime:
                    if now > self.last_traded_time + 10 and not self.selling_btcusdt:
                        qty = round(self.QTY * 2, 5) if self.buying_btcusdt else self.QTY
                        margin_send_market_sell_order("BTCUSDT", qty)
                        margin_send_market_buy_order("BTCBUSD", qty)

                        self.btcusdt_trade = self.btcusdt_bid
                        self.btcbusd_trade = self.btcbusd_ask
                        self.selling_btcusdt = True
                        self.buying_btcusdt = False
                        self.last_traded_time = now

        elif message['e'] == "24hrTicker":
            self.update_busdusdt_price(message)

        elif message['e'] == "executionReport":
            self.update_trade(message)

        elif message['e'] == "outboundAccountPosition":
            self.update_account(message)

    def update_busdusdt_price(self, message):
        bid = float(message['b'])
        ask = float(message['a'])
        self.busdusdt = (bid + ask) / 2

    def update_trade_real(self, message):
        symbol = message['s']
        trade_type = message['x']
        trade_price = float(message['L'])
        
        if symbol == "BTCUSDT" and trade_type == "TRADE":
            self.btcusdt_trade_real = trade_price
        elif symbol == "BTCBUSD" and trade_type == "TRADE":
            self.btcbusd_trade_real = trade_price

    def update_account(self, message):
        update_time = datetime.datetime.fromtimestamp(message['u'] // 1000 + 32400).strftime('%Y-%m-%d %H:%M:%S')
        
        btcusdt_midprice = (self.btcusdt_ask + self.btcusdt_bid) / 2
        btcbusd_midprice = (self.btcbusd_ask + self.btcbusd_bid) / 2

        for account in message['B']:
            if account['a'] == "BTC":
                account_btc = float(account['f']) + float(account['l'])

            elif account['a'] == "USDT":
                account_usdt = float(account['f']) + float(account['l'])
                self.account_btcusdt = (account_btc - self.BTCUSDT_BORROWED) * btcusdt_midprice + account_usdt

            elif account['a'] == "BUSD":
                account_busd = float(account['f']) + float(account['l'])
                self.account_btcbusd = (account_btc - self.BTCBUSD_BORROWED) * btcbusd_midprice + account_busd

        try:
            print(f"[{update_time}] {round(self.account_btcusdt + self.account_btcbusd, 2)}")
        except:
            pass
