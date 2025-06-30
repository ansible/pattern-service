"""
URL configuration for pattern_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from pattern_service.core import urls as core_urls
from pattern_service.core.views import (
    ResourceStateDetail,
    ResourceStateList,
    ping,
    test,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/pattern-service/v1/", include(core_urls)),
    path("ping/", ping),
    path("api/pattern-service/v1/test/", test),
    path(
        "api/pattern-service/v1/resource_state/", ResourceStateList.as_view()
    ),
    path(
        "api/pattern-service/v1/resource_state/<int:pk>/",
        ResourceStateDetail.as_view(),
    ),
]
