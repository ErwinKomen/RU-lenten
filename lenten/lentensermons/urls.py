"""
Definition of urls for lenten.
"""

from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import include, url
from django.contrib import admin
import django.contrib.auth.views

import lentensermons.seeker.forms
import lentensermons.seeker.views
from lentensermons.seeker.views import *

# Import from LENTENSERMONS as a whole
from lentensermons.settings import APP_PREFIX

# Other Django stuff
from django.core import urlresolvers
from django.shortcuts import redirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic.base import RedirectView

admin.autodiscover()


# Set admin stie information
admin.site.site_header = "Lenten sermons"
admin.site.site_title = "lentensermons Admin"

pfx = APP_PREFIX

urlpatterns = [
    # Examples:
    url(r'^$', lentensermons.seeker.views.home, name='home'),
    url(r'^contact$', lentensermons.seeker.views.contact, name='contact'),
    url(r'^about', lentensermons.seeker.views.about, name='about'),
    url(r'^short', lentensermons.seeker.views.about, name='short'),
    url(r'^nlogin', lentensermons.seeker.views.nlogin, name='nlogin'),

    url(r'^api/tagtext/', lentensermons.seeker.views.get_tributes, name='api_tributes'),

    url(r'^location/list', LocationListView.as_view(), name='location_list'),
    url(r'^location/details(?:/(?P<pk>\d+))?/$', LocationDetailsView.as_view(), name='location_details'),
    url(r'^location/edit(?:/(?P<pk>\d+))?/$', LocationEdit.as_view(), name='location_edit'),
    url(r'^location/relset(?:/(?P<pk>\d+))?/$', LocationRelset.as_view(), name='loc_relset'),

    url(r'^author/list',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/author'), name='author_list'),

    url(r'^sermon/list',  SermonListView.as_view(), name='sermon_list'),
    # url(r'^sermon/list',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/sermon'), name='sermon_list'),
    url(r'^sermon/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/sermon/add'), name='sermon_add'),
    url(r'^sermon/view(?:/(?P<pk>\d+))?/$', SermonDetailsView.as_view(), name='sermon_details'),

    url(r'^collection/list',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/sermoncollection'), name='collection_list'),

    url(r'^manuscript/list',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/manuscript'), name='manuscript_list'),

    url(r'^edition/list',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/edition'), name='edition_list'),

    url(r'^report/list', ReportListView.as_view(), name='report_list'),
    url(r'^report/details(?:/(?P<pk>\d+))?/$', ReportDetailsView.as_view(), name='report_details'),

    # For working with ModelWidgets from the select2 package https://django-select2.readthedocs.io
    url(r'^select2/', include('django_select2.urls')),

    url(r'^definitions$', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    url(r'^signup/$', lentensermons.seeker.views.signup, name='signup'),

    url(r'^login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'login.html',
            'authentication_form': lentensermons.seeker.forms.BootstrapAuthenticationForm,
            'extra_context':
            {
                'title': 'Log in',
                'year': datetime.now().year,
            }
        },
        name='login'),
    url(r'^logout$',
        django.contrib.auth.views.logout,
        {
            'next_page':  reverse_lazy('home'),
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls), name='admin_base'),
]
