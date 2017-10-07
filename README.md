# Stock Interval Performance API

Over a given range of dates, see the time intervals within that date range in which stocks performed at their best and worst.

The API can dynamically generate interval data for a date range up to a certain range length (adjusted as a function of time resolution), as well as serve statically-generated interval data created through a second, "private" API.

The private API can be configured to pre-generate interval data for a few date range samples (year-to-year, month=to-month etc.) to allow certain large date ranges to be used in latency-sensitive applications. Currently, the private API is hardcoded to generate interval data for all year-to-year ranges in the source data at a weekly resolution.

## Usage

Visit `${PUBLIC_API_URL}/intervals/symbol=${STOCK_TICKER_SYMBOL}&startdate=${START_DATE}&enddate=${END_DATE}` where START_DATE and END_DATE are of the form YYYY-MM-DD, YYYY-MM or YYYY. Optionally, add `&resolution=weekly` to reduce the resolution and thereby increase the maximum date range for dynamically-generated interval data.

## Deployment

1. Create a new project in GCP.
2. Add a bucket to it. Paste the bucket name into env.json.
3. Go to Alphavantage and generate an API key. Paste it into credentials.json.
4. Clone this repo in the shell.
5. Run `gcloud app deploy publicApi.yaml privateApi.yaml` from the directory you created with git to deploy the two APIs.

## Future Development

- Create a cron job which will refresh "static" data files on a regular basis through the private API.
- Spin up a compute instance for each stock when generating the static data through the private API.
