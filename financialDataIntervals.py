import json
import requests

from datetime import datetime
import operator

def refreshFinancialData():
    with open("conf.json") as data_file:
        conf = json.load(data_file)

    with open("tickerSymbols.json") as data_file:
        tickerSymbols = json.load(data_file)

    for tickerSymbol in tickerSymbols:
        dataFilenameSuffix = '-' + tickerSymbol + '-' + conf["alphavantageTimeFunction"] + '.json'

        financialDataFilename = 'financialData' + dataFilenameSuffix
        intervalDataFilename  = 'intervalData'  + dataFilenameSuffix

        #only call the alphavantage API for financial data if we haven't called it before
        try:
            with open(financialDataFilename) as data_file:
                financialData = json.load(data_file)

        except IOError:
            with open("credentials.json") as data_file:
                credentials = json.load(data_file)

            financialDataRequestUri = conf["alphavantageAddress"] + "/query?function=" +  \
                                      conf["alphavantageTimeFunction"] + "&symbol=" + conf["tickerSymbol"] + \
                                      "&datatype=json&apikey=" + credentials["apiKey"] + conf["alphavantageFullOrPartialOption"]

            financialDataRequest = requests.get(financialDataRequestUri)
            financialData        = financialDataRequest.json()

            with open(financialDataFilename, 'w') as data_file:
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

        #now we create a dict keyed by interval length
        dateFormat = "%Y-%m-%d"

        datePriceDictsByIntervalLength = {}
        for invervalDatePriceDict in intervalDatePriceDicts:
            endDate   = datetime.strptime(invervalDatePriceDict["endDate"], dateFormat)
            startDate = datetime.strptime(invervalDatePriceDict["startDate"], dateFormat)

            intervalLength = (endDate-startDate).days

            #if intervalLength==3109:
            #    print(startDate)
            #    print(endDate)

            if not intervalLength in datePriceDictsByIntervalLength:
                datePriceDictsByIntervalLength[intervalLength] = []

            datePriceDictsByIntervalLength[intervalLength].append(invervalDatePriceDict)

        #grab the price change percentage (positive/negative) for the elements in each interval, copy to new arrays
        priceDeltaPercentageByIntervalLength = {}
        for intervalLength, datePriceDicts in datePriceDictsByIntervalLength.items():
            priceDeltaPercentageByIntervalLength[intervalLength] = []
            for datePriceDict in datePriceDicts:
                priceDeltaPercentage = (float(datePriceDict["endPrice"])-float(datePriceDict["startPrice"]))/float(datePriceDict["startPrice"])

                priceDeltaPercentageByIntervalLength[intervalLength].append(priceDeltaPercentage)

        #sort the new arrays
        for intervalLength, priceDeltaPercentageList in priceDeltaPercentageByIntervalLength.items():
            priceDeltaPercentageByIntervalLength[intervalLength].sort()

        #grab the best, worst of each interval
        intervalMetrics = {}
        for intervalLength, priceDeltaPercentageList in priceDeltaPercentageByIntervalLength.items():
            intervalMetrics[intervalLength]          = {}
            intervalMetrics[intervalLength]["worst"] = priceDeltaPercentageList[0]
            intervalMetrics[intervalLength]["best"]  = priceDeltaPercentageList[len(priceDeltaPercentageList)-1]

        with open(intervalDataFilename, 'w') as data_file:
            json.dump(intervalMetrics,data_file)

        #print(intervalMetrics)
