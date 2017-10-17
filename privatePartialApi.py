import financialDataIntervals

from threading import Thread
import requests
import datetime

from flask import Flask
from flask_restful import Resource, Api, reqparse

import json

app = Flask(__name__)
api = Api(app)

requestParser = reqparse.RequestParser()

requestParser.add_argument('symbol',   dest='symbol',   type=str, location='args', required=True, help='A ticker symbol is required.')
requestParser.add_argument('fragment', dest='fragment', type=str, location='args', required=True, help='A fragment number is required.')

class StockIntervalPrivatePartialResource(Resource):
    def get(self):
        with open("env.json") as environmentFile:
            env = json.load(environmentFile)

        with open("tickerSymbols.json") as tickerSymbolsFile:
            tickerSymbols = json.load(tickerSymbolsFile)

        args = requestParser.parse_args()

        try:
            financialDataIntervals.refreshIntervalData(symbol=args.symbol,numFragments=int(env["numFragments"]),fragmentIndex=int(args.fragment))
        except:
            return 'Partial request failed (symbol: ' + args.symbol + ', fragment: ' + args.fragment + ').', 404

        return 'Performed a partial refresh on stock data (symbol: ' + args.symbol + ', fragment: ' + args.fragment + ').', 204

api.add_resource(StockIntervalPrivatePartialResource, '/refresh/partial')

if __name__ == '__main__':
    app.run(debug=True,threaded=True,port=5001)
