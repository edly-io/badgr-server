import logging

from django.core.management.base import BaseCommand
from badgeuser.models import BadgeUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Creating a
    """
    help = "Create or Update BadgeUser"

    def add_arguments(self, parser):
        parser.add_argument('username',
                            action='store',
                            help='Username')
        parser.add_argument('--email',
                            action='store',
                            dest='email',
                            help='Email')
        parser.add_argument('--first-name',
                            action='store',
                            dest='first_name',
                            default='',
                            help='First Name')
        parser.add_argument('--last-name',
                            action='store',
                            dest='last_name',
                            default='',
                            help='Last Name')
        parser.add_argument('--password',
                            action='store',
                            dest='password',
                            default='',
                            help='Password')
        parser.add_argument('--is-active',
                            action='store_true',
                            dest='is_active',
                            help='Active User, by default to False')
        parser.add_argument('--is-staff',
                            action='store_true',
                            dest='is_staff',
                            help='Staff User, by default to False')
        parser.add_argument('--is-superuser',
                            action='store_true',
                            dest='is_superuser',
                            help='Super User, by default to False')
        parser.add_argument('--update',
                            action='store_true',
                            dest='update',
                            help='If user already exists, update values.')

    def _create_user(self, username, user_data):
        """
        Create a new user
        """
        badgeuser = BadgeUser.objects.create_user(username=username)
        for key, value in user_data.items():
            setattr(badgeuser, key, value)
        badgeuser.save()
        
        self.stdout.write(self.style.SUCCESS('Created {} user with id: {}'.format(
            username,
            badgeuser.id,
        )))
        return badgeuser

    def _update_user(self, badgeuser, user_data):
        """
        Update given user with option values.
        """
        for key, value in user_data.items():
            setattr(badgeuser, key, value)
        badgeuser.save()
        self.stdout.write(self.style.SUCCESS('Updated {} user with id: {}'.format(
            badgeuser.username,
            badgeuser.id,
        )))

    def _update_password(self, badgeuser, password):
        """
        Update badgeUser password
        """
        badgeuser.set_password(password)
        badgeuser.save()

    def handle(self, *args, **options):
        update = options['update']
        username = options['username']
        password = options['password']

        user_data = dict(
            email=options['email'],
            first_name=options['first_name'],
            last_name=options['last_name'],
            is_active=options['is_active'],
            is_staff=options['is_staff'],
            is_superuser=options['is_superuser'],
        )
        badgeuser = BadgeUser.objects.filter(username=username).first()

        if badgeuser and update:
            self._update_user(badgeuser, user_data)
        elif badgeuser:
            self.stdout.write('User with username {} already exists.'.format(
                username
            ))
        else:
            badgeuser = self._create_user(username, user_data)

        if password:
            self._update_password(badgeuser, password)
