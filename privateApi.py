import financialDataIntervals

from threading import Thread
import requests

from flask import Flask
from flask_restful import Resource, Api

import json

app = Flask(__name__)
api = Api(app)

class StockIntervalPrivateResource(Resource):
    def get(self):
        with open("env.json") as environmentFile:
            env = json.load(environmentFile)

        with open("tickerSymbols.json") as tickerSymbolsFile:
            tickerSymbols = json.load(tickerSymbolsFile)

        for tickerSymbol in tickerSymbols:
            for i in range(int(env["numFragments"])):
                finalRequestUri = env["partialRefreshRequestUri"] + '/refresh/partial?symbol=' + tickerSymbol + '&fragment=' + str(i)
                refreshRequest = requests.get(finalRequestUri)

                if refreshRequest.status_code>=400:
                    return 'At least one partial refresh failed.', 404

        return 'Performed a full refresh on all stock data.', 204

api.add_resource(StockIntervalPrivateResource, '/refresh/full')

if __name__ == '__main__':
    app.run(debug=True)
