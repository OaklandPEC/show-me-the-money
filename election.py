""" Link candidates to elections
"""
import json
import argparse
from pathlib import Path
from pprint import PrettyPrinter
from v2api.query_v2_api import list_elections

pp = PrettyPrinter()

def get_elections_data(download:bool):
    """ Retrieve elections data from local or NetFile API """
    local_data_path = Path('example/elections.json')
    if download:
        elections = list_elections()
        local_data_path.write_text(json.dumps(elections), encoding='utf8')
        return elections
    else:
        return json.loads(local_data_path.read_text(encoding='utf8'))

def get_unique_elections(download:bool, elections:list[dict]):
    """ Get dict of unique elections
    - by extracting it from fetched data, if download
    - by loading it from local, if not download
    """
    uniq_elections_path = Path('example/election_nids.json')
    if download:
        uniq_elections = {
            e['electionDate']: e['electionNid']
            for e in elections
        }
        elec_dates = sorted(list(uniq_elections.keys()))
        uniq_elections = { d: uniq_elections[d] for d in elec_dates }

        uniq_elections_path.write_text(json.dumps(uniq_elections), encoding='utf8')
        return uniq_elections
    else:
        return json.loads(uniq_elections_path.read_text(encoding='utf8'))

def main(download:bool):
    """ Link elections to candidates """
    res = get_elections_data(download)

    elec_codes = { e['electionCodes'] for e in res }

    elections = get_unique_elections(download, res)

    print('Current election candidates')
    # Election dates are in the format 'yyyy-mm-dd'
    cur_elec = [
        e for e in res
        if e['electionDate'] == '2022-11-08'
    ][0]
    pp.pprint(cur_elec['candidates'])

    print('Are there any winners?')
    winners = [
        c for c in cur_elec['candidates']
        if c['isWinner'] is True
    ]
    print(winners)

    print('Are filers linked to candidateNids?')
    filers = json.loads(Path('example/filers.json').read_text(encoding='utf8'))
    pp.pprint(filers[0]['electionInfluences'])

    print('What does a ballot measures electioInfluence look like?')
    measure_filer = [
        f for f in filers
        if 'Yes on W' in ' '.join([ ei['committeeName'] for ei in f['electionInfluences'] ])
    ]
    pp.pprint(measure_filer)

    print('What are the unique values of committeeTypes?')
    committee_type = {
        c for f in filers
        for c in f['committeeTypes']
    }
    print(committee_type)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', '-d', action='store_true', default=False)

    ns = parser.parse_args()

    main(download=ns.download)