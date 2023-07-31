""" classes for Filer and FilerCollection
    each capable of returning a Pandas DataFrame
"""
from datetime import datetime as dt
from pprint import PrettyPrinter
from typing import List
import pandas as pd
import polars as pl
from .base import BaseModelCollection

class Filer:
    """ A filer record """
    def __init__(self, filer_record:dict):
        self.filer_nid = filer_record['filerNid']
        self.filer_id = filer_record['registrations'].get('CA SOS')

        influences = filer_record.get('electionInfluences')

        filer_contest = self._get_filer_contest(influences)
        self.filer_name, self.office, self.start_date, self.end_date, self.election_date = filer_contest


    def _get_filer_contest(self, election_influences):
        """ Get filer name and office from election_influence object """
        for i in election_influences:
            if i['candidate']:
                candidate_name = i['candidate']['candidateName']

                try:
                    office_name = i['seat']['officeName']
                except TypeError as e:
                    if e.args[0] == "'NoneType' object is not subscriptable":
                        office_name = i['candidate']['seatNid']
                    else:
                        raise e
                finally:
                    office_name = None
                start_date = i['startDate']
                end_date = i['endDate']
                election_date = i['electionDate']

                return candidate_name, office_name, start_date, end_date, election_date
            elif i['measure']:
                # This currently appears to be broken/missing in the NetFile API
                return None, None, i['startDate'], i['endDate'], i['electionDate']

        return [ None for _ in range(5) ]

class FilerCollection(BaseModelCollection):
    """ A bunch of filer objects """
    @property
    def df(self):
        if self._df.empty:
            self._df = pd.DataFrame([
                filer.__dict__
                for filer in self.collection
            ]).astype({
                'filer_nid': 'string',
                'filer_id': 'string',
                'filer_name': 'string',
                'start_date': 'datetime64',
                'end_date': 'datetime64',
                'election_date': 'datetime64'
            })

        return self._df

    def pl(self):
        if self._pl.is_empty():
            self._pl = pl.DataFrame([
                filer.__dict__
                for filer in self.collection
            ])
