import financialDataIntervals

from flask import Flask
from flask_restful import Resource, Api

import json

app = Flask(__name__)
api = Api(app)

class StockIntervalPrivateResource(Resource):
    def get(self):
        financialDataIntervals.refreshFinancialData()

        return 'Performed a full refresh on all stock data.', 204

api.add_resource(StockIntervalPrivateResource, '/refresh/full')

if __name__ == '__main__':
    app.run(debug=True)
