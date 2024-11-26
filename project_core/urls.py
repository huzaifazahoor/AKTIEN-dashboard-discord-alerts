"""
URL configuration for project_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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

import os

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import include, path

from .sitemap import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("accounts/", include("authentication.urls")),
    path("stocks/", include("stocks.urls")),
    path("alerts/", include("alerts.urls")),
    path(
        "",
        lambda request: HttpResponse(
            """
        <html>
            <head>
                <title>Site Under Development</title>
                <style>
                    html, body {
                height: 100%;
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: Arial, sans-serif;
                background-color: #f3f4f6;
                color: #333;
                text-align: center;
            }

                </style>
            </head>
            <body>
                <h1>Under Development<br>Please check back soon!</h1>
            </body>
        </html>
    """,
        ),
        name="home",
    ),
    path("env/", lambda request: JsonResponse(dict(os.environ))),
    path(
        "privacy-policy/",
        lambda request: render(request, "privacy_policy.html"),
        name="privacy_policy",
    ),
    path(
        "terms-of-service/",
        lambda request: render(request, "terms_of_service.html"),
        name="terms_of_service",
    ),
    path(
        "robots.txt",
        lambda request: HttpResponse(
            open("robots.txt").read(), content_type="text/plain"
        ),
    ),
]
