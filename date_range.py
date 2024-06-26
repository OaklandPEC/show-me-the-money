""" Get stuff out of Netfile v2 API
"""
import pandas as pd
import datetime as dt
import copy
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

AUTH=get_auth_from_env_file()

pp = PrettyPrinter()

def get_form(form,offset=0):
    """ Get filings with matching form type
    """
    url = f'{BASE_URL}/filing/v101/filings?Limit=100000&SpecificationForm={form}'

    params = { **PARAMS }
    if offset > 0:
        params['offset'] = offset

    res = requests.get(url, params=params, auth=AUTH)
    if res.status_code == 500:
        return get_form(form,offset=0)
    else:
        body = res.json()
        results = body.pop('results')

        return results, body
    
class form460:
    def __init__(self, rpt_date, date_range, filing_id, trash=0) -> None:
        self.date_range = date_range
        self.rpt_date = rpt_date
        self.filing_id = filing_id        
        self.trash = trash
    def copy(self):
        return copy.deepcopy(form460(self.rpt_date, self.date_range, self.filing_id))
    
def is_iso_str_in_range(iso_str, date_range):
    if iso_str:
        return dt.datetime.fromisoformat(iso_str).date().toordinal() in date_range
    else:
        return True

    
def date_range_fix(filter_df, filing_date = {}):
    formlist = sorted([item[11] for item in filter_df.itertuples()], key=lambda x: x.rpt_date)
    # subsets lose all date range
    superceded = [base for base in formlist if any(base.date_range.issubset(noble.date_range) and base.filing_id != noble.filing_id and noble.rpt_date > base.rpt_date for noble in formlist)]
    for base in superceded:
        base.date_range = set()
        filing_date[base.filing_id] = base.date_range
    formlist_copy = [form.copy() for form in formlist if form.date_range]

    for base in formlist_copy:
        other_date_ranges = [noble.date_range for noble in formlist if noble.rpt_date > base.rpt_date and noble.filing_id != base.filing_id]
        
        if other_date_ranges:
            base.date_range = base.date_range - set.union(*other_date_ranges)
        filing_date[base.filing_id] = base.date_range
    return filing_date

fppc460 = get_form('FPPC460')[0]
fppc465 = get_form('FPPC465')[0]
contribution_form = fppc460 + fppc465
# Filter and create the data
contribution_form_data = [
    {
        'filerNid': item['filerMeta']['filerId'],
        'originalFilingId': item['originalFilingId'],
        'commonName': item['filerMeta']['commonName'],
        'RegType1': item['filerMeta']['strings']['RegType1'],
        'SOS ID': item['filerMeta']['strings'].get('Registration_CA SOS', None),
        'amendmentType': item['filingMeta']['amendmentType'],
        'amendmentSequence': item['filingMeta']['amendmentSequence'],
        'rpt_date': dt.datetime.strptime(item['filingMeta']['legalFilingDate'], '%Y-%m-%d').date().toordinal(),
        'from_date': dt.datetime.strptime(item['filingMeta']['startDate'], '%Y-%m-%d').date().toordinal(),
        'thru_date': dt.datetime.strptime(item['filingMeta']['endDate'], '%Y-%m-%d').date().toordinal(),
    } 
    for item in contribution_form
    if item['filingMeta']['legalFilingDate'] and item['filingMeta']['startDate'] and item['filingMeta']['endDate']
]
contribution_df=pd.DataFrame(contribution_form_data)
# Create 'date_range' column
contribution_df['date_range'] = [form460(row['rpt_date'],set(range(row['from_date'],row['thru_date']+1)),row['originalFilingId'], index) for index, row in contribution_df.iterrows()]



filing_date = {}
for id in contribution_df['filerNid'].unique():
    filing_date = date_range_fix(contribution_df[contribution_df['filerNid']==id],filing_date)
