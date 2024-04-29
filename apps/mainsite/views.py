import base64
import time


from allauth.account.models import EmailAddress
from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.sessions.models import Session
from django.urls import reverse_lazy
from django.db import IntegrityError
from django.http import HttpResponseServerError, HttpResponseNotFound, HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import FormView, RedirectView
from oauth2_provider.views import TokenView as OAuth2ProviderTokenView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import permission_classes, authentication_classes, api_view
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from urllib.parse import quote
import jwt

from issuer.tasks import rebake_all_assertions, update_issuedon_all_assertions
from mainsite.admin_actions import clear_cache
from mainsite.models import EmailBlacklist, BadgrApp
from mainsite.serializers import LegacyVerifiedAuthTokenSerializer
import badgrlog

from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import DefaultStorage

import uuid
from django.http import JsonResponse
import requests
from requests_oauthlib import OAuth1
from .utils import generate_random_password
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from badgeuser.models import BadgeUser
from badgeuser.backends import CustomSessionAuthentication


import logging;
logger = logging.getLogger(__name__)

##
#
#  Error Handler Views
#
##
@xframe_options_exempt
def error404(request, *args, **kwargs):
    try:
        template = loader.get_template('error/404.html')
    except TemplateDoesNotExist:
        return HttpResponseServerError('<h1>Pagse not found (404)</h1>', content_type='text/html')
    return HttpResponseNotFound(template.render({
        'STATIC_URL': getattr(settings, 'STATIC_URL', '/static/'),
    }))


@login_required
def frontend_redirect(request):
    url = f'{settings.BADGR_UI_HOST_URL}/public/start/?is-lms-redirect=true'
    secret = request.COOKIES.get('edx-jwt-cookie-signature')
    url = f'{url}&secret={secret}' if secret else url
    badgr_session_id = request.COOKIES.get('badgr_session_id')
    url = f'{url}&si={badgr_session_id}' if badgr_session_id else url

    return redirect(url)


def authenticate_lms_user(request):
    token = request.headers.get('Authorization')

    if not token:
        return False
    
    try:
        decoded_data = jwt.decode(token, options={"verify_signature": False})
        email = decoded_data.get('email')
        if not email:
            return 

        url = f'{settings.LMS_HOST_URL}/api/badges/v1/verify-lms-token/'
        headers = {
        'Content-Type': 'application/json',
        'token': token
        }
        response = requests.request("POST", url, headers=headers, data={})

        if response.status_code != 200:
            return

        return BadgeUser.objects.filter(email=email).first()
    except jwt.ExpiredSignatureError as e:
        logger.info(e)
        return JsonResponse({'valid': False, 'error': 'Token has expired'})
    except jwt.InvalidTokenError as e:
        logger.info(e)
        return JsonResponse({'valid': False, 'error': 'Invalid token'})
    except Exception as e:
        logger.info(e)
    

class LMSTokenAuthnticater(OAuth2ProviderTokenView):
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):
        user = authenticate_lms_user(request=request)

        if not user:
            return JsonResponse(data={'error': 'Invalid request'}, status=400)
        
        user_email, is_created = EmailAddress.objects.get_or_create(email=user.email, user=user)
        if is_created:
            user_email.verified = True
            user_email.primary = True
            user_email.save()

        password = generate_random_password()
        user.set_password(password)
        user.save()

        request._body = f'{request.body.decode()}&username={quote(user.username)}&password={quote(password)}'

        return super(LMSTokenAuthnticater, self).post(request, *args, **kwargs)


class BadgrSessionAuthenticator(APIView):
    authentication_classes = [CustomSessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        badgr_session_id = request.COOKIES.get('badgr_session_id')
        print(f"\n\n badgr_session_id : {badgr_session_id}")
        try:
            session = Session.objects.get(session_key=badgr_session_id)
            print(f"\n\n session : {session}")
            if session.expire_date < timezone.now():
                print(f"\n\n session.expire_date < timezone.now() : {True}")
                return JsonResponse({"error": "Session has expired"}, status=403)
        except Session.DoesNotExist:
            print(f"\n\n Session.DoesNotExist ::::::")
            return JsonResponse({"error": "Session does not exists"}, status=403)

        session_data = session.get_decoded()
        print(f"\n\n session_data : {session_data}")
        user = BadgeUser.objects.filter(id=session_data["_auth_user_id"]).first()
        print(f"\n\n user : {user}")
        if not user:
            return JsonResponse(data={'error': 'Invalid request'}, status=400)
        print(f"\n user : {user} | {request.user}")
        password = generate_random_password()
        user.set_password(password)
        user.save()

        request._body = f'{request.body.decode()}&username={quote(user.username)}&password={quote(password)}'

        return super(LMSTokenAuthnticater, self).post(request, *args, **kwargs)


@xframe_options_exempt
def error500(request, *args, **kwargs):
    try:
        template = loader.get_template('error/500.html')
    except TemplateDoesNotExist:
        return HttpResponseServerError('<h1>Server Error (500)</h1>', content_type='text/html')
    return HttpResponseServerError(template.render({
        'STATIC_URL': getattr(settings, 'STATIC_URL', '/static/'),
    }))


def info_view(request, *args, **kwargs):
    return redirect(getattr(settings, 'LOGIN_REDIRECT_URL'))

@csrf_exempt
def upload(req):
    if req.method == 'POST':
        uploaded_file = req.FILES['files']
        file_extension = uploaded_file.name.split(".")[-1]
        random_filename = str(uuid.uuid4())
        final_filename = random_filename + "." + file_extension
        store = DefaultStorage()
        store.save(final_filename, uploaded_file)
    return JsonResponse({'filename': final_filename})

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def nounproject(req, searchterm, page):
    if req.method == 'GET':
        attempt_num = 0  # keep track of how many times we've retried
        while attempt_num < 4:
            auth = OAuth1(getattr(settings, 'NOUNPROJECT_API_KEY'), getattr(settings, 'NOUNPROJECT_SECRET'))
            endpoint = "http://api.thenounproject.com/icons/"+ searchterm +"?limit=10&page="+page
            response = requests.get(endpoint, auth=auth)
            if response.status_code == 200:
                data = response.json()
                return JsonResponse(data, status=status.HTTP_200_OK)
            else:
                attempt_num += 1
                # You can probably use a logger to log the error here
                time.sleep(5)  # Wait for 5 seconds before re-trying
        return JsonResponse({"error": "Request failed"}, status=response.status_code)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)


def email_unsubscribe_response(request, message, error=False):
    badgr_app_pk = request.GET.get('a', None)

    badgr_app = BadgrApp.objects.get_by_id_or_default(badgr_app_pk)

    query_param = 'infoMessage' if error else 'authError'
    redirect_url = "{url}?{query_param}={message}".format(
        url=badgr_app.ui_login_redirect,
        query_param=query_param,
        message=message)
    return HttpResponseRedirect(redirect_to=redirect_url)


def email_unsubscribe(request, *args, **kwargs):
    if time.time() > int(kwargs['expiration']):
        return email_unsubscribe_response(
            request, 'Your unsubscription link has expired.', error=True)

    try:
        email = base64.b64decode(kwargs['email_encoded']).decode("utf-8")
    except TypeError:
        logger.event(badgrlog.BlacklistUnsubscribeInvalidLinkEvent(kwargs['email_encoded']))
        return email_unsubscribe_response(request, 'Invalid unsubscribe link.',
                                          error=True)

    if not EmailBlacklist.verify_email_signature(**kwargs):
        logger.event(badgrlog.BlacklistUnsubscribeInvalidLinkEvent(email))
        return email_unsubscribe_response(request, 'Invalid unsubscribe link.',
                                          error=True)

    blacklist_instance = EmailBlacklist(email=email)
    try:
        blacklist_instance.save()
        logger.event(badgrlog.BlacklistUnsubscribeRequestSuccessEvent(email))
    except IntegrityError:
        pass
    except:
        logger.event(badgrlog.BlacklistUnsubscribeRequestFailedEvent(email))
        return email_unsubscribe_response(
            request, "Failed to unsubscribe email.",
            error=True)

    return email_unsubscribe_response(
        request, "You will no longer receive email notifications for earned"
        " badges from this domain.")


class AppleAppSiteAssociation(APIView):
    renderer_classes = (JSONRenderer,)
    permission_classes = (AllowAny,)

    def get(self, request):
        data = {
            "applinks": {
                "apps": [],
                "details": []
            }
        }

        for app_id in getattr(settings, 'APPLE_APP_IDS', []):
            data['applinks']['details'].append(app_id)

        return Response(data=data)


class LegacyLoginAndObtainAuthToken(ObtainAuthToken):
    serializer_class = LegacyVerifiedAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        response = super(LegacyLoginAndObtainAuthToken, self).post(request, *args, **kwargs)
        response.data['warning'] = 'This method of obtaining a token is deprecated and will be removed. ' \
                                   'This request has been logged.'
        return response


class SitewideActionForm(forms.Form):
    ACTION_CLEAR_CACHE = 'CLEAR_CACHE'
    ACTION_REBAKE_ALL_ASSERTIONS = "REBAKE_ALL_ASSERTIONS"
    ACTION_FIX_ISSUEDON = 'FIX_ISSUEDON'

    ACTIONS = {
        ACTION_CLEAR_CACHE: clear_cache,
        ACTION_REBAKE_ALL_ASSERTIONS: rebake_all_assertions,
        ACTION_FIX_ISSUEDON: update_issuedon_all_assertions,
    }
    CHOICES = (
        (ACTION_CLEAR_CACHE, 'Clear Cache',),
        (ACTION_REBAKE_ALL_ASSERTIONS, 'Rebake all assertions',),
        (ACTION_FIX_ISSUEDON, 'Re-process issuedOn for backpack assertions',),
    )

    action = forms.ChoiceField(choices=CHOICES, required=True, label="Pick an action")
    confirmed = forms.BooleanField(required=True, label='Are you sure you want to perform this action?')


class SitewideActionFormView(FormView):
    form_class = SitewideActionForm
    template_name = 'admin/sitewide_actions.html'
    success_url = reverse_lazy('admin:index')

    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super(SitewideActionFormView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        action = form.ACTIONS[form.cleaned_data['action']]

        if hasattr(action, 'delay'):
            action.delay()
        else:
            action()

        return super(SitewideActionFormView, self).form_valid(form)


class RedirectToUiLogin(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        badgrapp = BadgrApp.objects.get_current()
        return badgrapp.ui_login_redirect if badgrapp.ui_login_redirect is not None else badgrapp.email_confirmation_redirect


class DocsAuthorizeRedirect(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        badgrapp = BadgrApp.objects.get_current(request=self.request)
        url = badgrapp.oauth_authorization_redirect
        if not url:
            url = 'https://{cors}/auth/oauth2/authorize'.format(cors=badgrapp.cors)

        query = self.request.META.get('QUERY_STRING', '')
        if query:
            url = "{}?{}".format(url, query)
        return url
