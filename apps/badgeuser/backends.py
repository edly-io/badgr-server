# Created by wiggins@concentricsky.com on 9/3/15.
from allauth.account.auth_backends import AuthenticationBackend
from django.contrib.auth.backends import ModelBackend
from django.contrib.sessions.models import Session
from django.utils import timezone

from badgeuser.models import BadgeUser


class CachedModelBackend(ModelBackend):
    def get_user(self, user_id):
        try:
            return BadgeUser.cached.get(pk=user_id)
        except BadgeUser.DoesNotExist:
            return None


class CachedAuthenticationBackend(CachedModelBackend, AuthenticationBackend):
    pass


class CustomSessionAuthentication(AuthenticationBackend):
    """
    Authenticates the user using session.
    """

    def authenticate(self, request, username=None, password=None):
        badgr_session_id = request.COOKIES.get('badgr_session_id')
        try:
            session = Session.objects.get(session_key=badgr_session_id)
            if session.expire_date < timezone.now():
                return None
        except Session.DoesNotExist:
            return None

        session_data = session.get_decoded()
        try:
            user = BadgeUser.objects.filter(id=session_data["_auth_user_id"]).first()
            return user
        except BadgeUser.DoesNotExist:
            return None