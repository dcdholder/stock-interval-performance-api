# Stock Interval Performance API

EARLY DEVELOPMENT

This API will allow you to see the variance in stock performance over smaller time intervals within a chosen date interval. The idea is to give you the worst and best times (and other points in between) you could have bought a stock historically for a range of hold times. For instance, it could tell you that the best interval to have held a given stock for one month would have been October to November of 2005, while the best interval to have held that stock for two months was December to February of 2011.

## Deployment

1. Create a new project in GCP. 
2. Add a bucket to it. Paste the bucket name into env.json.
3. Go to Alphavantage and generate an API key. Paste it into credentials.json.
4. Clone this repo in the shell.
5. Run `gcloud app deploy publicApi.yaml privateApi.yaml` from the directory you created with git to deploy the two APIs.

## Usage

Choose a date interval, maximum interval length and time resolution, then specify the performance percentiles you're looking for.

## Plans

Create a mechanism to create some data on-the-fly and generate other data statically.
