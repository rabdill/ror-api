import json
import zipfile
from rorapi.settings import ES, ES_VARS, GRID

from django.core.management.base import BaseCommand
from elasticsearch import TransportError


class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def handle(self, *args, **options):
        # make sure ROR JSON file exists
        if not zipfile.is_zipfile(GRID['ROR_ZIP_PATH']):
            self.stdout.write('ROR dataset for GRID version {} not found. Please run the upgrade command first.'
                    .format(GRID['VERSION']))
            return

        with zipfile.ZipFile(GRID['ROR_ZIP_PATH'], 'r') as zip_ref:
            zip_ref.extractall(GRID['DIR'])
        
        with open(GRID['ROR_JSON_PATH'], 'r') as it:
            dataset = json.load(it)

        self.stdout.write('Indexing ROR dataset')

        index = ES_VARS['INDEX']
        backup_index = '{}-tmp'.format(index)
        ES.reindex(body={'source': {'index': index},
                         'dest': {'index': backup_index}})

        try:
            for i in range(0, len(dataset), ES_VARS['BATCH_SIZE']):
                body = []
                for org in dataset[i:i+ES_VARS['BATCH_SIZE']]:
                    body.append({'index': {'_index': index,
                                           '_type': 'org',
                                           '_id': org['id']}})
                    body.append(org)
                ES.bulk(body)
        except TransportError:
            ES.reindex(body={'source': {'index': backup_index},
                             'dest': {'index': index}})

        if ES.indices.exists(backup_index):
            ES.indices.delete(backup_index)
        self.stdout.write('ROR dataset indexed')
