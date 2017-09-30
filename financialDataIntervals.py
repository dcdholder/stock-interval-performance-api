import json
import requests

def refreshFinancialData():
    with open("conf.json") as data_file:
        conf = json.load(data_file)

    #only call the alphavantage API for financial data if we haven't called it before
    try:
        with open('financialData.json', 'r') as data_file:
            financialData = json.load(data_file)

    except IOError:
        with open("credentials.json") as data_file:
            credentials = json.load(data_file)

        financialDataRequestUri = conf["alphavantageAddress"] + "/query?function=" +  \
                                  conf["alphavantageTimeFunction"] + "&symbol=" + conf["tickerSymbol"] + \
                                  "&datatype=json&apikey=" + credentials["apiKey"] + conf["alphavantageFullOrPartialOption"]

        financialDataRequest = requests.get(financialDataRequestUri)
        financialData        = financialDataRequest.json()

        with open('financialData.json', 'w') as data_file:
            json.dump(financialData, data_file)

    #digest the Alphavantage JSON format into an array of date/price hashes
    datesAndPrices = []
    for date,priceDict in financialData[conf["alphavantageJsonTimeType"]].items():
        dateAndPrice = {}
        dateAndPrice["date"]  = date
        dateAndPrice["price"] = priceDict[conf["alphavantageJsonPriceType"]]
        datesAndPrices.append(dateAndPrice)

    #iterate over all possible pairs of the above date/price dicts to generate time interval dicts
    intervalDatePriceDicts = []
    for j in range(len(datesAndPrices)):
        for i in range(len(datesAndPrices)):
            intervalDatePriceDict = {}
            #prevents reordered pairs from being recorded twice
            #also prevents entries with startDate==endDate
            if datesAndPrices[j]["date"] > datesAndPrices[i]["date"]:
                startDict = datesAndPrices[i]
                endDict   = datesAndPrices[j]

                intervalDatePriceDict["startDate"]  = startDict["date"]
                intervalDatePriceDict["endDate"]    = endDict["date"]
                intervalDatePriceDict["startPrice"] = startDict["price"]
                intervalDatePriceDict["endPrice"]   = endDict["price"]

                intervalDatePriceDicts.append(intervalDatePriceDict)

    #TODO: now dump the above to SQLAlchemy, ids enabled
