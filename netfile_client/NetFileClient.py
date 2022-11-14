from pathlib import Path
import requests

TIMEOUT= 7

def get_auth_from_env_file(filename: str='.env'):
    """ Split .env file on newline and look for API_KEY and API_SECRET
        Return their values as a tuple
    """
    auth_keys = [ 'API_KEY', 'API_SECRET' ]
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

class BaseEndpointClient:
    """ Base functionality for fetching from NetFile endpoint """
    def __init__(self, base_url, base_params, auth):
        self.has_next_page = True
        self.base_url = base_url
        self.base_params = base_params
        self.auth = auth
        self.session = requests.Session()
        self.session.hooks['response'] = [
            lambda response, *args, **kwargs: response.raise_for_status()
        ]
        retry_strategy = requests.adapters.Retry(total=5, backoff_factor=2)
        adapter = TimeoutAdapter(max_retries=retry_strategy)
        self.session.mount('https://', adapter)

class FilingElementsClient(BaseEndpointClient):
    """ Fetch filing elements """
    def __init__(self, base_url, base_params, auth, **kwargs):
        super().__init__(base_url, base_params, auth)
        route = Routes.filing_elements
        self.url = f'{self.base_url}{route}'
        self.params = {
            **self.base_params,
            'offset': 0,
            'limit': 1000
        }
        self._fetchable_by = [
            'filing_nid',
            'element_nid'
        ]

        # Prepare own query attributes
        self._set_next_fetch_by = self._configure_fetch_by(**kwargs)

    def _configure_next_request(self, res):
        self.has_next_page = res['hasNextPage']
        next_offset = self.params['limit'] + self.params['offset'] if self.has_next_page else None

        if next_offset is None and callable(self._set_next_fetch_by):
            try:
                self._set_next_fetch_by()
            except StopIteration:
                pass
        else:
            self.params['offset'] = next_offset

    def _get(self, params):
        res = self.session.get(self.url, auth=self.auth, params=params)
        body = res.json()
        print('.', end='', flush=True)
        self._configure_next_request(body)

        return body['results']

    def fetch(self):
        """ Fetch all filings elements,
            probably for filing_nids
        """
        return self._get(self.params)

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
    base_url = 'https://netfile.com/api/campaign'
    base_params = { 'aid': 'COAK' }
    auth = get_auth_from_env_file()
    routes = Routes
    _clients = {
        'filing_elements': FilingElementsClient,
        'filings': FilingClient,
        'filer': FilerClient,
        'transaction': TransactionsClient,
        'filing_activities': FilingActivityClient
    }

    @classmethod
    def fetch(cls, endpoint, **kwargs):
        """ Fetch all of a particular record type """
        fetcher = cls._clients[endpoint](cls.base_url, cls.base_params, cls.auth, **kwargs)
        results = []

        while fetcher.has_next_page:
            results += fetcher.fetch()

        print('')
        return results
