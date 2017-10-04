import os
import lib.cloudstorage as gcs
from lib.google.appengine.api import app_identity

import json
import requests

from datetime import datetime
import operator

def stockDataFilename(dataType,tickerSymbol):
    with open("conf.json") as configurationFile:
        conf = json.load(configurationFile)

    return conf["filenamePrefix"] + dataType + '-' + tickerSymbol + '-' + conf["alphavantageCompactOrFull"] + '-' + conf["alphavantageTimeFunction"] + '.json'

def getExistingIntervalData(tickerSymbol):
    with open("env.json") as environmentFile:
        env = json.load(environmentFile)["env"]

    intervalDataFilename = stockDataFilename('intervals',tickerSymbol)

    if env=='local':
        with open(intervalDataFilename) as intervalDataFile:
            return json.load(intervalDataFile)
    elif env=='gcp':
        os.environ.get('BUCKET_NAME',app_identity.get_default_gcs_bucket_name())

        intervalDataFile = gcs.open(intervalDataFilename)
        intervalData     = json.load(intervalDataFile)

        intervalDataFile.close()

        return intervalData

def refreshrawData():
    with open("env.json") as environmentFile:
        env = json.load(environmentFile)["env"]

    with open("conf.json") as configurationFile:
        conf = json.load(configurationFile)

    with open("tickerSymbols.json") as tickerSymbolsFile:
        tickerSymbols = json.load(tickerSymbolsFile)

    for tickerSymbol in tickerSymbols:
        rawDataFilename = stockDataFilename('raw',tickerSymbol)
        intervalDataFilename  = stockDataFilename('intervals',tickerSymbol)

        #only call the alphavantage API for financial data if we haven't called it before
        try:
            if env=='local':
                with open(rawDataFilename) as rawDataFile:
                    rawData = json.load(rawDataFile)
            elif env=='gcp':
                os.environ.get('BUCKET_NAME',app_identity.get_default_gcs_bucket_name())

                rawDataFile = gcs.open(rawDataFilename)
                rawData     = json.load(rawDataFile)

                rawDataFile.close()

        except IOError:
            with open("credentials.json") as credentialsFile:
                credentials = json.load(credentialsFile)

            rawDataRequestUri = conf["alphavantageAddress"] + "/query?function=" +  \
                                      conf["alphavantageTimeFunction"] + "&symbol=" + tickerSymbol + \
                                      "&datatype=json&apikey=" + credentials["apiKey"] + "&outputsize=" + conf["alphavantageCompactOrFull"]

            rawDataRequest = requests.get(rawDataRequestUri)
            rawData        = rawDataRequest.json()

            if env=='local':
                with open(rawDataFilename, 'w') as rawDataFile:
                    json.dump(rawData, rawDataFile)
            elif env=='gcp':
                os.environ.get('BUCKET_NAME',app_identity.get_default_gcs_bucket_name())

                rawDataFile = gcs.open(rawDataFilename,'w')

                json.dump(rawData, rawDataFile)

                rawDataFile.close()

        #digest the Alphavantage JSON format into an array of date/price hashes
        dateFormat = "%Y-%m-%d"
        fixedDate  = datetime(1970,1,1)

        datesAndPrices = []
        for date,priceDict in rawData[conf["alphavantageJsonTimeType"]].items():
            dateAndPrice = {}

            dateAndPrice["date"]               = date
            dateAndPrice["daysSinceFixedDate"] = (datetime.strptime(date, dateFormat)-fixedDate).days
            dateAndPrice["price"]              = priceDict[conf["alphavantageJsonPriceType"]]

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

                    intervalDatePriceDict["startDate"] = startDict["date"]
                    intervalDatePriceDict["endDate"]   = endDict["date"]

                    intervalDatePriceDict["startDaysSinceFixedDate"] = startDict["daysSinceFixedDate"]
                    intervalDatePriceDict["endDaysSinceFixedDate"]   = endDict["daysSinceFixedDate"]

                    intervalDatePriceDict["startPrice"] = startDict["price"]
                    intervalDatePriceDict["endPrice"]   = endDict["price"]

                    intervalDatePriceDicts.append(intervalDatePriceDict)

        #now we create a dict keyed by interval length
        datePriceDictsByIntervalLength = {}
        for invervalDatePriceDict in intervalDatePriceDicts:
            endDate   = datetime.strptime(invervalDatePriceDict["endDate"], dateFormat)
            startDate = datetime.strptime(invervalDatePriceDict["startDate"], dateFormat)

            intervalLength = invervalDatePriceDict["endDaysSinceFixedDate"]-invervalDatePriceDict["startDaysSinceFixedDate"]

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

        if env=="local":
            with open(intervalDataFilename, 'w') as intervalDataFile:
                json.dump(intervalMetrics,intervalDataFile)
        elif env=="gcp":
            os.environ.get('BUCKET_NAME',app_identity.get_default_gcs_bucket_name())

            intervalDataFile = gcs.open(intervalDataFilename,'w')

            json.dump(intervalMetrics, intervalDataFilename)

            rawDataFile.close()

        return
