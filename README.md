# A script to load data into "Show Me The Money" Oakland campaign finance app
See it here https://data.oaklandca.gov/campaign_finance/

# To update Socrata app
First, make sure you have Pipenv installed. Start a pipenv environment by doing
```shell
$ pipenv shell
```

Then create the contributions and expenditures CSVs by running
```shell
$ python -m v2api.create_socrata_csv
```

The script will look for NETFILE_API_KEY and NETFILE_API_SECRET environment variables. I recommend setting these variables in a .env file. Pipenv will automatically load environment variables from a .env file.

The script will print the first five lines and the length of the CSV it created, and save two CSVs, output/contribs_socrata.csv and output/expends_socrata.csv.

You can now update the Socrata app from these CSVs by doing
```shell
$ python -m v2api.update
```
