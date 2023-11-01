""" transaction models """
import pandas as pd

OAKLAND_MISSPELLINGS = [
    'OAKLAND',
    'OakLand',
    'Oaklalnd',
    'Oaklannd',
    'Okaland',
    'oakland'
]

class Transaction:
    """ A transaction record """
    def __init__(self, transaction_record: dict):
        transaction_model = (
            transaction_record.get('transaction')
            or transaction_record.get('elementModel')
        )

        self.element_nid = transaction_record['elementNid']
        self.tran_id = transaction_model['tranId']
        self.filing_nid = transaction_record['filingNid']

        transactor_first_name = transaction_model['tranNamF'] or ''
        transactor_last_name = transaction_model['tranNamL'] or ''
        contributor_name = (
            transaction_record.get('allNames')
            or f'{transactor_first_name} {transactor_last_name}'.strip())
        self.contributor_name = contributor_name

        self.contributor_type = ('Individual'
            if transaction_model['entityCd'] == 'IND'
            else 'Organization')
        self.contributor_category = self._get_contrib_category(transaction_model['entityCd'])
        self.contributor_location = None
        self.amount = transaction_model['tranAmt1']
        self.receipt_date = transaction_model['tranDate']
        self.expn_code = transaction_model['tranCode']
        self.expenditure_description = transaction_model['tranDscr'] or ''
        self.form = transaction_model['calTransactionType']
        self.party = None

        self.contributor_address = None
        self.city = None
        self.state = None
        self.zip_code = None
        self.contributor_region = None

        self._set_address_fields(transaction_model)
        self._set_contributor_region()

    def _set_address_fields(self, transaction_model: dict) -> None:
        """ Get street address from addresses, or return empty string
            Expects address dicts in the form
            {
                line1
                line2
                city
                state
                zip
            }
        """
        street = (
            f'{transaction_model.get("tranAdr1") or ""}'
            f' {transaction_model.get("tranAdr2") or ""}'
        ).strip()
        self.city = (
            'Oakland'
            if (city := transaction_model.get('tranCity')) in OAKLAND_MISSPELLINGS
            else city
        )
        self.state = transaction_model['tranST']
        self.zip_code = transaction_model['tranZip4']
        city_state_zip = ' '.join([
            city or '', transaction_model['tranST'] or '',
            transaction_model['tranZip4'] or ''
        ]).strip()
        self.contributor_address = f'{street}, {city_state_zip}' if (street and city_state_zip) else ''

    def _set_contributor_region(self) -> str:
        """ Get location relative to Oakland, CA
            from address city & state
        """
        if self.city == 'Oakland':
            self.contributor_region = 'In Oakland'
        if self.state == 'CA':
            self.contributor_region = 'Other CA City'
        self.contributor_region = 'Out of State'

    def _get_contrib_category(self, entity_code):
        """ Translate three-letter entityCd into human readable entity code """
        return {
            'RCP': 'Committee',
            'IND': 'Individual',
            'OTH': 'Business/Other',
            'COM': 'Committee',
            'PTY': 'Political Party',
            'SCC': 'Small Contributor Committee'
        }.get(entity_code)

missing_element_model = []

def get_missing_element_model():
    return missing_element_model

class UnitemizedTransaction(Transaction):
    """ Fit 'UnItemized' filing_element to Transaction """
    def __init__(self, filing_element: dict):
        try:
            transaction_record = {
                **filing_element,
                'transaction': {
                    'tranId': 'Unitemized',
                    'entityCd': 'Unitemized',
                    'tranDate': filing_element['elementModel']['calculatedDate'],
                    'tranCode': 'Unitemized',
                    'tranDscr': 'Unitemized',
                    'tranNamF': '',
                    'tranNamL': 'Unitemized',
                    'tranAdr1': 'Unitemized',
                    'tranAdr2': 'Unitemized',
                    'tranCity': 'Unitemized',
                    'tranST': 'Unitemized',
                    'tranZip4': 'Unitemized',
                    'tranAmt1': filing_element['elementModel']['amount'],
                    'calTransactionType': filing_element['specificationRef']['name']
                }
            }
            super().__init__(transaction_record)

            self.contributor_address = 'Unitemized'
            self.city = ''
            self.state = ''
            self.zip_code = ''
            self.contributor_region = 'Unitemized'

            self.contributor_category = 'Unitemized'
            self.contributor_type = 'Unitemized'
            self.contributor_name = ''

        except KeyError:
            missing_element_model.append(filing_element)

class TransactionCollection:
    """ A bunch of transactions all in one place """
    def __init__(self, transactions: list[Transaction]):
        self.transactions = transactions

    @property
    def df(self):
        """ Get a Pandas DataFrame of transactions """
        tran_df = pd.DataFrame([
            t.__dict__
            for t in self.transactions
        ])
        tran_df = tran_df.astype({
            'element_nid': 'string',
            'tran_id': 'string',
            'filing_nid': 'string',
            'contributor_name': 'string',
            'contributor_type': 'string',
            'contributor_category': 'string',
            'contributor_location': 'string',
            'amount': 'float32',
            'receipt_date': 'string',
            'expn_code': 'string',
            'expenditure_description': 'string',
            'form': 'string',
            'party': 'string',
            'contributor_address': 'string',
            'city': 'string',
            'state': 'string',
            'zip_code': 'string',
            'contributor_region': 'string',
        })
        tran_df['receipt_date'] = pd.to_datetime(tran_df['receipt_date'])

        return tran_df
