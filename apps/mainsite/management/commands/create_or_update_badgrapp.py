from django.core.management.base import BaseCommand
from mainsite.models import BadgrApp

class Command(BaseCommand):
    """
    Create a BadgrApp 
    """
    help = 'Create a BadgrApp object'

    def add_arguments(self, parser):
        """
        Arguments for the mangaement command
        """
        parser.add_argument('name',
                            action='store',
                            help='Name of the app')
        parser.add_argument('--cors',
                            action='store',
                            dest='cors',
                            help='CORS value')
        parser.add_argument('--email-confirmation-redirect',
                            action='store',
                            dest='email_confirmation_redirect',
                            help='Email confirmation redirect URL')
        parser.add_argument('--signup-redirect',
                            action='store',
                            dest='signup_redirect',
                            help='Signup redirect URL')
        parser.add_argument('--forgot-password-redirect',
                            action='store',
                            dest='forgot_password_redirect',
                            help='Forgot password redirect URL')
        parser.add_argument('--ui-login-redirect',
                            action='store',
                            dest='ui_login_redirect',
                            help='UI redirect URL')
        parser.add_argument('--ui-signup-success-redirect',
                            action='store',
                            dest='ui_signup_success_redirect',
                            help='UI Signup success URL')
        parser.add_argument('--ui-connect-success-redirect',
                            action='store',
                            dest='ui_connect_success_redirect',
                            help='UI connect success URL')
        parser.add_argument('--ui-signup-failure-redirect',
                            action='store',
                            dest='ui_signup_failure_redirect',
                            help='UI signup failure URL')
        parser.add_argument('--public-pages-redirect',
                            action='store',
                            dest='public_pages_redirect',
                            help='Public page URL')
        parser.add_argument('--is-default',
                            action='store_true',
                            dest='is_default',
                            help='Set as default')
        parser.add_argument('--update',
                            action='store_true',
                            dest='update',
                            help='If App already exist, update values.')

    def _create_badgr_app(self, app_data):
        """
        Create new BadgrApp
        """
        badgrapp = BadgrApp.objects.create(
            **app_data
        )
        self.stdout.write('Created {} BadgrApp'.format(badgrapp.name))
        return badgrapp

    def _update_badgr_app(self, badgrapp, app_data):
        """
        Update given BadgerApp with the updated data
        """
        for key, value in app_data.items():
            setattr(badgrapp, key, value)
        badgrapp.save()
        self.stdout.write('Updated {} BadgrApp'.format(badgrapp.name))

    def handle(self, *args, **options):
        """
        Create a BadgrApp
        """

        app_data = dict(
            name=options['name'],
            cors=options['cors'],
            email_confirmation_redirect=options['email_confirmation_redirect'],
            signup_redirect=options['signup_redirect'],
            forgot_password_redirect=options['forgot_password_redirect'],
            ui_login_redirect=options['ui_login_redirect'],
            ui_signup_success_redirect=options['ui_signup_success_redirect'],
            ui_connect_success_redirect=options['ui_connect_success_redirect'],
            ui_signup_failure_redirect=options['ui_signup_failure_redirect'],
            public_pages_redirect=options['public_pages_redirect'],
            is_default=options['is_default'],
        )

        update = options['update']

        badgrapp = BadgrApp.objects.filter(name=app_data['name']).first()
        if badgrapp and update:
            self._update_badgr_app(badgrapp, app_data)
            self.stdout.write(self.style.SUCCESS(f'Successfully Updated BadgrApp with id {badgrapp.id}'))
        elif badgrapp:
            self.stdout.write('The application with the given name: {} already exists'.format(badgrapp.name))
        else:
            # Create a BadgrApp object
            badgrapp = self._create_badgr_app(app_data)
            self.stdout.write(self.style.SUCCESS(f'Successfully Created BadgrApp with id {badgrapp.id}'))
