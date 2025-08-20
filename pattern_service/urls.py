"""
URL configuration for the pattern_service project.
"""

from ansible_base.lib.dynamic_config.dynamic_urls import api_urls
from ansible_base.lib.dynamic_config.dynamic_urls import api_version_urls
from ansible_base.lib.dynamic_config.dynamic_urls import root_urls
from django.contrib import admin
from django.urls import include
from django.urls import path

from core.views import ping
from core.views import test

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/pattern-service/v1/", include("core.urls")),
    path("api/pattern-service/v1/", include(api_version_urls)),
    path("api/pattern-service/", include(api_urls)),
    path("", include(root_urls)),
    path("ping/", ping),
    path("api/pattern-service/v1/test/", test),
]
