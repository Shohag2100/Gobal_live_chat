from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.http import HttpResponse
from django.conf.urls.static import static


def _debug_settings(request):
    # Temporary debugging endpoint to show which settings the server is using
    module = getattr(settings, '__module__', None)
    source = getattr(settings, '__file__', 'no-file')
    import os
    env = os.environ.get('DJANGO_SETTINGS_MODULE')
    core_info = None
    try:
        import importlib
        cs = importlib.import_module('core.settings')
        core_info = f"core.settings.__file__={getattr(cs, '__file__', None)}\ncore.INSTALLED_APPS={getattr(cs, 'INSTALLED_APPS', None)}\ncore.TEMPLATES={getattr(cs, 'TEMPLATES', None)}\n"
    except Exception as e:
        core_info = f"core.settings import error: {e}\n"

    text = (
        f"DJANGO_SETTINGS_MODULE_ENV={env}\nsettings.__module__={module}\nsettings.__file__={source}\n"
        f"TEMPLATES={settings.TEMPLATES}\nINSTALLED_APPS={settings.INSTALLED_APPS}\nTEMPLATE_DIRS={settings.TEMPLATES[0].get('DIRS')}\n\n{core_info}"
    )
    return HttpResponse(text, content_type='text/plain')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),
    path('', TemplateView.as_view(template_name='welcome.html'), name='home'),  # THIS LINE IS KEY
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)