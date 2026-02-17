"""
Definition of urls for lenten.
"""

from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import path, re_path, include
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
    re_path(r'^$', lentensermons.seeker.views.home, name='home'),
    re_path(r'^contact$', lentensermons.seeker.views.contact, name='contact'),
    re_path(r'^instruction$', lentensermons.seeker.views.instruction, name='instruction'),
    re_path(r'^about', lentensermons.seeker.views.about, name='about'),
    re_path(r'^short', lentensermons.seeker.views.about, name='short'),
    re_path(r'^nlogin', lentensermons.seeker.views.nlogin, name='nlogin'),

    re_path(r'^api/tagtext/', lentensermons.seeker.views.get_tributes, name='api_tributes'),
    re_path(r'^api/params/', lentensermons.seeker.views.get_params, name='api_params'),

    re_path(r'^location/list', LocationListView.as_view(), name='location_list'),
    re_path(r'^location/details(?:/(?P<pk>\d+))?/$', LocationDetailsView.as_view(), name='location_details'),
    re_path(r'^location/edit(?:/(?P<pk>\d+))?/$', LocationEdit.as_view(), name='location_edit'),
    re_path(r'^location/relset(?:/(?P<pk>\d+))?/$', LocationRelset.as_view(), name='loc_relset'),

    re_path(r'^author/list',  AuthorListView.as_view(), name='author_list'),
    re_path(r'^author/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/author/add'), name='author_add'),
    re_path(r'^author/view(?:/(?P<pk>\d+))?/$', AuthorDetailsView.as_view(), name='author_details'),

    # re_path(r'^sermon/list',  SermonListView.as_view(), name='sermon_list'),
    re_path(r'^sermon/list',  SermonList.as_view(), name='sermon_list'),
    re_path(r'^sermon/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/sermon/add'), name='sermon_add'),
    re_path(r'^sermon/view(?:/(?P<pk>\d+))?/$', SermonDetailsView.as_view(), name='sermon_details'),

    re_path(r'^collection/list',  CollectionList.as_view(), name='collection_list'),
    re_path(r'^collection/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/sermoncollection/add'), name='collection_add'),
    re_path(r'^collection/view(?:/(?P<pk>\d+))?/$', CollectionDetailsView.as_view(), name='collection_details'),

    re_path(r'^manuscript/list',  ManuscriptListView.as_view(), name='manuscript_list'),
    re_path(r'^manuscript/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/manuscript/add'), name='manuscript_add'),
    re_path(r'^manuscript/view(?:/(?P<pk>\d+))?/$', ManuscriptDetailsView.as_view(), name='manuscript_details'),

    re_path(r'^edition/list',  EditionList.as_view(), name='edition_list'),
    re_path(r'^edition/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/edition/add'), name='edition_add'),
    re_path(r'^edition/view(?:/(?P<pk>\d+))?/$', EditionDetailsView.as_view(), name='edition_details'),

    re_path(r'^concept/list',  ConceptListView.as_view(), name='concept_list'),
    re_path(r'^concept/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/concept/add'), name='concept_add'),
    re_path(r'^concept/view(?:/(?P<pk>\d+))?/$', ConceptDetailsView.as_view(), name='concept_details'),

    re_path(r'^tag/group/list',  TgroupListView.as_view(), name='tgroup_list'),
    re_path(r'^tag/group/edit(?:/(?P<pk>\d+))?/$', TgroupEdit.as_view(), name='tgroup_edit'),
    re_path(r'^tag/group/view(?:/(?P<pk>\d+))?/$', TgroupDetails.as_view(), name='tgroup_details'),

    re_path(r'^tag/keyword/list',  TagKeywordListView.as_view(), name='tagkeyword_list'),
    re_path(r'^tag/keyword/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/tagkeyword/add'), name='tagkeyw_add'),
    re_path(r'^tag/keyword/view(?:/(?P<pk>\d+))?/$', TagKeywordDetailView.as_view(), name='tagkeyword_details'),

    re_path(r'^publisher/list',  PublisherListView.as_view(), name='publisher_list'),
    re_path(r'^publisher/view(?:/(?P<pk>\d+))?/$', PublisherDetailsView.as_view(), name='publisher_details'),
    re_path(r'^publisher/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/publisher/add'), name='publisher_add'),

    re_path(r'^news/list',  NewsListView.as_view(), name='newsitem_list'),
    re_path(r'^news/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/newsitem/add'), name='newsitem_add'),
    re_path(r'^news/view(?:/(?P<pk>\d+))?/$', NewsDetailsView.as_view(), name='newsitem_details'),

    re_path(r'^instruction/list',  InstructionListView.as_view(), name='instruction_list'),
    re_path(r'^instruction/edit(?:/(?P<pk>\d+))?/$', InstructionEdit.as_view(), name='instruction_edit'),
    re_path(r'^instruction/view(?:/(?P<pk>\d+))?/$', InstructionDetails.as_view(), name='instruction_details'),

    re_path(r'^reference/list',  LitrefListView.as_view(), name='litref_list'),
    re_path(r'^reference/view(?:/(?P<pk>\d+))?/$', LitrefDetailsView.as_view(), name='litref_details'),
    re_path(r'^reference/edit(?:/(?P<pk>\d+))?/$', LitrefEditView.as_view(), name='litref_edit'),

    re_path(r'^consulting/view(?:/(?P<pk>\d+))?/$', ConsultingDetailsView.as_view(), name='consulting_details'),
    re_path(r'^consulting/add',  RedirectView.as_view(url='/'+APP_PREFIX+'admin/seeker/consulting/add'), name='consulting_add'),

    re_path(r'^report/list', ReportListView.as_view(), name='report_list'),
    re_path(r'^report/details(?:/(?P<pk>\d+))?/$', ReportDetailsView.as_view(), name='report_details'),

    # For working with ModelWidgets from the select2 package https://django-select2.readthedocs.io
    re_path(r'^select2/', include('django_select2.urls')),

    re_path(r'^definitions$', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    re_path(r'^signup/$', lentensermons.seeker.views.signup, name='signup'),

    re_path(r'^login/user/(?P<user_id>\w[\w\d_]+)$', lentensermons.seeker.views.login_as_user, name='login_as'),

    re_path(r'^login/$', LoginView.as_view
        (
            template_name= 'login.html',
            authentication_form= lentensermons.seeker.forms.BootstrapAuthenticationForm,
            extra_context= {'title': 'Log in','year': datetime.now().year,}
        ),
        name='login'),
    re_path(r'^logout$',  LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),

    # Uncomment the next line to enable the admin:
    re_path(r'^admin/', admin.site.urls, name='admin_base'),
]
