""" classes for Filer and FilerCollection
    each capable of returning a Pandas DataFrame
"""
from datetime import datetime as dt
from pprint import PrettyPrinter
from typing import List
import pandas as pd

class Filer:
    """ A filer record """
    def __init__(self, filer_record:dict):
        self.filer_nid = filer_record['filerNid']
        self.filer_id = filer_record['registrations'].get('CA SOS')

        influences = filer_record.get('electionInfluences', [])

        filer_contest = self._get_filer_contest(influences)
        self.filer_name = filer_record['filerName']
        self.candidate_name = filer_record.get('candidateName')
        self.committee_type = filer_record['committeeTypes'][0]
        self.office, self.start_date, self.end_date, self.election_date = filer_contest


    def _get_filer_contest(self, election_influences):
        """ Get filer name and office from election_influence object """
        for i in election_influences:
            if i['candidate']:
                try:
                    office_name = i['seat']['officeName']
                except TypeError as e:
                    if e.args[0] == "'NoneType' object is not subscriptable":
                        office_name = i['candidate']['seatNid']
                    else:
                        raise e
                finally:
                    office_name = ''
                start_date = i['startDate']
                end_date = i['endDate']
                election_date = i['electionDate']

                return office_name, start_date, end_date, election_date
            elif i['measure']:
                # This currently appears to be broken/missing in the NetFile API
                return '', i['startDate'], i['endDate'], i['electionDate']

        return [ '' for _ in range(4) ]

class FilerCollection():
    """ A bunch of filer objects """
    def __init__(self, filer_records):

        self._column_dtypes = {
            'filer_nid': 'string',
            'filer_id': 'string',
            'filer_name': 'string',
            'candidate_name': 'string',
            'start_date': 'string',
            'end_date': 'string',
            'election_date': 'string'
        }
        self._collection = [ Filer(filer_record) for filer_record in filer_records ]
    @property
    def df(self):
        """ Get a Pandas DataFrame of transactions """
        filer_df = pd.DataFrame([
            f.__dict__
            for f in self._collection
        ])
        filer_df = filer_df.astype({
            'filer_nid': 'string',
            'filer_id': 'string',
            'filer_name': 'string',
            'committee_type':'string',
            'office': 'string',
            'candidate_name': 'string',
            'start_date': 'string',
            'end_date': 'string',
            'election_date': 'string'
        })
        filer_df['start_date'] = pd.to_datetime(filer_df['start_date'])
        filer_df['end_date'] = pd.to_datetime(filer_df['end_date'])
        filer_df['election_date'] = pd.to_datetime(filer_df['election_date'])

        return filer_df
