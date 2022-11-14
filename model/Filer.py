""" classes for Filer and FilerCollection
    each capable of returning a Pandas DataFrame
"""
from datetime import datetime as dt

class Filer:
    """ A filer record """
    def __init__(self, filer_record:dict):
        self.filer_nid = filer_record['filerNid']
        self.filer_id = filer_record['registrations'].get('CA SOS')

        influence = filer_record['electionInfluence']
        self.filer_name, self.office = self.get_filer_name(influence)
        self.start_date = influence['startDate']
        self.end_date = influence['endDate']
        self.election_year = dt.strptime(influence['electionDate'], '%Y-%m-%d').year

    def get_filer_name(self, election_influence):
        """ Get filer name and office from election_influence object """
        if election_influence['candidate']:
            filer_name = election_influence['candidate']['candidateName']
            office = election_influence['seat']['officeName']
            return filer_name, office
        elif election_influence['measure']:
            # This currently appears to be broken/missing in the NetFile API
            return None, None
