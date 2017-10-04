from flask import Flask
from flask_restful import Resource, Api

import json

app = Flask(__name__)
api = Api(app)

class StockIntervalPublicResource(Resource):
    def get(self, tickerSymbol):
        with open("conf.json") as data_file:
            conf = json.load(data_file)

        with open("tickerSymbols.json") as data_file:
            tickerSymbols = json.load(data_file)

        if tickerSymbol in tickerSymbols:
            dataFilenamePrefix   = conf['filenamePrefix']
            dataFilenameSuffix   = '-' + tickerSymbol + '-' + conf["alphavantageTimeFunction"] + '.json'
            intervalDataFilename = dataFilenamePrefix + 'intervalData'  + dataFilenameSuffix

            try:
                with open(intervalDataFilename) as stockIntervalDataFile:
                    return json.load(stockIntervalDataFile), 200
            except IOError:
                return tickerSymbol + ' data is listed as available, but could not be found.', 404
        else:
            return 'No data is available for ' + tickerSymbol + '.', 404

api.add_resource(StockIntervalPublicResource, '/intervals/<string:tickerSymbol>')

if __name__ == '__main__':
    app.run(debug=True)
