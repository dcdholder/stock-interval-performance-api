import boto3
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
elif env["env"]=='aws':
    client = boto3.client('s3')
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(env['aws']['bucketName'])

def getIntervalDataFilename(tickerSymbol,startDateString,endDateString,resolution):
    return 'intervals-' + tickerSymbol + '-' + startDateString + '_' + endDateString + '-' + resolution + '.json'

def getRawDataFilename(tickerSymbol):
    return 'raw-' + tickerSymbol + '-' + conf["alphavantageCompactOrFull"] + '-' + conf["alphavantageTimeFunction"] + '.json'

def resolveToDateRange(startDateString,endDateString):
    dailyGranularityRegex   = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    monthlyGranularityRegex = re.compile("^[0-9]{4}-[0-9]{2}$")
    yearlyGranularityRegex  = re.compile("^[0-9]{4}$")

    for granularityRegex in [dailyGranularityRegex,monthlyGranularityRegex,yearlyGranularityRegex]:
        granularityMatchStartDate = granularityRegex.match(startDateString)
        granularityMatchEndDate   = granularityRegex.match(endDateString)

        if granularityMatchStartDate!=None and granularityMatchEndDate==None:
            raise ValueError("Invalid format for start date, or attempted start/end date format mixing.")
        elif granularityMatchStartDate==None and granularityMatchEndDate!=None:
            raise ValueError("Invalid format for end date, or attempted start/end date format mixing.")
        elif granularityMatchStartDate!=None and granularityMatchEndDate!=None:
            matchingIdentifierStartDate = granularityMatchStartDate.group(0)
            matchingIdentifierEndDate   = granularityMatchEndDate.group(0)

            if granularityRegex==dailyGranularityRegex:
                return [matchingIdentifierStartDate, matchingIdentifierEndDate]
            elif granularityRegex==monthlyGranularityRegex:
                return [matchingIdentifierStartDate + '-01', matchingIdentifierEndDate + '-31']
            elif granularityRegex==yearlyGranularityRegex:
                return [matchingIdentifierStartDate + '-01-01', matchingIdentifierEndDate + '-12-31']

    raise ValueError("Invalid format for start date and end date.")

#some dates are not available in the raw data -- this is reflected in the interval data filenames
def resolveToAvailableDateRange(rawData,startDateString,endDateString):
    [initialStartDateString,initialEndDateString] = resolveToDateRange(startDateString,endDateString)

    initialEarliestDateString = "9999-99-99"
    initialLatestDateString   = "0000-00-00"

    earliestDateStringAtOrAfterStartDate = initialEarliestDateString
    latestDateStringBeforeOrAtEndDate    = initialLatestDateString

    for dateString in rawData[conf["alphavantageJsonTimeType"]]:
        if dateString<earliestDateStringAtOrAfterStartDate and dateString>=initialStartDateString:
            earliestDateStringAtOrAfterStartDate = dateString
        if dateString>latestDateStringBeforeOrAtEndDate and dateString<=initialEndDateString:
            latestDateStringBeforeOrAtEndDate = dateString

    if earliestDateStringAtOrAfterStartDate==initialEarliestDateString:
        raise ValueError("Could not resolve start date " + initialStartDateString + " to an available date (initial input " + startDateString + ").")
    elif latestDateStringBeforeOrAtEndDate==initialLatestDateString:
        raise ValueError("Could not resolve end date " + initialEndDateString + " to an available date (initial input " + endDateString + ").")
    else:
        return [earliestDateStringAtOrAfterStartDate,latestDateStringBeforeOrAtEndDate]

def getIntervalDataFromDateRange(tickerSymbol,startDateString,endDateString,resolution):
    rawData = rawDataFromTickerSymbol(tickerSymbol)

    [resolvedStartDateString,resolvedEndDateString] = resolveToAvailableDateRange(rawData,startDateString,endDateString)

    dateFormat = "%Y-%m-%d"
    fixedDate  = datetime(1970,1,1)

    dateRangeInDays = (datetime.strptime(resolvedEndDateString, dateFormat)-datetime.strptime(resolvedStartDateString, dateFormat)).days

    dateRangeInDaysResolutionAdjusted = dateRangeInDays
    if resolution=="weekly":
        dateRangeInDaysResolutionAdjusted = dateRangeInDays // 7

    if dateRangeInDaysResolutionAdjusted<int(conf['maxDynamicGenerationDateRange']):
        try:
            return getExistingIntervalData(tickerSymbol,resolvedStartDateString,resolvedEndDateString,resolution)
        except:
            generateIntervalDataFileFromRawDataAndDateRange(rawData,resolvedStartDateString,resolvedEndDateString,resolution)

            return getExistingIntervalData(tickerSymbol,resolvedStartDateString,resolvedEndDateString,resolution)
    else:
        try:
            return getExistingIntervalData(tickerSymbol,resolvedStartDateString,resolvedEndDateString,resolution)
        except:
            raise ValueError("Could not find statically-generated interval data for the specified time range/resolution.")

def getExistingIntervalData(tickerSymbol,startDateString,endDateString,resolution):
    intervalDataFilename = getIntervalDataFilename(tickerSymbol,startDateString,endDateString,resolution)

    if env["env"]=='local':
        with open(intervalDataFilename) as intervalDataFile:
            return json.load(intervalDataFile)
    elif env["env"]=='gcp':
        intervalDataBlob = storage.Blob(intervalDataFilename, bucket)

        return json.loads(intervalDataBlob.download_as_string().decode("utf-8"))
    elif env["env"]=='aws':
        intervalDataObject = client.get_object(Bucket=env['aws']['bucketName'], Key=intervalDataFilename)

        return json.loads(intervalDataObject['Body'].read().decode("utf-8"))

def rawDataFromTickerSymbol(tickerSymbol):
    rawDataFilename = getRawDataFilename(tickerSymbol)

    #only call the alphavantage API for financial data if we haven't called it before
    try:
        if env["env"]=='local':
            with open(rawDataFilename) as rawDataFile:
                rawData = json.load(rawDataFile)
        elif env["env"]=='gcp':
            rawDataBlob = storage.Blob(rawDataFilename, bucket)

            rawData = json.loads(rawDataBlob.download_as_string().decode("utf-8"))
        elif env["env"]=='aws':
            rawDataObject = client.get_object(Bucket=env['aws']['bucketName'], Key=rawDataFilename)

            return json.loads(rawDataObject['Body'].read().decode("utf-8"))

    except:
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
        elif env["env"]=='aws':
            bucket.put_object(Body=json.dumps(rawData), Key=rawDataFilename)

    return rawData

def refreshIntervalData(symbol="all",numFragments=1,fragmentIndex=0):
    if symbol=="all":
        with open("tickerSymbols.json") as tickerSymbolsFile:
            tickerSymbols = json.load(tickerSymbolsFile)
    else:
        tickerSymbols = [symbol]

    for tickerSymbol in tickerSymbols:
        rawData = rawDataFromTickerSymbol(tickerSymbol)

        generateIntervalDataFileFromRawDataYearlyGranularity(rawData,'weekly',numFragments=numFragments,fragmentIndex=fragmentIndex)

def getAllYearsFromRawData(rawData):
    years = set()
    for dateString in rawData[conf["alphavantageJsonTimeType"]]:
        yearMatch = re.search('([0-9]{4})-[0-9]{2}-[0-9]{2}',dateString)
        years.add(yearMatch.group(1))

    return years

def generateIntervalDataFileFromRawDataMonthlyGranularity(rawData,resolution,numFragments=1,fragmentIndex=0):
    months = []
    for month in range(1,12+1):
        if month<10:
            month = "0" + str(month)
        else:
            month = str(month)

        months.append(month)

    years = getAllYearsFromRawData(rawData)

    for startYear in years:
        for startMonth in months:
            startDateString = startYear + '-' + startMonth

            for endYear in years:
                for endMonth in months:
                    if endYear>=startYear and endMonth>=startMonth:
                        endDateString = endYear + '-' + endMonth

                        #try/except is necessary because some end dates will be generated which are prior to the earliest dates in the raw data
                        try:
                            [resolvedStartDateString,resolvedEndDateString] = resolveToAvailableDateRange(rawData,startDateString,endDateString)
                            generateIntervalDataFileFromRawDataAndDateRange(rawData,resolvedStartDateString,resolvedEndDateString,resolution)
                        except:
                            pass

def generateIntervalDataFileFromRawDataYearlyGranularity(rawData,resolution,numFragments=1,fragmentIndex=0):
    years = getAllYearsFromRawData(rawData)

    resolvedDateRanges = []
    for startYear in years:
        for endYear in years:
            if endYear>=startYear:
                resolvedDateRanges.append(resolveToAvailableDateRange(rawData,startYear,endYear))

    resolvedDateRangesBelongingToThisFragment = assignToFragment(resolvedDateRanges,numFragments,fragmentIndex)

    for dateRange in resolvedDateRangesBelongingToThisFragment:
        resolvedStartDateString = dateRange[0]
        resolvedEndDateString   = dateRange[1]

        generateIntervalDataFileFromRawDataAndDateRange(rawData,resolvedStartDateString,resolvedEndDateString,resolution)

def assignToFragment(startDateEndDatePairs,numFragments,fragmentIndex):
    dateFormat = "%Y-%m-%d"

    #first we want the intervals to be ordered, so that date ranges of similar length are spread over the fragments equally
    timeDeltaDicts = []
    for startDateEndDatePair in startDateEndDatePairs:
        timeDelta = (datetime.strptime(startDateEndDatePair[1], dateFormat)-datetime.strptime(startDateEndDatePair[0], dateFormat)).days

        timeDeltaDicts.append({"startDateEndDateStringPair": startDateEndDatePair,"timeDelta": timeDelta})

    timeDeltaDictsByTimeDelta = sorted(timeDeltaDicts, key=lambda k: k["timeDelta"])

    startDateEndDatePairsByTimeDelta = []
    for timeDeltaDict in timeDeltaDictsByTimeDelta:
        startDateEndDatePairsByTimeDelta.append(timeDeltaDict["startDateEndDateStringPair"])

    #now we can evenly spread the date ranges between fragments
    datePairsByFragment = {}
    for i in range(len(startDateEndDatePairsByTimeDelta)):
        if i%numFragments not in datePairsByFragment.keys():
            datePairsByFragment[i%numFragments] = []

        startDateEndDatePair = startDateEndDatePairsByTimeDelta[i]
        datePairsByFragment[i%numFragments].append(startDateEndDatePair)

    #now return only the fragment relevant to the target fragment
    return datePairsByFragment[fragmentIndex]

def generateIntervalDataFileFromRawDataAndDateRange(rawData,startDateString,endDateString,resolution):
    intervalDataFilename = getIntervalDataFilename(rawData["Meta Data"]["2. Symbol"],startDateString,endDateString,resolution)

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

    #reduce the resolution of the price data, if required
    #all lengths of intervals generated using this data should be integer multiples of the resolution
    if resolution=="weekly":
        sortedDatesAndPrices = sorted(datesAndPrices, key=lambda k: k['daysSinceFixedDate'])

        reducedDatesAndPrices = []
        previousDate = sortedDatesAndPrices[0]['daysSinceFixedDate']
        for i in range(len(sortedDatesAndPrices)):
            #WARNING: may generate sparse data in some cases to enforce intervals of an integer multiple week length
            if (sortedDatesAndPrices[i]['daysSinceFixedDate']-previousDate)%7==0:
                reducedDatesAndPrices.append(sortedDatesAndPrices[i])
                previousDate = sortedDatesAndPrices[i]['daysSinceFixedDate']

        datesAndPrices = reducedDatesAndPrices

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
    elif env["env"]=="aws":
        bucket.put_object(Body=json.dumps(intervalMetrics), Key=intervalDataFilename)
