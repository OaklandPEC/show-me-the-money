# Do this
```python
from netfile_client.NetFileClient import NetFileClient
nf = NetFileClient()
```

It will automatically load `NETFILE_API_KEY` and `NETFILE_API_SECRET` from a .env file.

Then you can do:
```python
nf.fetch('filings')
```

This fetches all filings. Currently configured endpoints are 'filings', 'filers', 'transactions', 'filing_activities', 'filing_elements', and 'elections'. You could concievably add any endpoint listed in the docs https://netfile.com/api/campaign/swagger/index.html. See the static `Routes` class for configured endpoints.

You can also pass keyword args to the `fetch` method and they will be sent as query parameters. For example, you could call `fetch` like `nf.fetch('transactions', FilingNid=somefilingid)` to get transactions for a particular filing. The client doesn't do any kind of validation on these parameters, it'll naively pass them along in the HTTP request.

This is heavily inspired by NetFile's own client https://github.com/NetFile/campaign-api-client, which, iirc, didn't serve my purposes well because it was geared towards the sync functionality.
