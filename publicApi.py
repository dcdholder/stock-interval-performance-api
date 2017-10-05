import financialDataIntervals

from flask import Flask
from flask_restful import Resource, Api

import json

app = Flask(__name__)
api = Api(app)

class StockIntervalPublicResource(Resource):
    def get(self, timeGranularity, tickerSymbol):
        with open("conf.json") as data_file:
            conf = json.load(data_file)

        with open("tickerSymbols.json") as data_file:
            tickerSymbols = json.load(data_file)

        if tickerSymbol in tickerSymbols:
            [resolvedStartDateString, resolvedEndDateString] = financialDataIntervals.resolveToDateRange(startDateString,endDateString,timeGranularity)

            try:
                return financialDataIntervals.getExistingIntervalData(tickerSymbol,resolvedStartDateString,resolvedEndDateString)
            except IOError:
                return tickerSymbol + ' data for the range ' + startDateString + 'to' + endDateString + ' could not be found.', 404
        else:
            return 'No data is available for ' + tickerSymbol + '.', 404

api.add_resource(StockIntervalPublicResource, '/intervals/<string:timeGranularity>/<string:tickerSymbol>')

if __name__ == '__main__':
    app.run(debug=True)
