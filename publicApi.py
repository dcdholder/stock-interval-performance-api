import financialDataIntervals

from flask import Flask
from flask_restful import Resource, Api, marshal_with, reqparse

import json

app = Flask(__name__)
api = Api(app)

requestParser = reqparse.RequestParser()

requestParser.add_argument('symbol',     dest='symbol',     type=str, location='args', required=True, help='A ticker symbol is required.')
requestParser.add_argument('startdate',  dest='startdate',  type=str, location='args', required=True, help='A start date is required.')
requestParser.add_argument('enddate',    dest='enddate',    type=str, location='args', required=True, help='An end date is required.')
requestParser.add_argument('resolution', dest='resolution', type=str, location='args', required=False)

class StockIntervalPublicResource(Resource):
    def get(self):
        args = requestParser.parse_args()

        with open("conf.json") as data_file:
            conf = json.load(data_file)

        with open("tickerSymbols.json") as data_file:
            tickerSymbols = json.load(data_file)

        if args.symbol in tickerSymbols:
            resolution="daily"
            if args.resolution!=None:
                resolution=args.resolution

            try:
                return financialDataIntervals.getIntervalDataFromDateRange(args.symbol,args.startdate,args.enddate,resolution), 200
            except Exception as e:
                return str(e), 404
        else:
            return 'No data is available for ' + tickerSymbol + '.', 404

api.add_resource(StockIntervalPublicResource, '/intervals')

if __name__ == '__main__':
    app.run(debug=True)
