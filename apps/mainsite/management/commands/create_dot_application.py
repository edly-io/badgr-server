import logging

from django.core.management.base import BaseCommand

from mainsite.models import BadgrApp, ApplicationInfo
from oauth2_provider.models import Application


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Creates a Django OAuth Toolkit (DOT) Application Instance.
    """
    help = "Creates a Django OAuth Toolkit (DOT) Application Instance."

    def add_arguments(self, parser):
        grant_type_choices = [grant_type[0] for grant_type in Application.GRANT_TYPES]
        parser.add_argument('name',
                            action='store',
                            help='The name of this DOT Application')
        parser.add_argument('--username',
                            action='store',
                            default='',
                            help='Username')
        parser.add_argument('--grant-type',
                            action='store',
                            dest='grant_type',
                            default=Application.GRANT_CLIENT_CREDENTIALS,
                            choices=grant_type_choices,
                            help='The type of authorization this application can grant')
        parser.add_argument('--redirect-uris',
                            action='store',
                            dest='redirect_uris',
                            default='',
                            help='The redirect URI(s) for this application.  Multiple URIs should be space separated.')
        parser.add_argument('--public',
                            action='store_true',
                            dest='public',
                            default=False,
                            help='Make the application public?  Confidential by default.')
        parser.add_argument('--skip-authorization',
                            action='store_true',
                            dest='skip_authorization',
                            help='Skip the in-browser user authorization?  False by default.')
        parser.add_argument('--client-id',
                            action='store',
                            dest='client_id',
                            default='',
                            help='The client_id for this application. If omitted, one will be generated.')
        parser.add_argument('--client-secret',
                            action='store',
                            dest='client_secret',
                            default='',
                            help='The client_secret for this application. If omitted, one will be generated.')
        parser.add_argument('--scopes',
                            action='store',
                            dest='scopes',
                            default='',
                            help='Comma-separated list of scopes that this application will be allowed to request.')
        parser.add_argument('--update',
                            action='store_true',
                            dest='update',
                            help='If application and/or access already exist, update values.')

    def _create_application(self, app_name, application_kwargs):
        """
        Create new application with given User, name, and option values.
        """
        application = Application.objects.create(
            name=app_name, **application_kwargs
        )
        self.stdout.write(self.style.SUCCESS('Created {} application with id: {}, client_id: {}, and client_secret: {}'.format(
            app_name,
            application.id,
            application.client_id,
            application.client_secret,
        )))
        return application

    def _update_application(self, application, application_kwargs):
        """
        Update given application with option values.
        """
        for key, value in application_kwargs.items():
            setattr(application, key, value)
        application.save()
        self.stdout.write(self.style.SUCCESS('Updated {} application with id: {}, client_id: {}, and client_secret: {}'.format(
            application.name,
            application.id,
            application.client_id,
            application.client_secret,
        )))

    def _create_or_update_access(self, application, scopes, update):
        """
        Create application access with specified scopes.

        If application access already exists, then:
          * Update with specified scopes if update=True,
          * Otherwise do nothing.
        """
        access = ApplicationInfo.objects.filter(application_id=application.id).first()

        if access and update:
            access.allowed_scopes = scopes
            access.save()
            self.stdout.write('Updated application access for {} with scopes: {}'.format(
                application.name,
                scopes,
            ))
        elif access:
            self.stdout.write('Application access for application {} already exists.'.format(
                application.name,
            ))
        else:
            application_info = ApplicationInfo.objects.create(
                application_id=application.id,
                allowed_scopes=scopes,
            )
            self.stdout.write('Created application access for {} with scopes: {}'.format(
                application.name,
                application_info.allowed_scopes,
            ))

    def handle(self, *args, **options):
        username = options['username']
        app_name = options['name']
        update = options['update']

        redirect_uris = options['redirect_uris']
        client_type = Application.CLIENT_PUBLIC if options['public'] else Application.CLIENT_CONFIDENTIAL
        grant_type = options['grant_type']
        skip_authorization = options['skip_authorization']
        client_id = options['client_id']
        client_secret = options['client_secret']

        application_kwargs = dict(
            redirect_uris=redirect_uris,
            client_type=client_type,
            authorization_grant_type=grant_type,
            skip_authorization=skip_authorization
        )
        if client_id:
            application_kwargs['client_id'] = client_id
        if client_secret:
            application_kwargs['client_secret'] = client_secret

        application = Application.objects.filter(name=app_name).first()
        if application and update:
            self._update_application(application, application_kwargs)
        elif application:
            self.stdout.write('Application with name {} and user {} already exists.'.format(
                app_name,
                username
            ))
        else:
            application = self._create_application(app_name, application_kwargs)

        scopes = options['scopes']
        if scopes:
            self._create_or_update_access(application, scopes, update)
