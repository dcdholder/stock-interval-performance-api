# Stock Interval Performance API

Over a given range of dates, see the time intervals within that date range in which stocks performed at their best and worst.

## Usage

Visit `${PUBLIC_API_URL}/intervals/symbol=${STOCK_TICKER_SYMBOL}&startdate=${START_DATE}&enddate=${END_DATE}` where START_DATE and END_DATE are of the form YYYY-MM-DD, YYYY-MM or YYYY.

## Deployment

1. Create a new project in GCP.
2. Add a bucket to it. Paste the bucket name into env.json.
3. Go to Alphavantage and generate an API key. Paste it into credentials.json.
4. Clone this repo in the shell.
5. Run `gcloud app deploy publicApi.yaml privateApi.yaml` from the directory you created with git to deploy the two APIs.

## Future Development

- Allow a public API user to specify a date "resolution".
- Create a cron job which will refresh "static" data files on a regular basis through the private API.
- Spin up a compute instance for each stock when generating the static data through the private API.
