# noinspection PyUnresolvedReferences
from google.oauth2.credentials import Credentials
# noinspection PyUnresolvedReferences
from google_auth_oauthlib.flow import Flow
# noinspection PyUnresolvedReferences
from googleapiclient.errors import HttpError
# noinspection PyUnresolvedReferences
from googleapiclient.discovery import build
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View
# noinspection PyUnresolvedReferences
from rest_framework.response import Response
from oauth2_provider.views.generic import ProtectedResourceView
from oauth2_provider.models import AccessToken


class GoogleCalendarInitView(View):
    def get(self, request):
        flow = Flow.from_client_config(
            settings.GOOGLE_CLIENT_CONFIG,
            scopes=['https://www.googleapis.com/auth/calendar.events.readonly'],
            redirect_uri=request.build_absolute_uri(reverse('google-calendar-redirect')),
        )
        authorization_url, _ = flow.authorization_url(prompt='consent')

        return redirect(authorization_url)


class GoogleCalendarRedirectView(View):
    def get(self, request):
        flow = Flow.from_client_config(
            settings.GOOGLE_CLIENT_CONFIG,
            scopes=['https://www.googleapis.com/auth/calendar.events.readonly'],
            redirect_uri=request.build_absolute_uri(reverse('google-calendar-redirect')),
        )
        flow.fetch_token(code=request.GET.get('code'))

        try:
            credentials = flow.credentials
            credentials_dict = credentials_to_dict(credentials)
            access_token = AccessToken.objects.create(
                user=request.user,
                token=credentials_dict['token'],
                expires_at=credentials_dict['expiry'],
                scope=' '.join(credentials_dict['scopes']),
            )
            events = get_calendar_events(credentials)
            return Response({'events': events})
        except HttpError as e:
            return Response({'error': str(e)}, status=500)


class GoogleCalendarEventsView(ProtectedResourceView):
    def get(self, request, *args, **kwargs):
        try:
            access_token = AccessToken.objects.get(user=request.user)
            credentials = Credentials.from_authorized_user_info(info=access_token.to_dict())
            events = get_calendar_events(credentials)
            return Response({'events': events})
        except (AccessToken.DoesNotExist, HttpError) as e:
            return Response({'error': str(e)}, status=500)


def get_calendar_events(credentials):
    service = build('calendar', 'v3', credentials=credentials)
    events_result = service.events().list(calendarId='primary', timeMin='2023-01-01T00:00:00Z',
                                          timeMax='2023-12-31T23:59:59Z',
                                          maxResults=20, singleEvents=True,
                                          orderBy='startTime').execute()
    return events_result.get('items', [])


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'expiry': credentials.expiry.isoformat(),
        'refresh_token': credentials.refresh_token,
        'scopes': credentials.scopes,
    }
