"""
Definition of urls for lenten.
"""

from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
import django.contrib.auth.views

import lentensermons.seeker.forms
from lentensermons.seeker.views import *

# Import from LENTENSERMONS as a whole
from lentensermons.settings import APP_PREFIX

# Other Django stuff
# from django.core import urlresolvers
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
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
    url(r'^instruction$', lentensermons.seeker.views.instruction, name='instruction'),
    url(r'^about', lentensermons.seeker.views.about, name='about'),
    url(r'^short', lentensermons.seeker.views.about, name='short'),
    url(r'^nlogin', lentensermons.seeker.views.nlogin, name='nlogin'),

    url(r'^api/tagtext/', lentensermons.seeker.views.get_tributes, name='api_tributes'),
    url(r'^api/params/', lentensermons.seeker.views.get_params, name='api_params'),

    url(r'^location/list', LocationListView.as_view(), name='location_list'),
    url(r'^location/details(?:/(?P<pk>\d+))?/$', LocationDetailsView.as_view(), name='location_details'),
    url(r'^location/edit(?:/(?P<pk>\d+))?/$', LocationEdit.as_view(), name='location_edit'),
    url(r'^location/relset(?:/(?P<pk>\d+))?/$', LocationRelset.as_view(), name='loc_relset'),

    url(r'^author/list',  AuthorListView.as_view(), name='author_list'),
    url(r'^author/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/author/add'), name='author_add'),
    url(r'^author/view(?:/(?P<pk>\d+))?/$', AuthorDetailsView.as_view(), name='author_details'),

    url(r'^sermon/list',  SermonListView.as_view(), name='sermon_list'),
    url(r'^sermon/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/sermon/add'), name='sermon_add'),
    url(r'^sermon/view(?:/(?P<pk>\d+))?/$', SermonDetailsView.as_view(), name='sermon_details'),

    url(r'^collection/list',  CollectionList.as_view(), name='collection_list'),
    url(r'^collection/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/sermoncollection/add'), name='collection_add'),
    url(r'^collection/view(?:/(?P<pk>\d+))?/$', CollectionDetailsView.as_view(), name='collection_details'),

    url(r'^manuscript/list',  ManuscriptListView.as_view(), name='manuscript_list'),
    url(r'^manuscript/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/manuscript/add'), name='manuscript_add'),
    url(r'^manuscript/view(?:/(?P<pk>\d+))?/$', ManuscriptDetailsView.as_view(), name='manuscript_details'),

    url(r'^edition/list',  EditionList.as_view(), name='edition_list'),
    url(r'^edition/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/edition/add'), name='edition_add'),
    url(r'^edition/view(?:/(?P<pk>\d+))?/$', EditionDetailsView.as_view(), name='edition_details'),

    url(r'^concept/list',  ConceptListView.as_view(), name='concept_list'),
    url(r'^concept/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/concept/add'), name='concept_add'),
    url(r'^concept/view(?:/(?P<pk>\d+))?/$', ConceptDetailsView.as_view(), name='concept_details'),

    url(r'^tag/group/list',  TgroupListView.as_view(), name='tgroup_list'),
    url(r'^tag/group/edit(?:/(?P<pk>\d+))?/$', TgroupEdit.as_view(), name='tgroup_edit'),
    url(r'^tag/group/view(?:/(?P<pk>\d+))?/$', TgroupDetails.as_view(), name='tgroup_details'),

    url(r'^tag/keyword/list',  TagKeywordListView.as_view(), name='tagkeyword_list'),
    url(r'^tag/keyword/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/tagkeyword/add'), name='tagkeyw_add'),
    url(r'^tag/keyword/view(?:/(?P<pk>\d+))?/$', TagKeywordDetailView.as_view(), name='tagkeyword_details'),

    url(r'^publisher/list',  PublisherListView.as_view(), name='publisher_list'),
    url(r'^publisher/view(?:/(?P<pk>\d+))?/$', PublisherDetailsView.as_view(), name='publisher_details'),
    url(r'^publisher/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/publisher/add'), name='publisher_add'),

    url(r'^news/list',  NewsListView.as_view(), name='newsitem_list'),
    url(r'^news/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/newsitem/add'), name='newsitem_add'),
    url(r'^news/view(?:/(?P<pk>\d+))?/$', NewsDetailsView.as_view(), name='newsitem_details'),

    url(r'^reference/list',  LitrefListView.as_view(), name='litref_list'),
    url(r'^reference/view(?:/(?P<pk>\d+))?/$', LitrefDetailsView.as_view(), name='litref_details'),
    url(r'^reference/edit(?:/(?P<pk>\d+))?/$', LitrefEditView.as_view(), name='litref_edit'),

    url(r'^consulting/view(?:/(?P<pk>\d+))?/$', ConsultingDetailsView.as_view(), name='consulting_details'),
    url(r'^consulting/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/consulting/add'), name='consulting_add'),

    url(r'^report/list', ReportListView.as_view(), name='report_list'),
    url(r'^report/details(?:/(?P<pk>\d+))?/$', ReportDetailsView.as_view(), name='report_details'),

    # For working with ModelWidgets from the select2 package https://django-select2.readthedocs.io
    url(r'^select2/', include('django_select2.urls')),

    url(r'^definitions$', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    url(r'^signup/$', lentensermons.seeker.views.signup, name='signup'),

    url(r'^login/user/(?P<user_id>\w[\w\d_]+)$', lentensermons.seeker.views.login_as_user, name='login_as'),

    url(r'^login/$', LoginView.as_view
        (
            template_name= 'login.html',
            authentication_form= lentensermons.seeker.forms.BootstrapAuthenticationForm,
            extra_context= {'title': 'Log in','year': datetime.now().year,}
        ),
        name='login'),
    url(r'^logout$',  LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),

    #url(r'^login/$',
    #    django.contrib.auth.views.login,
    #    {
    #        'template_name': 'login.html',
    #        'authentication_form': lentensermons.seeker.forms.BootstrapAuthenticationForm,
    #        'extra_context':
    #        {
    #            'title': 'Log in',
    #            'year': datetime.now().year,
    #        }
    #    },
    #    name='login'),
    #url(r'^logout$',
    #    django.contrib.auth.views.logout,
    #    {
    #        'next_page':  reverse_lazy('home'),
    #    },
    #    name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', admin.site.urls, name='admin_base'),
]
