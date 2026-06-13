from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from task_app.models import UserPreferences


class APIKeyAuthentication(BaseAuthentication):
    """Accept requests that carry a valid API key in the X-API-Key header."""

    keyword = 'X-API-Key'

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        try:
            prefs = UserPreferences.objects.select_related('user').get(api_key=api_key)
        except UserPreferences.DoesNotExist:
            raise AuthenticationFailed('Invalid API key.')
        return (prefs.user, api_key)

    def authenticate_header(self, request):
        # Return the challenge header only when the client actually sent a key.
        # This keeps unauthenticated (no-key) requests at 403 while invalid-key
        # requests correctly receive 401.
        if request.META.get('HTTP_X_API_KEY'):
            return self.keyword
        return None
