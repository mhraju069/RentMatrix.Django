from rest_framework.response import Response
from apps.currency_and_language.models import UserPreference
from apps.currency_and_language.translation import translate_message

class ResponseTranslationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # We translate only DRF Response objects that contain dictionary data
        if isinstance(response, Response) and isinstance(response.data, dict):
            # 1. Determine active language
            lang = 'en'
            if request.user and request.user.is_authenticated:
                try:
                    pref = UserPreference.objects.select_related('language').get(user=request.user)
                    if pref.language:
                        lang = pref.language.code
                except UserPreference.DoesNotExist:
                    pass
            else:
                # Fallback to Accept-Language header for unauthenticated users
                accept_lang = request.headers.get('Accept-Language', '')
                if 'ar' in accept_lang.lower():
                    lang = 'ar'

            # 2. Check and translate the 'message' key
            msg = response.data.get('message')
            if msg and isinstance(msg, str):
                response.data['message'] = translate_message(msg, lang)
                
                # Re-render to update the response content (since DRF Response renders to string lazily or already did)
                if hasattr(response, 'render') and callable(response.render):
                    response.content = None
                    try:
                        response.render()
                    except Exception:
                        pass

        return response
