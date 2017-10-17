from datetime import datetime

import financialDataIntervals

from threading import Thread
from queue import Queue

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

        partialRefreshRequestResponse = self.partialRefreshRequestLauncher(tickerSymbols,int(env["numFragments"]),env["partialRefreshRequestUri"])

        return partialRefreshRequestResponse

    def partialRefreshRequestLauncher(self,tickerSymbols,numFragments,partialRefreshRequestUri):
        finalRequestUris = Queue()
        responseQueue    = Queue()

        for tickerSymbol in tickerSymbols:
            for i in range(numFragments):
                finalRequestUris.put(partialRefreshRequestUri + '/refresh/partial?symbol=' + tickerSymbol + '&fragment=' + str(i))

        #all requests are made concurrently, not in batches -- could set a ceiling on the number of concurrent requests in the future
        partialRequestThreads = []
        for i in range(finalRequestUris.qsize()):
            partialRequestThread = Thread(target=self.partialRefreshRequestHandler, args=(finalRequestUris,responseQueue))
            partialRequestThread.start()

            partialRequestThreads.append(partialRequestThread)

        finalRequestUris.join()

        for partialRequestThread in partialRequestThreads:
            partialRequestThread.join()

        while not responseQueue.empty():
            response = responseQueue.get()

            if response[0]>=400:
                return 'At least one partial refresh failed.', 404

        return 'Performed a full refresh on all stock data.', 204

    def partialRefreshRequestHandler(self,partialRefreshRequestUris,responseQueue):
        partialRefreshRequest = requests.get(partialRefreshRequestUris.get())

        responseQueue.put([partialRefreshRequest.status_code,partialRefreshRequest.text])

        partialRefreshRequestUris.task_done()

api.add_resource(StockIntervalPrivateResource, '/refresh/full')

if __name__ == '__main__':
    app.run(debug=True)
