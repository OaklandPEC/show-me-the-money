import logging
import os
from pathlib import Path
import requests

TIMEOUT= 7

def get_auth_from_env_file(filename: str='.env'):
    """ Split .env file on newline and look for API_KEY and API_SECRET
        Return their values as a tuple
    """
    auth_keys = [ 'NETFILE_API_KEY', 'NETFILE_API_SECRET' ]
    auth = tuple( v for _, v in sorted([
        ln.split('=') for ln in
        Path(filename).read_text(encoding='utf8').strip().split('\n')
        if ln.startswith(auth_keys[0]) or ln.startswith(auth_keys[1])
    ], key=lambda ln: auth_keys.index(ln[0])))

    return auth

class TimeoutAdapter(requests.adapters.HTTPAdapter):
    """ Will this allow me to retry on timeout? """
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', TIMEOUT)
        super().__init__(*args, **kwargs)

    def send(self, request, *args, **kwargs):
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        return super().send(request, *args, **kwargs)

class Routes:
    """ NetFile routes """
    filings = '/filing/v101/filings'
    filers = '/filer/v101/filers'
    transactions = '/cal/v101/transaction-elements'
    filing_activities = 'filing/v101/filing-activities'
    filing_elements = '/filing/v101/filing-elements'
    elections = '/election/v101/elections'


class NetFileClient:
    """ Fetch data from NetFile V2 endpoints """
    def __init__(self, api_key='', api_secret='', env_file='.env'):
        self._base_url = 'https://netfile.com/api/campaign'
        self._initial_params = {
            'offset': 0,
            'limit': 1000
        }
        self._base_params = { 'aid': 'COAK' }
        self._params = {
            **self._base_params,
            **self._initial_params
        }
        self._auth = (api_key, api_secret) if api_key and api_secret else self.get_auth(env_file)

        self.session = requests.Session()
        self.session.hooks['response'] = [
            lambda response, *_, **__: response.raise_for_status()
        ]
        retry_strategy = requests.adapters.Retry(total=5, backoff_factor=2)
        adapter = TimeoutAdapter(max_retries=retry_strategy)
        self.session.mount('https://', adapter)

        self._log_level = os.environ.get('LOG_LEVEL', 'INFO')
        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        self._logger.addHandler(handler)
        self._logger.setLevel(self._log_level)

    def get_auth(self, env_file):
        key_api_key = 'NETFILE_API_KEY'
        key_api_secret = 'NETFILE_API_SECRET'

        # Attempt to get auth from env vars
        api_key = os.environ.get(key_api_key)
        api_secret = os.environ.get(key_api_secret)

        if api_key and api_secret:
            return api_key, api_secret

        # Attempt to get auth from .env file
        with open(env_file) as f:
            contents = {
                (item := line.split('='))[0]: item[1] for line in f.read().strip().split('\n')
            }
            api_key, api_secret = contents.get(key_api_key), contents.get(key_api_secret) 

        if api_key and api_secret:
            return api_key, api_secret
        else:
            raise KeyError('Unable to load credentials')

    def fetch(self, endpoint, **kwargs):
        """ Fetch all of a particular record type """
        url = self._base_url + getattr(Routes, endpoint)
        params = { **self._params }
        if 'params' in kwargs:
            params.update(kwargs['params'])
        res = self.session.get(url, auth=self._auth, params=params)
        body = res.json()
        results = body['results']
        self._logger.debug(body['totalCount'])

        while body['hasNextPage']:
            params['offset'] = params['limit'] + params['offset']
            res = self.session.get(url, auth=self._auth, params=params)
            body = res.json()
            results += body['results']
            self._logger.debug('%s %s', params['offset'], params['limit'])

        return results
