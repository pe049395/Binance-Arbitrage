import json
import websocket
from typing import List

from arbitrage_trader import Arbitrageur, BTCUSDT_LISTEN_KEY, BTCBUSD_LISTEN_KEY


class BinanceWebsocketConnector(Arbitrageur):
    def __init__(self, symbols: List[str]):
        super().__init__()

        self.symbols = symbols
        self.ws = websocket.WebSocketApp(
            "wss://stream.binance.com:9443/ws",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )
        websocket.enableTrace(False)

    def on_open(self, ws):
        print("WebSocket connection opened")
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@bookTicker" for symbol in self.symbols] + [
                "busdusdt@ticker",
                BTCUSDT_LISTEN_KEY,
                BTCBUSD_LISTEN_KEY,
            ],
            "id": 1,
        }
        self.ws.send(json.dumps(subscribe_message))

    def on_error(self, ws, message):
        print(f"WebSocket error: {message}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")

    def on_message(self, ws, message):
        self.message_handler(message)


def main():
    symbols = ["BTCUSDT", "BTCBUSD"]
    connector = BinanceWebsocketConnector(symbols)
    connector.ws.run_forever()


if __name__ == "__main__":
    main()
