from google.cloud import storage, exceptions

import json
import requests

import re

from datetime import datetime
import operator

with open("env.json") as environmentFile:
    env = json.load(environmentFile)

with open("conf.json") as configurationFile:
    conf = json.load(configurationFile)

if env["env"]=='gcp':
    client = storage.Client()
    bucket = client.get_bucket(env['gcp']['bucketName'])

def getIntervalDataFilename(tickerSymbol,startDateString,endDateString):
    return 'intervals-' + tickerSymbol + '-' + startDateString + '_' + endDateString + '.json'

def getRawDataFilename(tickerSymbol):
    return 'raw-' + tickerSymbol + '-' + conf["alphavantageCompactOrFull"] + '-' + conf["alphavantageTimeFunction"] + '.json'

def resolveToDateRange(startDateString,endDateString,timeGranularity):
    pass

def getExistingIntervalData(tickerSymbol):
    intervalDataFilename = getIntervalDataFilename(tickerSymbol,"","")

    if env["env"]=='local':
        with open(intervalDataFilename) as intervalDataFile:
            return json.load(intervalDataFile)
    elif env["env"]=='gcp':
        intervalDataBlob = storage.Blob(intervalDataFilename, bucket)

        return json.loads(intervalDataBlob.download_as_string().decode("utf-8"))

def refreshIntervalData():
    with open("tickerSymbols.json") as tickerSymbolsFile:
        tickerSymbols = json.load(tickerSymbolsFile)

    for tickerSymbol in tickerSymbols:
        rawDataFilename = getRawDataFilename(tickerSymbol)

        #only call the alphavantage API for financial data if we haven't called it before
        try:
            if env["env"]=='local':
                with open(rawDataFilename) as rawDataFile:
                    rawData = json.load(rawDataFile)
            elif env["env"]=='gcp':
                rawDataBlob = storage.Blob(rawDataFilename, bucket)

                rawData = json.loads(rawDataBlob.download_as_string().decode("utf-8"))

        except (IOError, exceptions.NotFound):
            with open("credentials.json") as credentialsFile:
                credentials = json.load(credentialsFile)

            rawDataRequestUri = conf["alphavantageAddress"] + "/query?function=" +  \
                                      conf["alphavantageTimeFunction"] + "&symbol=" + tickerSymbol + \
                                      "&datatype=json&apikey=" + credentials["apiKey"] + "&outputsize=" + conf["alphavantageCompactOrFull"]

            rawDataRequest = requests.get(rawDataRequestUri)
            rawData        = rawDataRequest.json()

            if env["env"]=='local':
                with open(rawDataFilename, 'w') as rawDataFile:
                    json.dump(rawData, rawDataFile)
            elif env["env"]=='gcp':
                rawDataBlob = storage.Blob(rawDataFilename, bucket)
                rawDataBlob.upload_from_string(json.dumps(rawData),content_type='text/json')

        generateIntervalDataFileFromRawDataMonthlyGranularity(rawData)

def generateIntervalDataFileFromRawDataMonthlyGranularity(rawData):
    earliestAndLatestDaysByMonth = {}
    for dateString in rawData[conf["alphavantageJsonTimeType"]]:
        monthMatch      = re.search('([0-9]{4}-[0-9]{2})-([0-9]{2})',dateString)
        monthIdentifier = monthMatch.group(1)
        dayIdentifier   = monthMatch.group(2)

        if monthIdentifier not in earliestAndLatestDaysByMonth.keys():
            earliestAndLatestDaysByMonth[monthIdentifier] = {}
            earliestAndLatestDaysByMonth[monthIdentifier]["earliestDayInMonth"] = "32" #higher than highest possible
            earliestAndLatestDaysByMonth[monthIdentifier]["latestDayInMonth"]   = "00" #lower than lowest possible

        if dayIdentifier<earliestAndLatestDaysByMonth[monthIdentifier]["earliestDayInMonth"]:
            earliestAndLatestDaysByMonth[monthIdentifier]["earliestDayInMonth"] = dayIdentifier

        if dayIdentifier>earliestAndLatestDaysByMonth[monthIdentifier]["latestDayInMonth"]:
            earliestAndLatestDaysByMonth[monthIdentifier]["latestDayInMonth"] = dayIdentifier

    #generate interval data for each possible pair of months, starting from the earliest day in the first and ending at the latest day in the last
    #also generate data for individual months
    for startMonthIdentifier in earliestAndLatestDaysByMonth:
        earliestDateString = startMonthIdentifier + '-' + earliestAndLatestDaysByMonth[startMonthIdentifier]["earliestDayInMonth"]
        for endMonthIdentifier in earliestAndLatestDaysByMonth:
            if endMonthIdentifier>=startMonthIdentifier:
                latestDateString = endMonthIdentifier + '-' + earliestAndLatestDaysByMonth[startMonthIdentifier]["latestDayInMonth"]

                generateIntervalDataFileFromRawDataAndDateRange(rawData,earliestDateString,latestDateString)

def generateIntervalDataFileFromRawDataAndDateRange(rawData,startDateString,endDateString):
    intervalDataFilename = getIntervalDataFilename(rawData["Meta Data"]["2. Symbol"],startDateString,endDateString)

    #digest the Alphavantage JSON format into an array of date/price hashes
    dateFormat = "%Y-%m-%d"
    fixedDate  = datetime(1970,1,1)

    datesAndPrices = []
    for dateString,priceDict in rawData[conf["alphavantageJsonTimeType"]].items():
        if dateString<endDateString and dateString>startDateString:
            dateAndPrice = {}

            dateAndPrice["dateString"]         = dateString
            dateAndPrice["daysSinceFixedDate"] = (datetime.strptime(dateString, dateFormat)-fixedDate).days
            dateAndPrice["price"]              = priceDict[conf["alphavantageJsonPriceType"]]

            datesAndPrices.append(dateAndPrice)

    #iterate over all possible pairs of the above date/price dicts to generate time interval dicts
    intervalDatePriceDicts = []
    for j in range(len(datesAndPrices)):
        for i in range(len(datesAndPrices)):
            intervalDatePriceDict = {}
            #prevents reordered pairs from being recorded twice
            #also prevents entries with startDate==endDate
            if datesAndPrices[j]["dateString"] > datesAndPrices[i]["dateString"]:
                startDict = datesAndPrices[i]
                endDict   = datesAndPrices[j]

                intervalDatePriceDict["startDateString"] = startDict["dateString"]
                intervalDatePriceDict["endDateString"]   = endDict["dateString"]

                intervalDatePriceDict["startDaysSinceFixedDate"] = startDict["daysSinceFixedDate"]
                intervalDatePriceDict["endDaysSinceFixedDate"]   = endDict["daysSinceFixedDate"]

                intervalDatePriceDict["startPrice"] = startDict["price"]
                intervalDatePriceDict["endPrice"]   = endDict["price"]

                intervalDatePriceDicts.append(intervalDatePriceDict)

    #now we create a dict keyed by interval length
    datePriceDictsByIntervalLength = {}
    for invervalDatePriceDict in intervalDatePriceDicts:
        endDate   = datetime.strptime(invervalDatePriceDict["endDateString"], dateFormat)
        startDate = datetime.strptime(invervalDatePriceDict["startDateString"], dateFormat)

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

    if env["env"]=="local":
        with open(intervalDataFilename, 'w') as intervalDataFile:
            json.dump(intervalMetrics,intervalDataFile)
    elif env["env"]=="gcp":
        intervalDataBlob = storage.Blob(intervalDataFilename, bucket)
        intervalDataBlob.upload_from_string(json.dumps(intervalMetrics),content_type='text/json')

def generateFullIntervalDataFileFromRawDataAllDates(rawData):
    dateStrings = []
    for dateString in rawData[conf["alphavantageJsonTimeType"]]:
        dateStrings.append(dateString)
        dateStrings.sort()

    generateIntervalDataFileFromRawDataAndDateRange(rawData,dateStrings[0],dateStrings[len(dateStrings)-1])
