""" classes for Filer and FilerCollection
    each capable of returning a Pandas DataFrame
"""
from datetime import datetime as dt
from pprint import PrettyPrinter
from typing import List
import pandas as pd
from .base import BaseModelCollection

class Filer:
    """ A filer record """
    def __init__(self, filer_record:dict):
        self.filer_nid = filer_record['filerNid']
        self.filer_id = filer_record['registrations'].get('CA SOS')

        influences = filer_record.get('electionInfluences', [])

        filer_contest = self._get_filer_contest(influences)
        self.filer_name = filer_record['candidateName'] if filer_record.get('candidateName') else filer_record['filerName']
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

class FilerCollection(BaseModelCollection):
    """ A bunch of filer objects """
    def __init__(self, filer_records):
        super().__init__(filer_records)
        self._column_dtypes = {
            'filer_nid': 'string',
            'filer_id': 'string',
            'filer_name': 'string',
            'start_date': 'datetime64[ns]',
            'end_date': 'datetime64[ns]',
            'election_date': 'datetime64[ns]'
        }
        self._collection = [ Filer(filer_record) for filer_record in filer_records ]
