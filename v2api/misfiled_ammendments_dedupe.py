import pandas as pd
import datetime as dt
import numpy as np
import requests
from .query_v2_api import AUTH, BASE_URL, PARAMS

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
    def __init__(self, rpt_date, date_range, filing_id) -> None:
        self.date_range = date_range
        self.rpt_date = rpt_date
        self.filing_id = filing_id        
    def update(self, new_date_range):
        self.date_range = new_date_range

def is_iso_str_in_range(iso_str, date_range):
    if iso_str:
        return dt.datetime.fromisoformat(iso_str).date().toordinal() in date_range
    else:
        return True

# This should cut the complexity from O(n^2) to O(n)
def date_range_fix(df, result_dict):    
    array1 = np.array(df['filingNid'])
    array2 = np.array(df['date_range'].apply(lambda x: x.date_range))
    i = 0
    for array in array2[1:]:    
        if array2[i]:
            array2[i+1:] = array2[i+1:] - np.repeat(array2[i], len(array2[i+1:]))
        i+=1
    result_dict.update(dict(zip(array1, array2)))
    return result_dict

def create_corrected_period_covered():
    fppc460 = get_form('FPPC460')[0]
    fppc465 = get_form('FPPC465')[0]
    contribution_form = fppc460 + fppc465
    # Filter and create the data
    contribution_df=pd.DataFrame({
        'filerNid': item['filerMeta']['filerId'],
        'filingNid': item['filingNid'],
        'commonName': item['filerMeta']['commonName'],
        'RegType1': item['filerMeta']['strings']['RegType1'],
        'SOS ID': item['filerMeta']['strings'].get('Registration_CA SOS', None),
        'amendmentType': item['filingMeta']['amendmentType'],
        'amendmentSequence': item['filingMeta']['amendmentSequence'],
        'from_date': dt.datetime.strptime(item['filingMeta']['startDate'], '%Y-%m-%d').date().toordinal(),
        'thru_date': dt.datetime.strptime(item['filingMeta']['endDate'], '%Y-%m-%d').date().toordinal(),
        'rpt_date': dt.datetime.fromisoformat(item['filingMeta']['legalFilingDateTime']),
        'date_range': form460
        (
            dt.datetime.strptime(item['filingMeta']['legalFilingDate'], '%Y-%m-%d').date().toordinal(),
            set
            (
                range
                (
                    dt.datetime.strptime(item['filingMeta']['startDate'], '%Y-%m-%d').date().toordinal(),
                    dt.datetime.strptime(item['filingMeta']['endDate'], '%Y-%m-%d').date().toordinal()+1
                )
            ),
            item['filingNid'],
        )
    } 
    for item in contribution_form
    if item['filingMeta']['legalFilingDate'] and item['filingMeta']['startDate'] and item['filingMeta']['endDate'])

    # sort filings by report date, more recent report dates will be prefered this way
    contribution_df = contribution_df.sort_values('rpt_date', ascending=False)
    # get indices of the columns which cover the same periods as another by the same filer
    dupe_indices = contribution_df[contribution_df.duplicated(subset=['filerNid', 'from_date', 'thru_date'], keep='first')].index
    # empty the date_range but keep the row
    contribution_df.loc[dupe_indices, 'date_range'] = contribution_df.loc[dupe_indices, 'date_range'].apply(lambda x: x.update(set()) or x)

    filing_date = {}

    for id in contribution_df['filerNid'].unique():
        filing_date = date_range_fix(contribution_df[contribution_df['filerNid']==id],filing_date)

    return filing_date

if __name__ == "__main__":
    filing_date = create_corrected_period_covered()
