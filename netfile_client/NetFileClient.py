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

class BaseEndpointClient:
    """ Base functionality for fetching from NetFile endpoint """
    def __init__(self, base_url:str, base_params:dict, auth:tuple, additional_params:dict={}):
        self.has_next_page = True
        self.base_url = base_url
        self.url = base_url
        initial_params = {
            'offset': 0,
            'limit': 1000
        }
        self.base_params = {
            **initial_params,
            **base_params
        }
        self.params = {
            **self.base_params,
            **additional_params
        }
        self.auth = auth
        self.session = requests.Session()
        self.session.hooks['response'] = [
            lambda response, *_, **__: response.raise_for_status()
        ]
        retry_strategy = requests.adapters.Retry(total=5, backoff_factor=2)
        adapter = TimeoutAdapter(max_retries=retry_strategy)
        self.session.mount('https://', adapter)

    def fetch(self):
        res = self.session.get(self.url, auth=self.auth, params=self.params)
        body = res.json()
        if self.params['offset'] == 0:
            print(body['totalCount'], flush=True)

        self._configure_next_request(body)

        return body['results']
    
    def _configure_next_request(self, response_body):
        self.has_next_page = response_body['hasNextPage']
        next_offset = self.params['limit'] + self.params['offset'] if self.has_next_page else None

        if next_offset is not None and callable(self._set_next_fetch_by):
            try:
                self._set_next_fetch_by()
            except StopIteration:
                print('done', flush=True)

        else:
            self.params['offset'] = next_offset
            print(self.params['offset'], self.params['limit'], flush=True)

class FilingElementClient(BaseEndpointClient):
    """ Fetch filing elements """
    def __init__(self, base_url, base_params, auth, **kwargs):
        super().__init__(base_url, base_params, auth)
        self.url = f'{self.base_url}{Routes.filing_elements}'
        self._fetchable_by = [
            'filing_nid',
            'element_nid'
        ]

        # Prepare own query attributes
        self._set_next_fetch_by = self._configure_fetch_by(**kwargs)

    def _configure_fetch_by(self, **kwargs):
        if len(kwargs) > 1:
            raise ValueError(f'filing_elements may only be queried by 1 param type, got {kwargs}')

        if len(kwargs) < 1:
            return None

        fetch_by = list(kwargs.keys())[0]
        if fetch_by not in self._fetchable_by:
            raise ValueError(f'Unknown request parameter {fetch_by}')

        return getattr(self, f'_set_next_{fetch_by}')(kwargs[fetch_by])

    def _set_next_filing_nid(self, filing_nids:list[str]=None):
        """ Add 'filing_nid' to self.params """
        filing_nids_iter = iter(filing_nids)
        filing_nid = next(filing_nids_iter)
        fetch_by = 'filingNid'
        def set_next():
            self.params[fetch_by] = filing_nid

        return set_next

    def _set_next_element_nid(self, element_nid):
        """ Add /{element_nid} to self.url """
        pass

class FilingClient(BaseEndpointClient):
    pass

class FilerClient(BaseEndpointClient):
    pass

class TransactionsClient(BaseEndpointClient):
    pass

class FilingActivityClient(BaseEndpointClient):
    pass

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
        params = self._params
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
