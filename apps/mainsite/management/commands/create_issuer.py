from django.core.management.base import BaseCommand

from issuer.models import Issuer
from mainsite.models import BadgrApp
from badgeuser.models import BadgeUser


class Command(BaseCommand):
    """
    Create a Issuer 
    """
    help = 'Create a defualt issuer'

    def add_arguments(self, parser):
        """
        Arguments for the mangaement command
        """
        parser.add_argument('entity_id',
                            action='store',
                            help='Issuer Slug')
        parser.add_argument('--create-name',
                            action='store',
                            dest='name',
                            help='Name of the Issuer')
        parser.add_argument('--username',
                            action='store',
                            help='Created by user')
        parser.add_argument('--url',
                            action='store',
                            dest='url',
                            help='Issuer URL')
        parser.add_argument('--badgrapp-name',
                            action='store',
                            dest='badgrapp_name',
                            help='Name of the badgr app')
        parser.add_argument('--verified',
                            action='store_true',
                            dest='verified',
                            help='Verified Status')
        parser.add_argument('--update',
                            action='store_true',
                            dest='update',
                            help='If App already exist, update values.')

    def _create_issuer(self, name, issuer_data):
        """
        Create a new Issuer
        """
        issuer_app = Issuer.objects.create(
            name=name, **issuer_data
        )
        self.stdout.write(f'Created {issuer_app.name} Issuer')
        return issuer_app

    def _update_issuer(self, issuer_app, issuer_data):
        """
        Update given Issuer with the updated data
        """
        for key, value in issuer_data.items():
            setattr(issuer_app, key, value)
        issuer_app.save()
        self.stdout.write(f'Updated {issuer_app.name} Issuer')

    def handle(self, *args, **options):
        """
        Create or Update Issuer
        """
        update = options['update']
        username = options['username']
        name = options['name']

        badgrapp = BadgrApp.objects.filter(name=options['badgrapp_name']).first()

        issuer_data = dict(
            url=options['url'],
            badgrapp=badgrapp,
            entity_id=options['entity_id'],
            verified=options['verified'],
        )

        if username:
            badgeuser = BadgeUser.objects.filter(username=username).first()
            issuer_data['created_by'] = badgeuser

        issuer = Issuer.objects.filter(entity_id=options['entity_id']).first()
        if issuer and update:
            self._update_issuer(issuer, issuer_data)
            self.stdout.write(self.style.SUCCESS(f'Successfully Updated Issuer with id {issuer.id}'))
        elif issuer:
            self.stdout.write(f'The issuer with the given name: {issuer.name} already exists')
        else:
            # Create a Issuer
            issuer = self._create_issuer(name, issuer_data)
            self.stdout.write(self.style.SUCCESS(f'Successfully Created Issuer with id {issuer.id}'))
