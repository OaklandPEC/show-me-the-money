""" Get stuff out of Netfile v2 API
"""
from pprint import PrettyPrinter
from pathlib import Path
import os
import requests

BASE_URL = 'https://netfile.com/api/campaign'
CONTRIBUTION_FORM = 'F460A'
EXPENDITURE_FORM = 'F460E'

PARAMS = { 'aid': 'COAK' }

def get_auth_from_env_file(filename: str='.env'):
    """ Split .env file on newline and look for API_KEY and API_SECRET
        Return their values as a tuple
    """
    env_file=Path(filename)
    auth_keys = [ 'API_KEY', 'API_SECRET' ]
    if env_file.exists():
        auth = tuple( v for _, v in sorted([
            ln.split('=') for ln in
            env_file.read_text(encoding='utf8').strip().split('\n')
            if ln.startswith(auth_keys[0]) or ln.startswith(auth_keys[1])
        ], key=lambda ln: auth_keys.index(ln[0])))
    else:
        auth=tuple(os.environ[key] for key in auth_keys)
            
    return auth


pp = PrettyPrinter()

def get_filing(offset=0):
    """ Get a filing
    """
    url = f'{BASE_URL}/filing/v101/filings'

    params = { **PARAMS }
    if offset > 0:
        params['offset'] = offset

    res = requests.get(url, params=params, auth=AUTH)
    body = res.json()
    results = body.pop('results')

    return results, body

def get_transaction(filing):
    """ Get a transaction
    """
    url = f'{BASE_URL}/cal/v101/transaction-elements'

    res = requests.get(url, params={
        'filingNid': filing['filingNid'],
        'parts': 'All',
        **PARAMS
    }, auth=AUTH)
    body = res.json()

    return body['results']

def list_elections():
    """ Get all the elections
    """
    url = f'{BASE_URL}/election/v101/elections'

    res = requests.get(url, params=PARAMS, auth=AUTH)
    body = res.json()

    return body['results']

def get_filer(filer_nid):
    """ Get one filer
    """
    url = f'{BASE_URL}/filer/v101/filers'

    res = requests.get(url, params={ **PARAMS, 'filerNid': filer_nid }, auth=AUTH)
    body = res.json()

    return body['results']

if __name__ == '__main__':
    filings, meta = get_filing()
    print('----- METADATA returned from API -----')
    pp.pprint(meta)
    print('----- FILING -----')
    pp.pprint(filings[0])

    query_count = 0
    results_len = []
    transactions = []
    for i, f in enumerate(filings):
        next_trans = get_transaction(f)
        results_len.append(len(next_trans))
        transactions += next_trans
        query_count += 1
        if len(next_trans) > 0 and CONTRIBUTION_FORM in [ t['calTransactionType'] for t in next_trans ]:
            tran_filing = i
            break

    print('----- TRANSACTION -----')
    print('--------- Contribution -----')
    contributions = [ t for t in transactions if t['calTransactionType'] == CONTRIBUTION_FORM ]
    print('How many contributions?', len(contributions))
    one_contrib = contributions[0]
    pp.pprint(one_contrib)
    expenditures = [ t for t in transactions if t['calTransactionType'] == EXPENDITURE_FORM ]
    print('How many expenditures', len(expenditures))
    print('How many total transactions?', len(transactions))

    if len(expenditures) < 1:
        remaining_filings = filings[tran_filing + 1:]
        for i, f in enumerate(remaining_filings):
            next_trans = get_transaction(f)
            results_len.append(len(next_trans))
            transactions += next_trans
            query_count += 1
            expenditures = [ t for t in next_trans if t['calTransactionType'] == EXPENDITURE_FORM ]

    if len(expenditures) > 0:
        tran_filing = tran_filing + i
        print('--------- Expenditure -----')
        pp.pprint(expenditures[0])

    print('----- ALL FORM TYPES -----')
    pp.pprint(set(t['calTransactionType'] for t in transactions))

    print('----- ARE THERE ANY tranDscr AT ALL? -----')
    pp.pprint(set(t['transaction']['tranDscr'] for t in transactions))

    print('----- METRICS -----')
    print('Total number of transaction queries', len(results_len))
    print('Total number of transactions', sum(results_len))
    print('Avg size of transaction results', sum(results_len) / len(results_len))

    for t in transactions:
        filer = get_filer(t['filerNid'])
        if filer[0]['candidateName'] is not None:
            break

    print('----- FILER -----')
    pp.pprint(filer)


    elections = list_elections()
    pp.pprint(elections[0])

    election_dates = [ e['electionDate'] for e in elections ]
    print('----- ELECTION DATES -----')
    pp.pprint(election_dates)
