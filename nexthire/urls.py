# nexthire/urls.py
"""
NextHire Smart Placement – Root URL Routing Matrix.
Configures administrative console pathways and hooks up microservice endpoints.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.http import JsonResponse

from django.shortcuts import redirect

def api_root(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    return redirect('accounts:login')


urlpatterns = [
    # Root API Gateway
    path('', api_root, name='api-root'),
    
    # Admin Interface Gateway
    path('admin/', include('admin_custom.urls', namespace='admin_custom')),
    path('admin/', admin.site.urls),
    
    # Platform Routing isolation
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('placement/', include('trainer.urls', namespace='placement')),
    path('placement/', include('trainer.urls', namespace='trainer')),
    path('student/', include('trainees.urls', namespace='students')),
    path('student/', include('trainees.urls', namespace='trainees')),
    path('trainee/', include('trainees.urls')),
    path('trainees/', include('trainees.urls')),
    path('recruiter/', include('recruiters.urls', namespace='recruiters')),
    path('jobs/', include('jobs.urls', namespace='jobs')),
    path('applications/', include('applications.urls', namespace='applications')),
    path('interviews/', include('interviews.urls', namespace='interviews')),
    # path('analytics/', include('analytics.urls', namespace='analytics')),
    # path('reports/', include('reports.urls', namespace='reports')),
    # path('resume/', include('resume.urls', namespace='resume')),
    # path('prediction/', include('prediction.urls', namespace='prediction')),
    path('ai/', include('ai.urls', namespace='ai')),
    path('ml/', include('ml_engine.urls', namespace='ml_engine')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
]

# Static assets bindings if running under DEBUG development structures
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
