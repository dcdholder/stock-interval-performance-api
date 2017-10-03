from flask import Flask
from flask_restful import Resource, Api

import json

app = Flask(__name__)
api = Api(app)

class StockIntervalResource(Resource):
    def get(self, tickerSymbol):
        with open("conf.json") as data_file:
            conf = json.load(data_file)

        dataFilenameSuffix    = '-' + tickerSymbol + '-' + conf["alphavantageTimeFunction"] + '.json'
        intervalDataFilename  = 'intervalData'  + dataFilenameSuffix

        with open(intervalDataFilename) as stockIntervalDataFile:
            return json.dumps(json.load(stockIntervalDataFile))

api.add_resource(StockIntervalResource, '/<string:tickerSymbol>')

if __name__ == '__main__':
    app.run(debug=True)
