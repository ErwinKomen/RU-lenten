"""
Definition of views for the SEEKER app.
"""

from django.contrib import admin
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q
import operator
from functools import reduce

from django.db.models.functions import Lower
from django.db.models.query import QuerySet
from django.forms import formset_factory, modelformset_factory, inlineformset_factory
from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.views.generic.detail import DetailView
from django.views.generic.base import RedirectView
from django.views.generic import ListView, View
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from time import sleep

import fnmatch
import sys, os
import base64
import json
import csv, re
from io import StringIO

# My own application
from lentensermons.basic.views import BasicList, BasicDetails

# Application specific
from lentensermons.settings import APP_PREFIX, MEDIA_DIR
from lentensermons.utils import ErrHandle
from lentensermons.seeker.forms import UploadFileForm, UploadFilesForm, SearchUrlForm, LocationForm, LocationRelForm, ReportEditForm, \
    SignUpForm, SermonListForm, CollectionListForm, EditionListForm, ConceptListForm, \
    TagKeywordListForm, PublisherListForm, NewsForm, \
    LitrefForm, AuthorListForm, TgroupForm, ManuscriptForm  # , TagQsourceListForm
from lentensermons.seeker.models import get_current_datetime, adapt_search, get_searchable, get_now_time, \
    User, Group, Action, Report, Status, NewsItem, Profile, Visit, \
    Location, LocationRelation, Author, Concept, FieldChoice, Information, \
    Sermon, SermonCollection, Edition, Manuscript, TagKeyword,  \
    Publisher, Consulting, Litref, Tgroup   # , TagQsource

# Some constants that can be used
paginateSize = 20
paginateSelect = 15
paginateValues = (100, 50, 20, 10, 5, 2, 1, )

# Global debugging 
bDebug = False

app_editor = "lentensermons_editor"
app_uploader = "lentensermons_uploader"


def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'About',
                'message':'Radboud University passim utility.',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "About", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}, {'name': 'About', 'url': reverse('about')}]

    return render(request,'about.html', context)

def action_model_changes(form, instance):
    field_values = model_to_dict(instance)
    changed_fields = form.changed_data
    changes = {}
    for item in changed_fields: 
        if item in field_values:
            changes[item] = field_values[item]
        else:
            # It is a form field
            try:
                representation = form.cleaned_data[item]
                if isinstance(representation, QuerySet):
                    # This is a list
                    rep_list = []
                    for rep in representation:
                        rep_str = str(rep)
                        rep_list.append(rep_str)
                    representation = json.dumps(rep_list)
                changes[item] = representation
            except:
                changes[item] = "(unavailable)"
    return changes

def add_visit(request, name, is_menu):
    """Add the visit to the current path"""

    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous":
        Visit.add(username, name, request.path, is_menu)

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'Contact',
                'message':'Pietro Delcorno',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "Contact", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}, {'name': 'Contact', 'url': reverse('contact')}]


    return render(request,'contact.html', context)

def csv_to_excel(sCsvData, response):
    """Convert CSV data to an Excel worksheet"""

    # Start workbook
    wb = openpyxl.Workbook()
    ws = wb.get_active_sheet()
    ws.title="Data"

    # Start accessing the string data 
    f = StringIO(sCsvData)
    reader = csv.reader(f, delimiter=",")

    # Read the header cells and make a header row in the worksheet
    headers = next(reader)
    for col_num in range(len(headers)):
        c = ws.cell(row=1, column=col_num+1)
        c.value = headers[col_num]
        c.font = openpyxl.styles.Font(bold=True)
        # Set width to a fixed size
        ws.column_dimensions[get_column_letter(col_num+1)].width = 5.0        

    row_num = 1
    lCsv = []
    for row in reader:
        # Keep track of the EXCEL row we are in
        row_num += 1
        # Walk the elements in the data row
        # oRow = {}
        for idx, cell in enumerate(row):
            c = ws.cell(row=row_num, column=idx+1)
            c.value = row[idx]
            c.alignment = openpyxl.styles.Alignment(wrap_text=False)
    # Save the result in the response
    wb.save(response)
    return response

def download_file(url):
    """Download a file from the indicated URL"""

    bResult = True
    sResult = ""
    errHandle = ErrHandle()
    # Get the filename from the url
    name = url.split("/")[-1]
    # Set the output directory
    outdir = os.path.abspath(os.path.join(MEDIA_DIR, "e-codices"))
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    # Create a filename where we can store it
    filename = os.path.abspath(os.path.join(outdir, name))
    try:
        r = requests.get(url)
    except:
        sMsg = errHandle.get_error_message()
        errHandle.DoError("Request problem")
        return False, sMsg
    if r.status_code == 200:
        # Read the response
        sText = r.text
        # Write away
        with open(filename, "w", encoding="utf-8") as f:
            f.write(sText)
        sResult = filename
    else:
        bResult = False
        sResult = "download_file received status {} for {}".format(r.status_code, url)
    # Return the result
    return bResult, sResult

def get_date_display(dtThis):
    if dtThis == None:
        result = "-"
    else:
        result = dtThis.strftime("%d/%b/%Y %H:%M")
    return result

def get_previous_page(request):
    """Find the previous page for this user"""

    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous" and request.user.username != "":
        # Get the current path list
        p_list = Profile.get_stack(username)
        if len(p_list) < 2:
            prevpage = request.META.get('HTTP_REFERER') 
        else:
            p_item = p_list[len(p_list)-2]
            prevpage = p_item['url']
            # Possibly add arguments
            if 'kwargs' in p_item:
                # First strip off any arguments (anything after ?) in the url
                if "?" in prevpage:
                    prevpage = prevpage.split("?")[0]
                bFirst = True
                for k,v in p_item['kwargs'].items():
                    if bFirst:
                        addsign = "?"
                        bFirst = False
                    else:
                        addsign = "&"
                    prevpage = "{}{}{}={}".format(prevpage, addsign, k, v)
    else:
        prevpage = request.META.get('HTTP_REFERER') 
    # Return the path
    return prevpage

def has_list_value(field, obj):
    response = (field in obj and obj[field] != None and len(obj[field]) > 0)
    return response

def has_obj_value(field, obj):
    response = (field != None and field in obj and obj[field] != None)
    return response

def has_string_value(field, obj):
    response = (field in obj and obj[field] != None and obj[field] != "")
    return response

def home(request):
    """Renders the home page."""

    assert isinstance(request, HttpRequest)
    # Specify the template
    template_name = 'index.html'
    # Define the initial context
    context =  {'title':'RU-lenten',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "Home", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}]

    # Check the newsitems for validity
    NewsItem.check_until()
    # Create the list of news-items
    lstQ = []
    lstQ.append(Q(status='val'))
    newsitem_list = NewsItem.objects.filter(*lstQ).order_by('-saved', '-created')
    context['newsitem_list'] = newsitem_list

    # Set the number of sermons and the number of collections
    context['sermoncount'] = Sermon.objects.count()
    context['collectioncount'] = SermonCollection.objects.count()

    # Render and return the page
    return render(request, template_name, context)

def instruction(request):
    """Renders the instruction page."""

    assert isinstance(request, HttpRequest)
    context =  {'title':'Instruction',
                'message':'Helpful instructions',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}, {'name': 'Instruction', 'url': reverse('instruction')}]


    return render(request,'instruction.html', context)

def make_ordering(qs, qd, orders, order_cols, order_heads):

    oErr = ErrHandle()

    try:
        bAscending = True
        sType = 'str'
        order = []
        if 'o' in qd and qd['o'] != "":
            colnum = qd['o']
            if '=' in colnum:
                colnum = colnum.split('=')[1]
            if colnum != "":
                order = []
                iOrderCol = int(colnum)
                bAscending = (iOrderCol>0)
                iOrderCol = abs(iOrderCol)
                sType = order_heads[iOrderCol-1]['type']
                for order_item in order_cols[iOrderCol-1].split(";"):
                    if sType == "int":
                        order.append(order_item)
                    else:
                        order.append(Lower(order_item))
                if bAscending:
                    order_heads[iOrderCol-1]['order'] = 'o=-{}'.format(iOrderCol)
                else:
                    # order = "-" + order
                    order_heads[iOrderCol-1]['order'] = 'o={}'.format(iOrderCol)
        else:
            orderings = []
            for idx, order_item in enumerate(orders):
                # Get the type
                sType = order_heads[idx]['type']
                if ";" in order_item:
                    for sub_item in order_item.split(";"):
                        orderings.append(dict(type=sType, item=sub_item))
                else:
                    orderings.append(dict(type=sType, item=order_item))
            for item in orderings:
                sType = item['type']
                order_item = item['item']
                if order_item != "":
                    if sType == "int":
                        order.append(order_item)
                    else:
                        order.append(Lower(order_item))
            #for order_item in order_cols[0].split(";"):
            #    order.append(Lower(order_item))
        if sType == 'str':
            if len(order) > 0:
                qs = qs.order_by(*order)
            # qs = qs.order_by('editions__first__date_late')
        else:
            qs = qs.order_by(*order)
        # Possibly reverse the order
        if not bAscending:
            qs = qs.reverse()
    except:
        msg = oErr.get_error_message()
        oErr.DoError("make_ordering")
        lstQ = []

    return qs, order_heads

def make_search_list(filters, oFields, search_list, qd):
    """Using the information in oFields and search_list, produce a revised filters array and a lstQ for a Queryset"""

    def enable_filter(filter_id, head_id=None):
        for item in filters:
            if filter_id in item['id']:
                item['enabled'] = True
                # Break from my loop
                break
        # Check if this one has a head
        if head_id != None and head_id != "":
            for item in filters:
                if head_id in item['id']:
                    item['enabled'] = True
                    # Break from this sub-loop
                    break
        return True

    def get_value(obj, field, default=None):
        if field in obj:
            sBack = obj[field]
        else:
            sBack = default
        return sBack

    oErr = ErrHandle()

    try:
        # (1) Create default lstQ
        lstQ = []

        # (2) Reset the filters in the list we get
        for item in filters: item['enabled'] = False
    
        # (3) Walk all sections
        for part in search_list:
            head_id = get_value(part, 'section')

            # (4) Walk the list of defined searches
            for search_item in part['filterlist']:
                keyS = get_value(search_item, "keyS")
                keyId = get_value(search_item, "keyId")
                keyFk = get_value(search_item, "keyFk")
                keyList = get_value(search_item, "keyList")
                infield = get_value(search_item, "infield")
                dbfield = get_value(search_item, "dbfield")
                fkfield = get_value(search_item, "fkfield")
                keyType = get_value(search_item, "keyType")
                filter_type = get_value(search_item, "filter")
                s_q = ""
               
                # Main differentiation: fkfield or dbfield
                if fkfield:
                    # We are dealing with a foreign key
                    # Check for keyS
                    if has_string_value(keyS, oFields):
                        # Check for ID field
                        if has_string_value(keyId, oFields):
                            val = oFields[keyId]
                            if not isinstance(val, int): 
                                try:
                                    val = val.id
                                except:
                                    pass
                            enable_filter(filter_type, head_id)
                            s_q = Q(**{"{}__id".format(fkfield): val})
                        elif has_obj_value(fkfield, oFields):
                            val = oFields[fkfield]
                            enable_filter(filter_type, head_id)
                            s_q = Q(**{fkfield: val})
                        else:
                            val = oFields[keyS]
                            enable_filter(filter_type, head_id)
                            # we are dealing with a foreign key, so we should use keyFk
                            if "*" in val:
                                val = adapt_search(val)
                                s_q = Q(**{"{}__{}__iregex".format(fkfield, keyFk): val})
                            else:
                                s_q = Q(**{"{}__{}__iexact".format(fkfield, keyFk): val})
                    elif has_obj_value(fkfield, oFields):
                        val = oFields[fkfield]
                        enable_filter(filter_type, head_id)
                        s_q = Q(**{fkfield: val})
                        external = get_value(search_item, "external")
                        if has_string_value(external, oFields):
                            qd[external] = getattr(val, "name")
                elif dbfield:
                    # We are dealing with a plain direct field for the model
                    # OR: it is also possible we are dealing with a m2m field -- that gets the same treatment
                    # Check for keyS
                    if has_string_value(keyS, oFields):
                        # Check for ID field
                        if has_string_value(keyId, oFields):
                            val = oFields[keyId]
                            enable_filter(filter_type, head_id)
                            s_q = Q(**{"{}__id".format(dbfield): val})
                        elif has_obj_value(keyFk, oFields):
                            val = oFields[keyFk]
                            enable_filter(filter_type, head_id)
                            s_q = Q(**{dbfield: val})
                        else:
                            val = oFields[keyS]
                            enable_filter(filter_type, head_id)
                            if isinstance(val, int):
                                s_q = Q(**{"{}".format(dbfield): val})
                            elif "*" in val:
                                val = adapt_search(val)
                                s_q = Q(**{"{}__iregex".format(dbfield): val})
                            else:
                                s_q = Q(**{"{}__iexact".format(dbfield): val})
                    elif keyType == "has":
                        # Check the count for the db field
                        val = oFields[filter_type]
                        if val == "yes" or val == "no":
                            enable_filter(filter_type, head_id)
                            if val == "yes":
                                s_q = Q(**{"{}__gt".format(dbfield): 0})
                            else:
                                s_q = Q(**{"{}".format(dbfield): 0})

                # Check for list of specific signatures
                if has_list_value(keyList, oFields):
                    enable_filter(filter_type, head_id)
                    code_list = [getattr(x, infield) for x in oFields[keyList]]
                    if fkfield:
                        # Now we need to look at the id's
                        s_q_lst = Q(**{"{}__{}__in".format(fkfield, infield): code_list})
                    elif dbfield:
                        s_q_lst = Q(**{"{}__in".format(infield): code_list})
                    s_q = s_q_lst if s_q == "" else s_q | s_q_lst

                # Possibly add the result to the list
                if s_q != "": lstQ.append(s_q)
    except:
        msg = oErr.get_error_message()
        oErr.DoError("make_search_list")
        lstQ = []

    # Return what we have created
    return filters, lstQ, qd

def more(request):
    """Renders the more page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'More',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "More", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}, {'name': 'More', 'url': reverse('more')}]


    return render(request,'more.html', context)

def nlogin(request):
    """Renders the not-logged-in page."""
    assert isinstance(request, HttpRequest)
    context =  {    'title':'Not logged in', 
                    'message':'Radboud University passim utility.',
                    'year':get_current_datetime().year,}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    return render(request,'nlogin.html', context)

def process_visit(request, name, is_menu, **kwargs):
    """Process one visit and return updated breadcrumbs"""

    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous" and request.user.username != "":
        # Add the visit
        Visit.add(username, name, request.get_full_path(), is_menu, **kwargs)
        # Get the updated path list
        p_list = Profile.get_stack(username)
    else:
        p_list = []
        p_list.append({'name': 'Home', 'url': reverse('home')})
    # Return the breadcrumbs
    # return json.dumps(p_list)
    return p_list

def short(request):
    """Renders the page with the short instructions."""

    assert isinstance(request, HttpRequest)
    template = 'short.html'
    context = {'title': 'Short overview',
               'message': 'Radboud University passim short intro',
               'year': get_current_datetime().year}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    return render(request, template, context)

def signup(request):
    """Provide basic sign up and validation of it """

    allow_signup = False # Do not allow signup yet
    if allow_signup:
        if request.method == 'POST':
            form = SignUpForm(request.POST)
            if form.is_valid():
                # Save the form
                form.save()
                # Create the user
                username = form.cleaned_data.get('username')
                raw_password = form.cleaned_data.get('password1')
                # also make sure that the user gets into the STAFF,
                #      otherwise he/she may not see the admin pages
                user = authenticate(username=username, 
                                    password=raw_password,
                                    is_staff=True)
                user.is_staff = True
                user.save()
                # Add user to the "passim_user" group
                gQs = Group.objects.filter(name="passim_user")
                if gQs.count() > 0:
                    g = gQs[0]
                    g.user_set.add(user)
                # Log in as the user
                login(request, user)
                return redirect('home')
        else:
            form = SignUpForm()
        return render(request, 'signup.html', {'form': form})
    else:
        return redirect('home')

def sync_entry(request):
    """-"""
    assert isinstance(request, HttpRequest)

    # Gather info
    context = {'title': 'SyncEntry',
               'message': 'Radboud University PASSIM'
               }
    template_name = 'seeker/syncentry.html'

    # Add the information in the 'context' of the web page
    return render(request, template_name, context)

def sync_start(request):
    """Synchronize information"""

    oErr = ErrHandle()
    data = {'status': 'starting'}
    try:
        # Get the user
        username = request.user.username
        # Get the synchronization type
        get = request.GET
        synctype = ""
        if 'synctype' in get:
            synctype = get['synctype']

        if synctype == '':
            # Formulate a response
            data['status'] = 'no sync type specified'

        else:
            # Remove previous status objects for this combination of user/type
            lstQ = []
            lstQ.append(Q(user=username))
            lstQ.append(Q(type=synctype))
            qs = Status.objects.filter(*lstQ)
            qs.delete()

            # Create a status object for this combination of synctype/user
            oStatus = Status(user=username, type=synctype, status="preparing")
            oStatus.save()

            # Formulate a response
            data['status'] = 'done'

            if synctype == "entries":
                # Use the synchronisation object that contains all relevant information
                oStatus.set("loading")

                # Update the models with the new information
                oResult = process_lib_entries(oStatus)
                if oResult == None or oResult['result'] == False:
                    data.status = 'error'
                elif oResult != None:
                    data['count'] = oResult

    except:
        oErr.DoError("sync_start error")
        data['status'] = "error"

    # Return this response
    return JsonResponse(data)

def sync_progress(request):
    """Get the progress on the /crpp synchronisation process"""

    oErr = ErrHandle()
    data = {'status': 'preparing'}

    try:
        # Get the user
        username = request.user.username
        # Get the synchronization type
        get = request.GET
        synctype = ""
        if 'synctype' in get:
            synctype = get['synctype']

        if synctype == '':
            # Formulate a response
            data['status'] = 'error'
            data['msg'] = "no sync type specified" 

        else:
            # Formulate a response
            data['status'] = 'UNKNOWN'

            # Get the appropriate status object
            # sleep(1)
            oStatus = Status.objects.filter(user=username, type=synctype).first()

            # Check what we received
            if oStatus == None:
                # There is no status object for this type
                data['status'] = 'error'
                data['msg'] = "Cannot find status for {}/{}".format(
                    username, synctype)
            else:
                # Get the last status information
                data['status'] = oStatus.status
                data['msg'] = oStatus.msg
                data['count'] = oStatus.count

        # Return this response
        return JsonResponse(data)
    except:
        oErr.DoError("sync_start error")
        data = {'status': 'error'}

    # Return this response
    return JsonResponse(data)

def treat_bom(sHtml):
    """REmove the BOM marker except at the beginning of the string"""

    # Check if it is in the beginning
    bStartsWithBom = sHtml.startswith(u'\ufeff')
    # Remove everywhere
    sHtml = sHtml.replace(u'\ufeff', '')
    # Return what we have
    return sHtml

def user_is_authenticated(request):
    # Is this user authenticated?
    username = request.user.username
    user = User.objects.filter(username=username).first()
    return user.is_authenticated()

def user_is_ingroup(request, sGroup):
    # Is this user part of the indicated group?
    username = request.user.username
    user = User.objects.filter(username=username).first()
    # glist = user.groups.values_list('name', flat=True)

    # Only look at group if the user is known
    if user == None:
        glist = []
    else:
        glist = [x.name for x in user.groups.all()]

        # Only needed for debugging
        if bDebug:
            ErrHandle().Status("User [{}] is in groups: {}".format(user, glist))
    # Evaluate the list
    bIsInGroup = (sGroup in glist)
    return bIsInGroup

@csrf_exempt
def get_cities(request):
    """Get a list of cities for autocomplete"""

    data = 'fail'
    method = "useLocation"
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            # Get the user-specified 'country' and 'city' strings
            country = request.GET.get('country', "")
            if country == "": country = request.GET.get('country_ta', "")
            city = request.GET.get("city", "")
            if city == "": city = request.GET.get('city_ta', "")

            # build the query
            lstQ = []
            if method == "useLocation":
                # Start as broad as possible: country
                qs_loc = None
                if country != "":
                    loctype_country = LocationType.find("country")
                    lstQ.append(Q(name=country))
                    lstQ.append(Q(loctype=loctype_country))
                    qs_country = Location.objects.filter(*lstQ)
                    # Fine-tune on city...
                    loctype_city = LocationType.find("city")
                    lstQ = []
                    lstQ.append(Q(name__icontains=city))
                    lstQ.append(Q(loctype=loctype_city))
                    lstQ.append(Q(relations_location__in=qs_country))
                    cities = Location.objects.filter(*lstQ)
                else:
                    loctype_city = LocationType.find("city")
                    lstQ.append(Q(name__icontains=city))
                    lstQ.append(Q(loctype=loctype_city))
                    cities = Location.objects.filter(*lstQ)
            elif method == "slowLocation":
                # First of all: city...
                loctype_city = LocationType.find("city")
                lstQ.append(Q(name__icontains=city))
                lstQ.append(Q(loctype=loctype_city))
                # Do we have a *country* specification?
                if country != "":
                    loctype_country = LocationType.find("country")
                    lstQ.append(Q(relations_location__name=country))
                    lstQ.append(Q(relations_location__loctype=loctype_country))
                # Combine everything
                cities = Location.objects.filter(*lstQ).order_by('name')
            else:
                if country != "":
                    lstQ.append(Q(country__name__icontains=country))
                lstQ.append(Q(name__icontains=city))
                cities = City.objects.filter(*lstQ).order_by('name')
            results = []
            for co in cities:
                co_json = {'name': co.name, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_cities")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)
    
@csrf_exempt
def get_countries(request):
    """Get a list of countries for autocomplete"""

    data = 'fail'
    method = "useLocation"
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sName = request.GET.get('country', '')
            if sName == "": sName = request.GET.get('country_ta', "")
            lstQ = []
            lstQ.append(Q(name__icontains=sName))
            if method == "useLocation":
                loctype = LocationType.find("country")
                lstQ.append(Q(loctype=loctype))
                countries = Location.objects.filter(*lstQ).order_by('name')
            else:
                countries = Country.objects.filter(*lstQ).order_by('name')
            results = []
            for co in countries:
                co_json = {'name': co.name, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_countries")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_locations(request):
    """Get a list of location names for autocomplete"""

    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sName = request.GET.get('name', '')
            lstQ = []
            lstQ.append(Q(name__icontains=sName))
            locations = Location.objects.filter(*lstQ).order_by('name').values('name', 'loctype__name', 'id')
            results = []
            for co in locations:
                name = "{} ({})".format(co['name'], co['loctype__name'])
                co_json = {'name': name, 'id': co['id'] }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_locations")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_params(request):
    """Get a list of concepts for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            # Initialisations
            results = []
            lstQ = []
            fieldQ = None
            model = None

            # Get the two obligatory parameters
            field = request.GET.get("field", "")
            line = request.GET.get("name", "")

            # Get the complete code line, which could use semicolon-separation
            namelist = line.split(";")
            name = "" if len(namelist) == 0 else namelist[-1].strip()

            # Find out what type we have
            if field == "concept":
                model = Concept
                model_field = "name"
                fieldQ = Q(name__icontains=name)
            elif field == "language":
                model = FieldChoice
                model_field = "english_name"
                fieldQ = Q(english_name__icontains=name)
                lstQ.append(Q(field="seeker.language"))

            # Check if we are okay
            if fieldQ != None:
                # Construct the search
                lstQ.append(fieldQ)
                items = model.objects.filter(*lstQ).order_by(model_field).distinct()
                for co in items:
                    co_json = {'name': getattr(co, model_field), 'id': co.id }
                    results.append(co_json)

            # Construct the returnable data
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_tributes(request):
    """Get a list of tribute values for autocomplete"""

    data = 'fail'
    requestOk = request.is_ajax()
    requestOk = True
    if requestOk:
        oErr = ErrHandle()
        try:
            # Get the tribute class
            sTclass = request.GET.get('tclass', '')   
            # Get the actual word(s) to search for
            sQuery = request.GET.get('q', '')
            if sTclass!= "" and sQuery != "":
                # Yes, continue...
                lstQ = []
                lstQ.append(Q(name__icontains=sQuery))
                clsThis = None
                #if sTclass == "communicative":
                #    clsThis = TagCommunicative
                #elif sTclass == "liturgical":
                #    clsThis = TagLiturgical
                #elif sTclass == "qsource":
                #    clsThis = TagQsource
                if sTclass == "notes":
                    clsThis = TagKeyword
                if clsThis != None:
                    qs = clsThis.objects.filter(*lstQ).order_by('name')
                    results = []
                    for co in qs:
                        co_json = {'name': co.name, 'value': co.name, 'id': co.id }
                        results.append(co_json)
                    data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_tributes")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)


class BasicPart(View):
    """This is my own versatile handling view.

    Note: this version works with <pk> and not with <object_id>
    """

    # Initialisations
    arErr = []              # errors   
    template_name = None    # The template to be used
    template_err_view = None
    form_validated = True   # Used for POST form validation
    savedate = None         # When saving information, the savedate is returned in the context
    add = False             # Are we adding a new record or editing an existing one?
    obj = None              # The instance of the MainModel
    action = ""             # The action to be undertaken
    MainModel = None        # The model that is mainly used for this form
    form_objects = []       # List of forms to be processed
    formset_objects = []    # List of formsets to be processed
    previous = None         # Return to this
    bDebug = False          # Debugging information
    data = {'status': 'ok', 'html': ''}       # Create data to be returned    
    
    def post(self, request, pk=None):
        # A POST request means we are trying to SAVE something
        self.initializations(request, pk)

        # Explicitly set the status to OK
        self.data['status'] = "ok"
        
        if self.checkAuthentication(request):
            # Build the context
            context = dict(object_id = pk, savedate=None)
            # context['prevpage'] = get_prevpage(request)     #  self.previous
            context['authenticated'] = user_is_authenticated(request)
            context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
            context['is_app_editor'] = user_is_ingroup(request, app_editor)
            # Action depends on 'action' value
            if self.action == "":
                if self.bDebug: self.oErr.Status("ResearchPart: action=(empty)")
                # Walk all the forms for preparation of the formObj contents
                for formObj in self.form_objects:
                    # Are we SAVING a NEW item?
                    if self.add:
                        # We are saving a NEW item
                        formObj['forminstance'] = formObj['form'](request.POST, prefix=formObj['prefix'])
                        formObj['action'] = "new"
                    else:
                        # We are saving an EXISTING item
                        # Determine the instance to be passed on
                        instance = self.get_instance(formObj['prefix'])
                        # Make the instance available in the form-object
                        formObj['instance'] = instance
                        # Get an instance of the form
                        formObj['forminstance'] = formObj['form'](request.POST, prefix=formObj['prefix'], instance=instance)
                        formObj['action'] = "change"

                # Initially we are assuming this just is a review
                context['savedate']="reviewed at {}".format(get_current_datetime().strftime("%X"))

                # Iterate again
                for formObj in self.form_objects:
                    prefix = formObj['prefix']
                    # Adapt if it is not readonly
                    if not formObj['readonly']:
                        # Check validity of form
                        if formObj['forminstance'].is_valid() and self.is_custom_valid(prefix, formObj['forminstance']):
                            # Save it preliminarily
                            instance = formObj['forminstance'].save(commit=False)
                            # The instance must be made available (even though it is only 'preliminary')
                            formObj['instance'] = instance
                            # Perform actions to this form BEFORE FINAL saving
                            bNeedSaving = formObj['forminstance'].has_changed()
                            if self.before_save(prefix, request, instance=instance, form=formObj['forminstance']): bNeedSaving = True
                            if formObj['forminstance'].instance.id == None: bNeedSaving = True
                            if bNeedSaving:
                                # Perform the saving
                                instance.save()
                                # Log the SAVE action
                                details = {'id': instance.id}
                                if formObj['forminstance'].changed_data != None:
                                    details['changes'] = action_model_changes(formObj['forminstance'], instance)
                                if 'action' in formObj: details['savetype'] = formObj['action']
                                Action.add(request.user.username, self.MainModel.__name__, "save", json.dumps(details))
                                # Set the context
                                context['savedate']="saved at {}".format(get_current_datetime().strftime("%X"))
                                # Put the instance in the form object
                                formObj['instance'] = instance
                                # Store the instance id in the data
                                self.data[prefix + '_instanceid'] = instance.id
                                # Any action after saving this form
                                self.after_save(prefix, instance=instance, form=formObj['forminstance'])
                            # Also get the cleaned data from the form
                            formObj['cleaned_data'] = formObj['forminstance'].cleaned_data
                        else:
                            self.arErr.append(formObj['forminstance'].errors)
                            self.form_validated = False
                            formObj['cleaned_data'] = None
                    else:
                        # Form is readonly

                        # Check validity of form
                        if formObj['forminstance'].is_valid() and self.is_custom_valid(prefix, formObj['forminstance']):
                            # At least get the cleaned data from the form
                            formObj['cleaned_data'] = formObj['forminstance'].cleaned_data


                    # Add instance to the context object
                    context[prefix + "Form"] = formObj['forminstance']
                # Walk all the formset objects
                for formsetObj in self.formset_objects:
                    prefix  = formsetObj['prefix']
                    if self.can_process_formset(prefix):
                        formsetClass = formsetObj['formsetClass']
                        form_kwargs = self.get_form_kwargs(prefix)
                        if self.add:
                            # Saving a NEW item
                            if 'initial' in formsetObj:
                                formset = formsetClass(request.POST, request.FILES, prefix=prefix, initial=formsetObj['initial'], form_kwargs = form_kwargs)
                            else:
                                formset = formsetClass(request.POST, request.FILES, prefix=prefix, form_kwargs = form_kwargs)
                        else:
                            # Saving an EXISTING item
                            instance = self.get_instance(prefix)
                            qs = self.get_queryset(prefix)
                            if qs == None:
                                formset = formsetClass(request.POST, request.FILES, prefix=prefix, instance=instance, form_kwargs = form_kwargs)
                            else:
                                formset = formsetClass(request.POST, request.FILES, prefix=prefix, instance=instance, queryset=qs, form_kwargs = form_kwargs)
                        # Process all the forms in the formset
                        self.process_formset(prefix, request, formset)
                        # Store the instance
                        formsetObj['formsetinstance'] = formset
                        # Make sure we know what we are dealing with
                        itemtype = "form_{}".format(prefix)
                        # Adapt the formset contents only, when it is NOT READONLY
                        if not formsetObj['readonly']:
                            # Is the formset valid?
                            if formset.is_valid():
                                has_deletions = False
                                # Make sure all changes are saved in one database-go
                                with transaction.atomic():
                                    # Walk all the forms in the formset
                                    for form in formset:
                                        # At least check for validity
                                        if form.is_valid() and self.is_custom_valid(prefix, form):
                                            # Should we delete?
                                            if 'DELETE' in form.cleaned_data and form.cleaned_data['DELETE']:
                                                # Check if deletion should be done
                                                if self.before_delete(prefix, form.instance):
                                                    # Log the delete action
                                                    details = {'id': form.instance.id}
                                                    Action.add(request.user.username, itemtype, "delete", json.dumps(details))
                                                    # Delete this one
                                                    form.instance.delete()
                                                    # NOTE: the template knows this one is deleted by looking at form.DELETE
                                                    has_deletions = True
                                            else:
                                                # Check if anything has changed so far
                                                has_changed = form.has_changed()
                                                # Save it preliminarily
                                                sub_instance = form.save(commit=False)
                                                # Any actions before saving
                                                if self.before_save(prefix, request, sub_instance, form):
                                                    has_changed = True
                                                # Save this construction
                                                if has_changed and len(self.arErr) == 0: 
                                                    # Save the instance
                                                    sub_instance.save()
                                                    # Adapt the last save time
                                                    context['savedate']="saved at {}".format(get_current_datetime().strftime("%X"))
                                                    # Log the delete action
                                                    details = {'id': sub_instance.id}
                                                    if form.changed_data != None:
                                                        details['changes'] = action_model_changes(form, sub_instance)
                                                    Action.add(request.user.username, itemtype, "save", json.dumps(details))
                                                    # Store the instance id in the data
                                                    self.data[prefix + '_instanceid'] = sub_instance.id
                                                    # Any action after saving this form
                                                    self.after_save(prefix, sub_instance)
                                        else:
                                            if len(form.errors) > 0:
                                                self.arErr.append(form.errors)
                                
                                # Rebuild the formset if it contains deleted forms
                                if has_deletions or not has_deletions:
                                    # Or: ALWAYS
                                    if qs == None:
                                        formset = formsetClass(prefix=prefix, instance=instance, form_kwargs=form_kwargs)
                                    else:
                                        formset = formsetClass(prefix=prefix, instance=instance, queryset=qs, form_kwargs=form_kwargs)
                                    formsetObj['formsetinstance'] = formset
                            else:
                                # Iterate over all errors
                                for idx, err_this in enumerate(formset.errors):
                                    if '__all__' in err_this:
                                        self.arErr.append(err_this['__all__'][0])
                                    elif err_this != {}:
                                        # There is an error in item # [idx+1], field 
                                        problem = err_this 
                                        for k,v in err_this.items():
                                            fieldName = k
                                            errmsg = "Item #{} has an error at field [{}]: {}".format(idx+1, k, v[0])
                                            self.arErr.append(errmsg)

                            # self.arErr.append(formset.errors)
                    else:
                        formset = []
                    # Add the formset to the context
                    context[prefix + "_formset"] = formset
            elif self.action == "download":
                # We are being asked to download something
                if self.dtype != "":
                    # Initialise return status
                    oBack = {'status': 'ok'}
                    sType = "csv" if (self.dtype == "xlsx") else self.dtype

                    # Get the data
                    sData = self.get_data('', self.dtype)
                    # Decode the data and compress it using gzip
                    bUtf8 = (self.dtype != "db")
                    bUsePlain = (self.dtype == "xlsx" or self.dtype == "csv")

                    # Create name for download
                    # sDbName = "{}_{}_{}_QC{}_Dbase.{}{}".format(sCrpName, sLng, sPartDir, self.qcTarget, self.dtype, sGz)
                    modelname = self.MainModel.__name__
                    obj_id = "n" if self.obj == None else self.obj.id
                    sDbName = "passim_{}_{}.{}".format(modelname, obj_id, self.dtype)
                    sContentType = ""
                    if self.dtype == "csv":
                        sContentType = "text/tab-separated-values"
                    elif self.dtype == "json":
                        sContentType = "application/json"
                    elif self.dtype == "xlsx":
                        sContentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                    # Excel needs additional conversion
                    if self.dtype == "xlsx":
                        # Convert 'compressed_content' to an Excel worksheet
                        response = HttpResponse(content_type=sContentType)
                        response['Content-Disposition'] = 'attachment; filename="{}"'.format(sDbName)    
                        response = csv_to_excel(sData, response)
                    else:
                        response = HttpResponse(sData, content_type=sContentType)
                        response['Content-Disposition'] = 'attachment; filename="{}"'.format(sDbName)    

                    # Continue for all formats
                        
                    # return gzip_middleware.process_response(request, response)
                    return response
            elif self.action == "delete":
                # The user requests this to be deleted
                if self.before_delete():
                    # Log the delete action
                    details = {'id': self.obj.id}
                    Action.add(request.user.username, self.MainModel.__name__, "delete", json.dumps(details))
                    # We have permission to delete the instance
                    self.obj.delete()
                    context['deleted'] = True

            # Allow user to add to the context
            context = self.add_to_context(context)

            # Check if 'afternewurl' needs adding
            # NOTE: this should only be used after a *NEW* instance has been made -hence the self.add check
            if 'afternewurl' in context and self.add:
                self.data['afternewurl'] = context['afternewurl']
            if 'afterdelurl' in context:
                self.data['afterdelurl'] = context['afterdelurl']

            # Make sure we have a list of any errors
            error_list = [str(item) for item in self.arErr]
            context['error_list'] = error_list
            context['errors'] = json.dumps( self.arErr)
            if len(self.arErr) > 0:
                # Indicate that we have errors
                self.data['has_errors'] = True
                self.data['status'] = "error"
            else:
                self.data['has_errors'] = False
            # Standard: add request user to context
            context['requestuser'] = request.user

            # Get the HTML response
            if len(self.arErr) > 0:
                if self.template_err_view != None:
                     # Create a list of errors
                    self.data['err_view'] = render_to_string(self.template_err_view, context, request)
                else:
                    self.data['error_list'] = error_list
                    self.data['errors'] = self.arErr
                self.data['html'] = ''
            elif self.action == "delete":
                self.data['html'] = "deleted" 
            else:
                # In this case reset the errors - they should be shown within the template
                sHtml = render_to_string(self.template_name, context, request)
                sHtml = treat_bom(sHtml)
                self.data['html'] = sHtml

            # At any rate: empty the error basket
            self.arErr = []
            error_list = []

        else:
            self.data['html'] = "Please log in before continuing"

        # Return the information
        return JsonResponse(self.data)
        
    def get(self, request, pk=None): 
        self.data['status'] = 'ok'
        # Perform the initializations that need to be made anyway
        self.initializations(request, pk)
        if self.checkAuthentication(request):
            context = dict(object_id = pk, savedate=None)
            context['prevpage'] = self.previous
            context['authenticated'] = user_is_authenticated(request)
            context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
            context['is_app_editor'] = user_is_ingroup(request, app_editor)
            # Walk all the form objects
            for formObj in self.form_objects:        
                # Used to populate a NEW research project
                # - CREATE a NEW research form, populating it with any initial data in the request
                initial = dict(request.GET.items())
                if self.add:
                    # Create a new form
                    formObj['forminstance'] = formObj['form'](initial=initial, prefix=formObj['prefix'])
                else:
                    # Used to show EXISTING information
                    instance = self.get_instance(formObj['prefix'])
                    # We should show the data belonging to the current Research [obj]
                    formObj['forminstance'] = formObj['form'](instance=instance, prefix=formObj['prefix'])
                # Add instance to the context object
                context[formObj['prefix'] + "Form"] = formObj['forminstance']
            # Walk all the formset objects
            for formsetObj in self.formset_objects:
                formsetClass = formsetObj['formsetClass']
                prefix  = formsetObj['prefix']
                form_kwargs = self.get_form_kwargs(prefix)
                if self.add:
                    # - CREATE a NEW formset, populating it with any initial data in the request
                    initial = dict(request.GET.items())
                    # Saving a NEW item
                    formset = formsetClass(initial=initial, prefix=prefix, form_kwargs=form_kwargs)
                else:
                    # Possibly initial (default) values
                    if 'initial' in formsetObj:
                        initial = formsetObj['initial']
                    else:
                        initial = None
                    # show the data belonging to the current [obj]
                    instance = self.get_instance(prefix)
                    qs = self.get_queryset(prefix)
                    if qs == None:
                        formset = formsetClass(prefix=prefix, instance=instance, form_kwargs=form_kwargs)
                    else:
                        formset = formsetClass(prefix=prefix, instance=instance, queryset=qs, initial=initial, form_kwargs=form_kwargs)
                # Process all the forms in the formset
                ordered_forms = self.process_formset(prefix, request, formset)
                if ordered_forms:
                    context[prefix + "_ordered"] = ordered_forms
                # Store the instance
                formsetObj['formsetinstance'] = formset
                # Add the formset to the context
                context[prefix + "_formset"] = formset
            # Allow user to add to the context
            context = self.add_to_context(context)
            # Make sure we have a list of any errors
            error_list = [str(item) for item in self.arErr]
            context['error_list'] = error_list
            context['errors'] = self.arErr
            # Standard: add request user to context
            context['requestuser'] = request.user
            
            # Get the HTML response
            sHtml = render_to_string(self.template_name, context, request)
            sHtml = treat_bom(sHtml)
            self.data['html'] = sHtml
        else:
            self.data['html'] = "Please log in before continuing"

        # Return the information
        return JsonResponse(self.data)
      
    def checkAuthentication(self,request):
        # first check for authentication
        if not request.user.is_authenticated:
            # Simply redirect to the home page
            self.data['html'] = "Please log in to work on this project"
            return False
        else:
            return True

    def rebuild_formset(self, prefix, formset):
        return formset

    def initializations(self, request, object_id):
        # Store the previous page
        #self.previous = get_previous_page(request)
        # Clear errors
        self.arErr = []
        # COpy the request
        self.request = request
        # Copy any object id
        self.object_id = object_id
        self.add = object_id is None
        # Get the parameters
        if request.POST:
            self.qd = request.POST
        else:
            self.qd = request.GET

        # Check for action
        if 'action' in self.qd:
            self.action = self.qd['action']

        # Find out what the Main Model instance is, if any
        if self.add:
            self.obj = None
        else:
            # Get the instance of the Main Model object
            self.obj =  self.MainModel.objects.filter(pk=object_id).first()
            # NOTE: if the object doesn't exist, we will NOT get an error here
        # ALWAYS: perform some custom initialisations
        self.custom_init()

    def get_instance(self, prefix):
        return self.obj

    def is_custom_valid(self, prefix, form):
        return True

    def get_queryset(self, prefix):
        return None

    def get_form_kwargs(self, prefix):
        return None

    def get_data(self, prefix, dtype):
        return ""

    def before_save(self, prefix, request, instance=None, form=None):
        return False

    def before_delete(self, prefix=None, instance=None):
        return True

    def after_save(self, prefix, instance=None, form=None):
        return True

    def add_to_context(self, context):
        return context

    def process_formset(self, prefix, request, formset):
        return None

    def can_process_formset(self, prefix):
        return True

    def custom_init(self):
        pass    
           

class PassimDetails(DetailView):
    """Extension of the normal DetailView class for PASSIM"""

    template_name = ""      # Template for GET
    template_post = ""      # Template for POST
    formset_objects = []    # List of formsets to be processed
    afternewurl = ""        # URL to move to after adding a new item
    prefix = ""             # The prefix for the one (!) form we use
    previous = None         # Start with empty previous page
    title = ""              # The title to be passedon with the context
    rtype = "json"          # JSON response (alternative: html)
    prefix_type = ""        # Whether the adapt the prefix or not ('simple')
    mForm = None            # Model form
    newRedirect = False     # Redirect the page name to a correct one after creating
    redirectpage = ""       # Where to redirect to
    add = False             # Are we adding a new record or editing an existing one?

    def get(self, request, pk=None, *args, **kwargs):
        # Initialisation
        data = {'status': 'ok', 'html': '', 'statuscode': ''}
        # always do this initialisation to get the object
        self.initializations(request, pk)
        if not request.user.is_authenticated:
            # Do not allow to get a good response
            if self.rtype == "json":
                data['html'] = "(No authorization)"
                data['status'] = "error"
                response = JsonResponse(data)
            else:
                response = reverse('nlogin')
        else:
            context = self.get_context_data(object=self.object)

            # Possibly indicate form errors
            # NOTE: errors is a dictionary itself...
            if 'errors' in context and len(context['errors']) > 0:
                data['status'] = "error"
                data['msg'] = context['errors']

            if self.rtype == "json":
                # We render to the _name 
                sHtml = render_to_string(self.template_name, context, request)
                sHtml = sHtml.replace("\ufeff", "")
                data['html'] = sHtml
                response = JsonResponse(data)
            elif self.redirectpage != "":
                return redirect(self.redirectpage)
            else:
                # This takes self.template_name...
                response = self.render_to_response(context)

        # Return the response
        return response

    def post(self, request, pk=None, *args, **kwargs):
        # Initialisation
        data = {'status': 'ok', 'html': '', 'statuscode': ''}
        # always do this initialisation to get the object
        self.initializations(request, pk)
        # Make sure only POSTS get through that are authorized
        if request.user.is_authenticated:
            context = self.get_context_data(object=self.object)
            # Check if 'afternewurl' needs adding
            if 'afternewurl' in context:
                data['afternewurl'] = context['afternewurl']
            # Check if 'afterdelurl' needs adding
            if 'afterdelurl' in context:
                data['afterdelurl'] = context['afterdelurl']
            # Possibly indicate form errors
            # NOTE: errors is a dictionary itself...
            if 'errors' in context and len(context['errors']) > 0:
                data['status'] = "error"
                data['msg'] = context['errors']

            if self.rtype == "json":
                response = render_to_string(self.template_post, context, request)
                response = response.replace("\ufeff", "")
                data['html'] = response
                response = JsonResponse(data)
            elif self.newRedirect and self.redirectpage != "":
                # Redirect to this page
                return redirect(self.redirectpage)
            else:
                # This takes self.template_name...
                response = self.render_to_response(context)
        else:
            data['html'] = "(No authorization)"
            data['status'] = "error"
            response = JsonResponse(data)

        # Return the response
        return response

    def initializations(self, request, pk):
        # Store the previous page
        # self.previous = get_previous_page(request)

        # Copy any pk
        self.pk = pk
        self.add = pk is None
        # Get the parameters
        if request.POST:
            self.qd = request.POST
        else:
            self.qd = request.GET

        # Check for action
        if 'action' in self.qd:
            self.action = self.qd['action']

        # Find out what the Main Model instance is, if any
        if self.add:
            self.object = None
        else:
            # Get the instance of the Main Model object
            # NOTE: if the object doesn't exist, we will NOT get an error here
            self.object = self.get_object()

    def before_delete(self, instance):
        """Anything that needs doing before deleting [instance] """
        return True, "" 

    def after_new(self, form, instance):
        """Action to be performed after adding a new item"""
        return True, "" 

    def before_save(self, instance):
        """Action to be performed after saving an item preliminarily, and before saving completely"""
        return True, "" 

    def add_to_context(self, context, instance):
        """Add to the existing context"""
        return context

    def process_formset(self, prefix, request, formset):
        return None

    def get_formset_queryset(self, prefix):
        return None

    def get_form_kwargs(self, prefix):
        return None

    def get_context_data(self, **kwargs):
        # Get the current context
        context = super(PassimDetails, self).get_context_data(**kwargs)

        # Check this user: is he allowed to UPLOAD data?
        context['authenticated'] = user_is_authenticated(self.request)
        context['is_app_uploader'] = user_is_ingroup(self.request, app_uploader)
        context['is_app_editor'] = user_is_ingroup(self.request, app_editor)
        # context['prevpage'] = get_previous_page(self.request) # self.previous

        # Define where to go to after deletion
        context['afterdelurl'] = get_previous_page(self.request)
        context['afternewurl'] = ""

        # Get the parameters passed on with the GET or the POST request
        get = self.request.GET if self.request.method == "GET" else self.request.POST
        initial = get.copy()
        self.qd = initial

        self.bHasFormInfo = (len(self.qd) > 0)

        # Set the title of the application
        context['title'] = self.title

        # Get the instance
        instance = self.object
        bNew = False
        mForm = self.mForm
        frm = None
        oErr = ErrHandle()

        # prefix = self.prefix
        if self.prefix_type == "":
            id = "n" if instance == None else instance.id
            prefix = "{}-{}".format(self.prefix, id)
        else:
            prefix = self.prefix

        if mForm != None:
            # Check if this is a POST or a GET request
            if self.request.method == "POST":
                # Determine what the action is (if specified)
                action = ""
                if 'action' in initial: action = initial['action']
                if action == "delete":
                    # The user wants to delete this item
                    try:
                        bResult, msg = self.before_delete(instance)
                        if bResult:
                            # Log the DELETE action
                            details = {'id': instance.id}
                            Action.add(self.request.user.username, instance.__class__.__name__, "delete", json.dumps(details))
                            # Remove this sermongold instance
                            instance.delete()
                        else:
                            # Removing is not possible
                            context['errors'] = {'delete': msg }
                    except:
                        msg = oErr.get_error_message()
                        # Create an errors object
                        context['errors'] = {'delete':  msg }
                    # And return the complied context
                    return context
            
                # All other actions just mean: edit or new and send back

                # Do we have an existing object or are we creating?
                if instance == None:
                    # Saving a new item
                    frm = mForm(initial, prefix=prefix)
                    bNew = True
                else:
                    # Editing an existing one
                    frm = mForm(initial, prefix=prefix, instance=instance)
                # Both cases: validation and saving
                if frm.is_valid():
                    # The form is valid - do a preliminary saving
                    instance = frm.save(commit=False)
                    # Any checks go here...
                    bResult, msg = self.before_save(instance)
                    if bResult:
                        # Now save it for real
                        instance.save()
                        # Make it available
                        context['object'] = instance
                        self.object = instance
                        # Log the SAVE action
                        details = {'id': instance.id}
                        details["savetype"] = "new" if bNew else "change"
                        if frm.changed_data != None:
                            details['changes'] = action_model_changes(frm, instance)
                        Action.add(self.request.user.username, instance.__class__.__name__, "save", json.dumps(details))
                    else:
                        context['errors'] = {'save': msg }
                else:
                    # We need to pass on to the user that there are errors
                    context['errors'] = frm.errors
                # Check if this is a new one
                if bNew:
                    # Any code that should be added when creating a new [SermonGold] instance
                    bResult, msg = self.after_new(frm, instance)
                    if not bResult:
                        # Removing is not possible
                        context['errors'] = {'new': msg }
                    # Check if an 'afternewurl' is specified
                    if self.afternewurl != "":
                        context['afternewurl'] = self.afternewurl
                
            else:
                # Check if this is asking for a new form
                if instance == None:
                    # Get the form for the sermon
                    frm = mForm(prefix=prefix)
                else:
                    # Get the form for the sermon
                    frm = mForm(instance=instance, prefix=prefix)
                # Walk all the formset objects
                for formsetObj in self.formset_objects:
                    formsetClass = formsetObj['formsetClass']
                    prefix  = formsetObj['prefix']
                    form_kwargs = self.get_form_kwargs(prefix)
                    if self.add:
                        # - CREATE a NEW formset, populating it with any initial data in the request
                        # Saving a NEW item
                        formset = formsetClass(initial=initial, prefix=prefix, form_kwargs=form_kwargs)
                    else:
                        # show the data belonging to the current [obj]
                        qs = self.get_formset_queryset(prefix)
                        if qs == None:
                            formset = formsetClass(prefix=prefix, instance=instance, form_kwargs=form_kwargs)
                        else:
                            formset = formsetClass(prefix=prefix, instance=instance, queryset=qs, form_kwargs=form_kwargs)
                    # Process all the forms in the formset
                    ordered_forms = self.process_formset(prefix, self.request, formset)
                    if ordered_forms:
                        context[prefix + "_ordered"] = ordered_forms
                    # Store the instance
                    formsetObj['formsetinstance'] = formset
                    # Add the formset to the context
                    context[prefix + "_formset"] = formset

        # Put the form and the formset in the context
        context['{}Form'.format(self.prefix)] = frm
        context['instance'] = instance
        context['options'] = json.dumps({"isnew": (instance == None)})

        # Possibly define where a listview is
        classname = self.model._meta.model_name
        listviewname = "{}_list".format(classname)
        try:
            context['listview'] = reverse(listviewname)
        except:
            context['listview'] = reverse('home')

        # Possibly define the admin detailsview
        if instance:
            admindetails = "admin:seeker_{}_change".format(classname)
            try:
                context['admindetails'] = reverse(admindetails, args=[instance.id])
            except:
                pass
        context['modelname'] = self.model._meta.object_name


        # Possibly add to context by the calling function
        context = self.add_to_context(context, instance)

        # Return the calculated context
        return context


class BasicListView(ListView):
    """Basic listview"""

    paginate_by = 15
    entrycount = 0
    qd = None
    bFilter = False
    basketview = False
    initial = None
    listform = None
    plural_name = ""
    prefix = ""
    order_default = []
    order_cols = []
    order_heads = []
    filters = []
    searches = []
    page_function = None
    formdiv = None

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BasicListView, self).get_context_data(**kwargs)

        # Get parameters for the search
        if self.initial == None:
            initial = self.request.POST if self.request.POST else self.request.GET
        else:
            initial = self.initial

        # Need to load the correct form
        if self.listform:
            context['{}Form'.format(self.prefix)] = self.listform(initial, prefix=self.prefix)

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Need to pass on a pagination function
        # if self.page_function:
        context['page_function'] = self.page_function
        context['formdiv'] = self.formdiv

        # Set the page number if needed
        if 'page_obj' in context and 'page' in initial and initial['page'] != "":
            # context['page_obj'].number = initial['page']
            page_num = int(initial['page'])
            context['page_obj'] = context['paginator'].page( page_num)
            # Make sure to adapt the object_list
            context['object_list'] = context['page_obj']

        # Set the title of the application
        context['title'] = self.plural_name

        # Make sure we pass on the ordered heads
        context['order_heads'] = self.order_heads
        context['has_filter'] = self.bFilter
        context['filters'] = self.filters

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_app_uploader'] = user_is_ingroup(self.request, app_uploader)
        context['is_app_editor'] = user_is_ingroup(self.request, app_editor)

        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, self.plural_name, True)
        context['prevpage'] = get_previous_page(self.request)

        # Allow others to add to context
        context = self.add_to_context(context, initial)

        # Return the calculated context
        return context

    def add_to_context(self, context, initial):
        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in default class property value.
        """
        return self.paginate_by
  
    def get_basketqueryset(self):
        """User-specific function to get a queryset based on a basket"""
        return None
  
    def get_queryset(self):
        # Get the parameters passed on with the GET or the POST request
        get = self.request.GET if self.request.method == "GET" else self.request.POST
        get = get.copy()
        self.qd = get

        self.bHasParameters = (len(get) > 0)
        bHasListFilters = False
        if self.basketview:
            self.basketview = True
            # We should show the contents of the basket
            # (1) Reset the filters
            for item in self.filters: item['enabled'] = False
            # (2) Indicate we have no filters
            self.bFilter = False
            # (3) Set the queryset -- this is listview-specific
            qs = self.get_basketqueryset()

            # Do the ordering of the results
            order = self.order_default
            qs, self.order_heads = make_ordering(qs, self.qd, order, self.order_cols, self.order_heads)
        elif self.bHasParameters:
            # y = [x for x in get ]
            bHasListFilters = len([x for x in get if self.prefix in x and get[x] != ""]) > 0
            if not bHasListFilters:
                self.basketview = ("usebasket" in get and get['usebasket'] == "True")

        if self.bHasParameters:
            lstQ = []
            # Indicate we have no filters
            self.bFilter = False

            # Read the form with the information
            thisForm = self.listform(self.qd, prefix=self.prefix)

            if thisForm.is_valid():
                # Process the criteria for this form
                oFields = thisForm.cleaned_data
                
                self.filters, lstQ, self.initial = make_search_list(self.filters, oFields, self.searches, self.qd)
                # Calculate the final qs
                if len(lstQ) == 0:
                    # Just show everything
                    qs = self.model.objects.all()
                else:
                    # There is a filter, so apply it
                    qs = self.model.objects.filter(*lstQ).distinct()
                    # Only set the [bFilter] value if there is an overt specified filter
                    for filter in self.filters:
                        if filter['enabled']:
                            self.bFilter = True
                            break
            else:
                # Just show everything
                qs = self.model.objects.all().distinct()

            # Do the ordering of the results
            order = self.order_default
            qs, self.order_heads = make_ordering(qs, self.qd, order, self.order_cols, self.order_heads)
        else:
            # Just show everything
            qs = self.model.objects.all().distinct()
            order = self.order_default
            qs, tmp_heads = make_ordering(qs, self.qd, order, self.order_cols, self.order_heads)

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)
    

class LocationListView(ListView):
    """Listview of locations"""

    model = Location
    paginate_by = 15
    template_name = 'seeker/location_list.html'
    entrycount = 0

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(LocationListView, self).get_context_data(**kwargs)

        # Get parameters
        initial = self.request.GET

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Get parameters for the search
        initial = self.request.GET
        # The searchform is just a list form, but filled with the 'initial' parameters
        context['searchform'] = LocationForm(initial)

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the title of the application
        context['title'] = "Lenten sermons location info"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_app_uploader'] = user_is_ingroup(self.request, app_uploader)
        context['is_app_editor'] = user_is_ingroup(self.request, app_editor)

        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, "Locations", True)
        context['prevpage'] = get_previous_page(self.request)

        # Return the calculated context
        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in default class property value.
        """
        return self.paginate_by
  
    def get_queryset(self):
        # Get the parameters passed on with the GET or the POST request
        get = self.request.GET if self.request.method == "GET" else self.request.POST
        get = get.copy()
        self.get = get

        lstQ = []

        # Check for author [name]
        if 'name' in get and get['name'] != '':
            val = adapt_search(get['name'])
            # Search in both the name field
            lstQ.append(Q(name__iregex=val))

        # Check for location type
        if 'loctype' in get and get['loctype'] != '':
            val = get['loctype']
            # Search in both the name field
            lstQ.append(Q(loctype=val))

        # Calculate the final qs
        qs = Location.objects.filter(*lstQ).order_by('name').distinct()

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs


class LocationDetailsView(PassimDetails):
    model = Location
    mForm = LocationForm
    template_name = 'seeker/location_details.html'
    prefix = 'loc'
    prefix_type = "simple"
    title = "LocationDetails"
    rtype = "html"

    def after_new(self, form, instance):
        """Action to be performed after adding a new item"""

        self.afternewurl = reverse('location_list')
        return True, "" 

    def add_to_context(self, context, instance):

        # Add the list of relations in which I am contained
        contained_locations = []
        if instance != None:
            contained_locations = instance.hierarchy(include_self=False)
        context['contained_locations'] = contained_locations

        # The standard information
        context['is_app_editor'] = user_is_ingroup(self.request, app_editor)
        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, "Location edit", False)
        context['prevpage'] = get_previous_page(self.request)
        return context


class LocationEdit(BasicPart):
    """The details of one location"""

    MainModel = Location
    template_name = 'seeker/location_edit.html'  
    title = "Location" 
    afternewurl = ""
    # One form is attached to this 
    prefix = "loc"
    form_objects = [{'form': LocationForm, 'prefix': prefix, 'readonly': False}]

    def before_save(self, prefix, request, instance = None, form = None):
        bNeedSaving = False
        if prefix == "loc":
            pass

        return bNeedSaving

    def after_save(self, prefix, instance = None, form = None):
        bStatus = True
        if prefix == "loc":
            # Check if there is a locationlist
            if 'locationlist' in form.cleaned_data:
                locationlist = form.cleaned_data['locationlist']

                # Get all the containers inside which [instance] is contained
                current_qs = Location.objects.filter(container_locrelations__contained=instance)
                # Walk the new list
                for item in locationlist:
                    #if item.id not in current_ids:
                    if item not in current_qs:
                        # Add it to the containers
                        LocationRelation.objects.create(contained=instance, container=item)
                # Update the current list
                current_qs = Location.objects.filter(container_locrelations__contained=instance)
                # Walk the current list
                remove_list = []
                for item in current_qs:
                    if item not in locationlist:
                        # Add it to the list of to-be-fremoved
                        remove_list.append(item.id)
                # Remove them from the container
                if len(remove_list) > 0:
                    LocationRelation.objects.filter(contained=instance, container__id__in=remove_list).delete()

        return bStatus

    def add_to_context(self, context):

        # Get the instance
        instance = self.obj

        if instance != None:
            pass

        afternew =  reverse('location_list')
        if 'afternewurl' in self.qd:
            afternew = self.qd['afternewurl']
        context['afternewurl'] = afternew

        return context


class LocationRelset(BasicPart):
    """The set of provenances from one manuscript"""

    MainModel = Location
    template_name = 'seeker/location_relset.html'
    title = "LocationRelations"
    LrelFormSet = inlineformset_factory(Location, LocationRelation,
                                         form=LocationRelForm, min_num=0,
                                         fk_name = "contained",
                                         extra=0, can_delete=True, can_order=False)
    formset_objects = [{'formsetClass': LrelFormSet, 'prefix': 'lrel', 'readonly': False}]

    def get_queryset(self, prefix):
        qs = None
        if prefix == "lrel":
            # List the parent locations for this location correctly
            qs = LocationRelation.objects.filter(contained=self.obj).order_by('container__name')
        return qs

    def before_save(self, prefix, request, instance = None, form = None):
        has_changed = False
        if prefix == "lrel":
            # Get any selected partof location id
            loc_id = form.cleaned_data['partof']
            if loc_id != "":
                # Check if a new relation should be made or an existing one should be changed
                if instance.id == None:
                    # Set the correct container
                    location = Location.objects.filter(id=loc_id).first()
                    instance.container = location
                    has_changed = True
                elif instance.container == None or instance.container.id == None or instance.container.id != int(loc_id):
                    location = Location.objects.filter(id=loc_id).first()
                    # Set the correct container
                    instance.container = location
                    has_changed = True
 
        return has_changed


class SermonListView(BasicListView):
    """Listview of sermons"""

    model = Sermon
    listform = SermonListForm
    prefix = "sermo"
    template_name = 'seeker/sermon_list.html'
    plural_name = "Sermons"
    order_default = ['collection__idno;edition__idno;idno', 'collection__firstauthor__name', 'collection__title', 'litday', 'book;chapter;verse', 'firsttopic__name']
    order_cols = order_default
    order_heads = [{'name': 'Code',             'order': 'o=1', 'type': 'int'}, 
                   {'name': 'Authors',          'order': 'o=2', 'type': 'str'}, 
                   {'name': 'Collection',       'order': 'o=3', 'type': 'str'}, 
                   {'name': 'Liturgical day',   'order': 'o=4', 'type': 'str'},
                   {'name': 'Thema',            'order': 'o=5', 'type': 'str'},
                   {'name': 'Main topic',       'order': 'o=6', 'type': 'str'}]
    filters = [ {"name": "Code",           "id": "filter_code",         "enabled": False},
                {"name": "Collection",     "id": "filter_collection",   "enabled": False},
                {"name": "Liturgical day", "id": "filter_litday",       "enabled": False},
                {"name": "Book",           "id": "filter_book",         "enabled": False},
                {"name": "Concept",        "id": "filter_concept",      "enabled": False},
                {"name": "Topic",          "id": "filter_topic",        "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'code',      'dbfield': 'code',      'keyS': 'code'},
            {'filter': 'collection','fkfield': 'collection','keyS': 'collname', 'keyFk': 'title', 'keyList': 'collectionlist', 'infield': 'id'},
            {'filter': 'litday',    'dbfield': 'litday',    'keyS': 'litday'},
            {'filter': 'book',      'fkfield': 'book',      'keyS': 'bookname', 'keyFk': 'name', 'keyList': 'booklist', 'infield': 'id'},
            {'filter': 'concept',   'fkfield': 'concepts',  'keyS': 'concept',  'keyFk': 'name', 'keyList': 'cnclist',  'infield': 'id' },
            {'filter': 'topic',     'fkfield': 'topics',                        'keyFk': 'name', 'keyList': 'toplist',  'infield': 'id' }
            ]},
        {'section': 'other', 'filterlist': [
            {'filter': 'tagnoteid',  'fkfield': 'notetags',         'keyS': 'tagnoteid', 'keyFk': 'id' },
            {'filter': 'tagsummid',  'fkfield': 'summarynotetags',  'keyS': 'tagsummid', 'keyFk': 'id' }
            ]}
        ]
    

class ConsultingDetailsView(PassimDetails):
    model = Consulting
    mForm = None
    template_name = 'generic_details.html' 
    prefix = "cons"
    title = "ConsultingDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        url_label = "url" if instance.label == None or instance.label == "" else instance.label
        context['mainitems'] = [
            {'type': 'plain', 'label': "Location:", 'value': instance.location},
            {'type': 'bold', 'label': "Link:", 'value': url_label, 'link': instance.link},
            {'type': 'plain', 'label': "Ownership:", 'value': instance.ownership},
            {'type': 'plain', 'label': "Marginalia:", 'value': instance.marginalia},
            {'type': 'plain', 'label': "Images:", 'value': instance.images}
            ]

        # Adapt the listview to which the user can link: 
        #    this should be the details view of the *EDITION* to which the consultings belong
        context['listview'] = reverse('edition_details', kwargs={'pk': instance.edition.id})

        return context


class CollectionDetailsView(PassimDetails):
    model = SermonCollection
    mForm = None
    template_name = 'generic_details.html' 
    prefix = ""
    title = "CollectionDetails"
    rtype = "html"
    mainitems = []
    sections = []

    def add_to_context(self, context, instance):
        # Show the main items of this sermon collection
        context['mainitems'] = [
            {'type': 'plain', 'label': "Identifier (Code):", 'value': str(instance.idno)},
            {'type': 'bold',  'label': "Title:", 'value': instance.title},
            {'type': 'plain', 'label': "Authors:", 'value': instance.get_authors()},
            {'type': 'plain', 'label': "Date of composition:", 'value': "{} ({})".format(instance.datecomp, instance.get_datetype_display()) },
            {'type': 'plain', 'label': "Place of composition:", 'value': instance.place.name },
            {'type': 'plain', 'label': "First edition:", 'value': instance.get_firstedition() },
            {'type': 'plain', 'label': "Number of editions:", 'value': instance.numeditions }

            ]

        context['sections'] = [
            {'name': 'Typology / structure', 'id': 'coll_typology', 'fields': [
                {'type': 'plain',       'label': "Structure:", 'value': instance.structure },
                {'type': 'safeline',    'label': "Liturgical relation:", 'value': instance.get_liturgical_display.strip(), 'title': "Relationship with liturgical texts"},
                {'type': 'safeline',    'label': "Communicative strategy:", 'value': instance.get_communicative_display.strip()},
                ]},
            {'name': 'General notes', 'id': 'coll_general', 'fields': [
                {'type': 'safeline',    'label': "Quoted sources:", 'value': instance.get_sources_display.strip()},
                {'type': 'safeline',    'label': "Exempla:", 'value': instance.get_exempla_display.strip()},
                {'type': 'safeline',    'label': "Notes:", 'value': instance.get_notes_display.strip()}                ]}
            ]

        related_objects = []

        # Show the SERMONS of this collection
        sermons = {'prefix': 'srm', 'title': 'Sermons of this collection (based on the year/place edition code)'}
        # Show the list of sermons that are part of this collection
        qs = Sermon.objects.filter(collection=instance).order_by('collection__idno', 'edition__idno', 'idno')
        rel_list =[]
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.get_code(), 'title': 'View this sermon', 'link': reverse('sermon_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.litday})
            rel_item.append({'value': item.get_bibref()})
            rel_item.append({'value': item.get_topics()})
            rel_list.append(rel_item)
        sermons['rel_list'] = rel_list
        sermons['columns'] = ['Code', 'Liturgical day', 'Thema', 'Topics']
        related_objects.append(sermons)

        # Show the MANUSCRIPTS that point to this collection
        manuscripts = {'prefix': 'man', 'title': 'Manuscripts that contain this collection'}
        # Get the list of manuscripts
        qs = Manuscript.objects.filter(collection=instance).order_by('info')
        rel_list = []
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.name, 'title': 'View this manuscript', 'link': reverse('manuscript_details', kwargs={'pk': item.id})})
            # OLD: rel_item.append({'value': item.get_info_display, 'title': 'View this manuscript', 'link': reverse('manuscript_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.has_link()})
            rel_item.append({'value': item.has_info()})
            rel_list.append(rel_item)
        manuscripts['rel_list'] = rel_list
        manuscripts['columns'] = ['Manuscript', 'Link', 'Information']
        related_objects.append(manuscripts)

        # Show the EDITIONS that point to this collection
        editions = {'prefix': 'edi', 'title': 'Printed editions that contain this collection'}
        # Get the list of editions
        qs = Edition.objects.filter(sermoncollection=instance).order_by('sermoncollection__idno', 'idno')
        rel_list = []
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.get_code(), 'title': 'View this edition', 'link': reverse('edition_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.get_place()})
            rel_item.append({'value': item.get_publishers()})
            rel_item.append({'value': item.get_date()})
            rel_item.append({'value': item.has_notes()})
            rel_list.append(rel_item)
        editions['rel_list'] = rel_list
        editions['columns'] = ['Code', 'Place', 'Publishers', 'Date', 'Notes']
        related_objects.append(editions)

        context['related_objects'] = related_objects
        # Return the context we have made
        return context


class CollectionList(BasicList):
    """Listview of sermon collections"""

    model = SermonCollection
    listform = CollectionListForm
    prefix = "coll"
    basic_name = "collection"
    plural_name = "Sermon collections"
    sg_name = "Sermon collection"
    basic_add = 'collection_add'
    has_select2 = True
    entrycount = 0
    order_default = ['idno', 'firstauthor__name', 'title', 'datecomp', 'place__name', 'numeditions', 'firstedition', '', '']
    order_cols = order_default
    order_heads = [{'name': 'Code',          'order': 'o=1', 'type': 'int', 'field': 'idno'}, 
                   {'name': 'Authors',       'order': 'o=2', 'type': 'str', 'custom': 'author'}, 
                   {'name': 'Title',         'order': 'o=3', 'type': 'str', 'field': 'title', 'main': True, 'linkdetails': True}, 
                   {'name': 'Year',          'order': 'o=4', 'type': 'str', 'field': 'datecomp'},
                   {'name': 'Place',         'order': 'o=5', 'type': 'str', 'custom': 'place'},
                   {'name': 'Editions',      'order': 'o=6', 'type': 'int', 'field': 'numeditions'},
                   {'name': 'First Edition', 'order': 'o=7', 'type': 'str', 'field': 'firstedition'},
                   {'name': '...place',      'order': '',    'type': 'str', 'custom': 'firstedition_place',
                    'title': 'Place of the first edition'},
                   {'name': '...publisher',  'order': '',    'type': 'str', 'custom': 'firstedition_publisher',
                    'title': 'First publisher of the first edition'}]
    filters = [ {"name": "Identifier",      "id": "filter_idno",    "enabled": False},
                {"name": "Author",          "id": "filter_author",  "enabled": False},
                {"name": "Title",           "id": "filter_title",   "enabled": False},
                {"name": "Place",           "id": "filter_place",   "enabled": False},
                {"name": "Has manuscripts", "id": "filter_hasmanu", "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'idno',      'dbfield': 'idno',      'keyS': 'idno'},
            {'filter': 'author',    'fkfield': 'authors',   'keyS': 'authorname', 'keyFk': 'title', 'keyList': 'authorlist', 'infield': 'id'},
            {'filter': 'title',     'dbfield': 'title',     'keyS': 'title'},
            {'filter': 'place',     'fkfield': 'place',     'keyS': 'placename', 'keyFk': 'name', 'keyList': 'placelist', 'infield': 'id' },
            {'filter': 'hasmanu',   'dbfield': 'nummanu',   'keyS': 'hasmanu',   'keyType': 'has'}
            ]},
        {'section': 'other', 'filterlist': [
            {'filter': 'tagnoteid',     'fkfield': 'notetags',          'keyS': 'tagnoteid',    'keyFk': 'id' },
            {'filter': 'taglituid',     'fkfield': 'liturgicaltags',    'keyS': 'taglituid',    'keyFk': 'id' },
            {'filter': 'tagcommid',     'fkfield': 'communicativetags', 'keyS': 'tagcommid',    'keyFk': 'id' },
            {'filter': 'tagqsrcid',     'fkfield': 'sourcetags',        'keyS': 'tagqsrcid',    'keyFk': 'id' },
            {'filter': 'tagexmpid',     'fkfield': 'exemplatags',       'keyS': 'tagexmpid',    'keyFk': 'id' }
            ]}
        ]

    def initializations(self):
        # Change TagLiturgical + TagCommunicative into TagKeyword
        litucomm = Information.get_kvalue("taglitucomm")
        if litucomm == None or litucomm == "" or litucomm != "done":
            # Convert liturtags into liturgical tags
            for coll in SermonCollection.objects.all():
                # GO through the liturgical tags
                for litur in coll.liturtags.all():
                    # Convert the TagLiturgical
                    word = litur.name
                    tgroup = litur.tgroup
                    tagkw = TagKeyword.objects.filter(name=word, tgroup=tgroup).first()
                    if tagkw == None:
                        tagkw = TagKeyword.objects.create(name=word, tgroup=tgroup)
                    # Add this to coll.liturgicaltags
                    coll.liturgicaltags.add(tagkw)
                # Go through the communicative tags
                for commu in coll.commutags.all():
                    # Convert the TagCommunicative
                    word = commu.name
                    tgroup = commu.tgroup
                    tagkw = TagKeyword.objects.filter(name=word, tgroup=tgroup).first()
                    if tagkw == None:
                        tagkw = TagKeyword.objects.create(name=word, tgroup=tgroup)
                    # Add this to coll.communicativetags
                    coll.communicativetags.add(tagkw)

            Information.set_kvalue("taglitucomm", "done")
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        # FIgure out what to return
        if custom == "author":
            html.append(instance.get_authors())
        elif custom == "place":
            html.append(instance.place.name)
        elif custom == "firstedition_place":
            edi = instance.first_edition_obj()
            place = "" if edi == None or edi.place == None else edi.place.name
            html.append(place)
        elif custom == "firstedition_publisher":
            edi = instance.first_edition_obj()
            publisher = "" if edi == None or edi.firstpublisher == None else edi.firstpublisher.name
            html.append(publisher)
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle


class ConceptListView(BasicListView):
    """Listview of sermon collections"""

    model = Concept
    listform = ConceptListForm
    prefix = "cnc"
    template_name = 'seeker/concept_list.html'
    plural_name = "Concepts"
    entrycount = 0
    order_default = ['name', 'language']
    order_cols = ['name', 'language']
    order_heads = [{'name': 'Language', 'order': 'o=2', 'type': 'str'},
                   {'name': 'Concept',  'order': 'o=1', 'type': 'str'}]
    filters = [ {"name": "Concept",     "id": "filter_name",    "enabled": False},
                {"name": "Language",    "id": "filter_language",  "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'name',      'dbfield': 'name',      'keyS': 'cncname',  'keyList': 'cnclist', 'infield': 'name'},
            {'filter': 'language',  'dbfield': 'language',  'keyS': 'lngname',  'keyList': 'lnglist', 'infield': 'abbr'} ]}
        ]


class PublisherListView(BasicListView):
    """Listview of sermon collections"""

    model = Publisher
    listform = PublisherListForm
    prefix = "pb"
    template_name = 'seeker/publisher_list.html'
    plural_name = "Publishers"
    entrycount = 0
    order_default = ['name']
    order_cols = ['name']
    order_heads = [{'name': 'Publisher', 'order': 'o=1', 'type': 'str'}]
    filters = [ {"name": "Publisher",     "id": "filter_name",    "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'name',      'dbfield': 'name',      'keyS': 'pbname',   'keyList': 'pblist', 'infield': 'name'} ]}
        ]


class TgroupListView(BasicList):
    """Listview of tgroups"""

    model = Tgroup
    listform = TgroupForm
    prefix = "tgr"
    basic_name = "tgroup"
    plural_name = "Tag groups"
    sg_name = "Tag group"
    order_default = ['name', '']
    order_cols = order_default
    order_heads = [{'name': 'Name',          'order': 'o=1', 'type': 'str', 'field': 'name', 'main': True, 'linkdetails': True},
                   {'name': 'Counts',        'order': '',    'type': 'str', 'custom': 'counts'}]
    filters = [{"name": "Name",          "id": "filter_name",            "enabled": False}]
    searches = [
       {'section': '', 'filterlist': [
            {'filter': 'name',   'dbfield': 'name',       'keyS': 'name'}
            ]},
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        # FIgure out what to return
        if custom == "counts":
            # Get the number of tgroups for each of the tag types
            iLitu = instance.tgroupslitu.all().count()
            iComm = instance.tgroupscomm.all().count()
            iKeyw = instance.tgroupskeyw.all().count()
            if iLitu > 0:
                url = "{}?tagl-tgrlist={}".format(reverse('tagliturgical_list'), instance.id)
                html.append("<span class='badge' title='liturgical tags'><a class='nostyle' href='{}'>{}</a></span>".format(url, iLitu))
            if iComm > 0:
                url = "{}?tagc-tgrlist={}".format(reverse('tagcommunicative_list'), instance.id)
                html.append("<span class='badge' title='communicative tags'><a class='nostyle' href='{}'>{}</a></span>".format(url, iComm))
            if iKeyw > 0:
                url = "{}?tagk-tgrlist={}".format(reverse('tagkeyword_list'), instance.id)
                html.append("<span class='badge' title='keyword tags'><a class='nostyle' href='{}'>{}</a></span>".format(url, iKeyw))
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle

    def initializations(self):
        general = Information.get_kvalue("taggroup_general")
        if general == None or general == "" or general != "done":
            old = Tgroup.objects.filter(name="general").first()
            new = Tgroup.objects.filter(name="New").first()
            if old and new:
                # Change the 'general' into 'General'
                with transaction.atomic():
                    for obj in TagKeyword.objects.filter(tgroup=old):
                        obj.tgroup = new
                        obj.save()
            Information.set_kvalue("taggroup_general", "done")
        return None


class TgroupEdit(BasicDetails):
    model = Tgroup
    mForm = TgroupForm
    prefix = "tgr"
    titlesg = "Tag group"
    title = "Tgroup Edit"
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'safe', 'label': "Name:", 'value': instance.name, 'field_key': 'name'}
            ]
        # Return the context we have made
        return context

    def before_save(self, form, instance):
        bResult = True
        msg = ""
        name = form.instance.name
        obj = Tgroup.objects.filter(name__iexact=name).first()
        if obj != None:
            msg = "Sorry, group [{}] already exists. Cannot have two instances of the same Tag group.".format(obj.name)
            bResult = False
        return bResult, msg


class TgroupDetails(TgroupEdit):
    rtype = "html"


class TagListView(BasicList):
    """Listview of tags"""

    model = None
    listform = None
    prefix = ""
    urldef = ""
    basic_name = ""
    plural_name = ""
    sg_name = ""
    has_select2 = True
    order_default = ['tgroup', 'name', '']
    order_cols = ['tgroup', 'name', '']
    order_heads = [{'name': 'Group',    'order': 'o=1', 'type': 'str', 'custom': 'group', 'linkdetails': True},
                   {'name': 'Tag',      'order': 'o=2', 'type': 'str', 'field':  'name',  'linkdetails': True, 'main': True},
                   {'name': 'Usage',    'order': '',    'type': 'str', 'custom': 'usage'}]
    filters = [ {"name": "Tag",     "id": "filter_name",    "enabled": False},
                {"name": "Group",   "id": "filter_tgroup",  "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'name',      'dbfield': 'name',      'keyS': 'tagname',   'keyList': 'taglist', 'infield': 'name'},
            {'filter': 'tgroup',    'fkfield': 'tgroup',    'keyFk': 'name',     'keyList': 'tgrlist', 'infield': 'id'} ] }
        ]

    def initializations(self):
        if self.prefix == "tagl":
            self.basic_add = 'taglitu_add'
        elif self.prefix == "tagc":
            self.basic_add = 'tagcomm_add'
        elif self.prefix == "tagkw":
            self.basic_add = 'tagkeyw_add'
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        # FIgure out what to return
        if custom == "usage":
            # Get the number of times each tag is used
            for tagitem in instance.get_list():
                if tagitem['count'] > 0:
                    url = "{}?{}".format(tagitem['params'], tagitem['count'])
                    html.append("<span class='badge {}' title='{}'><a ref='{}'>{}</a></span>".format(
                        tagitem['css'], tagitem['type'], url, tagitem['count']))
        elif custom == "group":
            # Show the group
            html.append(instance.tgroup.name)

        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle


class TagKeywordListView(TagListView):
    model = TagKeyword
    listform = TagKeywordListForm
    prefix = "tagkw"
    urldef = "tagkeyword_list"

    basic_name = "tagkeyword"
    plural_name = "Keyword tags"
    sg_name = "Keyword tag"


class TagKeywordDetailView(PassimDetails):
    model = TagKeyword
    mForm = None
    template_name = 'generic_details.html'
    prefix = "tagkw"
    title = "KeywordTagDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        # The main item of the view is the name of the tag itself
        context['mainitems'] = [
            {'type': 'bold',  'label': "Tag", 'value': instance.name, 'link': ""},
            {'type': 'plain',  'label': "Group", 'value': instance.tgroup.name, 'link': ""}
            ]
        # Add the counts in different lists (collection, sermon, manuscript, edition) to the view
        lst_count = instance.get_list()
        for oCount in lst_count:
            oItem = dict(type='plain', label=oCount['type'], value=oCount['count'], align='right')
            context['mainitems'].append(oItem)

        # Make sure to show each of the sections in [lst_count] separately
        related_objects = []

        # This tag in: author.info
        infos = {'prefix': 'auth', 'title': 'Author descriptions that use this tag in their [Information]'}
        # Show the list of sermons that contain this tag
        qs = instance.author_infotags.all().order_by('name')
        if qs.count() > 0:
            rel_list =[]
            for item in qs:
                rel_item = []
                rel_item.append({'value': item.name, 'title': 'View this author', 'link': reverse('author_details', kwargs={'pk': item.id})})
                rel_item.append({'value': item.get_info_display})
                rel_list.append(rel_item)
            infos['rel_list'] = rel_list
            infos['columns'] = ['Name', 'Information']
            related_objects.append(infos)

        # This tag in: manuscript.info
        infos = {'prefix': 'manu', 'title': 'Manuscript descriptions that use this tag in their [Information]'}
        # Show the list of sermons that contain this tag
        qs = instance.manuscript_infotags.all().order_by('name')
        if qs.count() > 0:
            rel_list =[]
            for item in qs:
                rel_item = []
                rel_item.append({'value': item.name, 'title': 'View this manuscript', 'link': reverse('manuscript_details', kwargs={'pk': item.id})})
                rel_item.append({'value': item.get_info_display})
                rel_item.append({'value': item.link})
                rel_list.append(rel_item)
            infos['rel_list'] = rel_list
            infos['columns'] = ['Name', 'Information', 'Link']
            related_objects.append(infos)

        # Sermon listviews
        sermondescriptions = [
            {'field': 'DivisionL',   'head': 'Division (Latin)',    'display': 'divisionL',
                'qs': instance.sermon_divisionltags.all().order_by('code')},
            {'field': 'DivisionE',   'head': 'Division (English)',  'display': 'divisionE',
                'qs': instance.sermon_divisionetags.all().order_by('code')},
            {'field': 'Summary',   'head': 'Context: Summary',      'display': '',
                'qs': instance.sermon_summarynotes.all().order_by('code')},
            {'field': 'Notes',     'head': 'Context:  Note',        'display': 'note', 
                'qs': instance.sermon_notetags.all().order_by('code')}
            ]
        for description in sermondescriptions:
            base = {'prefix': 'srm', 'title': 'Sermons that use this tag in their [{}]'.format(description['field'])}
            qs = description['qs']
            if qs.count() > 0:
                rel_list =[]
                displayfieldname = "get_{}_display".format(description['display'])
                for item in qs:
                    rel_item = []
                    rel_item.append({'value': item.get_code(), 'title': 'View this sermon', 'link': reverse('sermon_details', kwargs={'pk': item.id})})
                    rel_item.append({'value': item.litday})
                    rel_item.append({'value': item.get_authors()})
                    if description['field'] == "Summary":
                        rel_item.append({'value': item.get_summary_markdown(instance)})
                    else:
                        rel_item.append({'value': getattr(item, displayfieldname)})
                    rel_list.append(rel_item)
                base['rel_list'] = rel_list
                base['columns'] = ['Code', 'Liturgical day', 'Authors', description['head']]
                related_objects.append(base)

        # Collection listviews
        collectiondescriptions = [
            {'field': 'relationship with [Liturgical] texts',   'display': 'liturgical',    'head': 'Liturgical',
                'qs': instance.collection_liturgicaltags.all().order_by('idno')},
            {'field': '[Communicative strategy]',               'display': 'communicative', 'head': 'Communicative strategy', 
                'qs': instance.collection_communicativetags.all().order_by('idno')},
            {'field': '[Sources]',                              'display': 'sources',       'head': 'Sources',                 
                'qs': instance.collection_sourcenotes.all().order_by('idno')},
            {'field': '[Notes]',                                'display': 'notes',         'head': 'Notes',                   
                'qs': instance.collection_notes.all().order_by('idno')},
            {'field': '[Exempla]',                              'display': 'exempla',       'head': 'Exempla',                
                'qs': instance.collection_exempla.all().order_by('idno')}
            ]
        for description in collectiondescriptions:
            base = {'prefix': 'col', 'title': 'Collections that use this tag in their {}'.format(description['field'])}
            qs = description['qs']
            if qs.count() > 0:
                rel_list =[]
                displayfieldname = "get_{}_display".format(description['display'])
                for item in qs:
                    rel_item = []
                    rel_item.append({'value': item.idno, 'title': 'View this collection', 'link': reverse('collection_details', kwargs={'pk': item.id})})
                    rel_item.append({'value': item.title})
                    rel_item.append({'value': item.datecomp})
                    rel_item.append({'value': item.get_place()})
                    rel_item.append({'value': getattr(item, displayfieldname)})
                    rel_list.append(rel_item)
                base['rel_list'] = rel_list
                base['columns'] = ['Idno', 'Title', 'Date', 'Place', description['head']]
                related_objects.append(base)
 
        # Edition listviews
        editiondescriptions = [
            {'field': 'DateComment',    'qs': instance.edition_datecommenttags.all().order_by('code')},
            {'field': 'Notes',          'qs': instance.edition_notetags.all().order_by('code')},
            {'field': 'Frontpage',      'qs': instance.edition_frontpagetags.all().order_by('code')},
            {'field': 'Prologue',       'qs': instance.edition_prologuetags.all().order_by('code')},
            {'field': 'Dedicatory',     'qs': instance.edition_dedicatorytags.all().order_by('code')},
            {'field': 'Contents',       'qs': instance.edition_contentstags.all().order_by('code')},
            {'field': 'Sermonlist',     'qs': instance.edition_sermonlisttags.all().order_by('code')},
            {'field': 'OtherTexts',     'qs': instance.edition_othertextstags.all().order_by('code')},
            {'field': 'Images',         'qs': instance.edition_imagestags.all().order_by('code')},
            {'field': 'Fulltitle',      'qs': instance.edition_fulltitletags.all().order_by('code')},
            {'field': 'Colophon',       'qs': instance.edition_colophontags.all().order_by('code')}
            ]
        for description in editiondescriptions:
            base = {'prefix': 'edi', 'title': 'Editions that use this tag in their [{}]'.format(description['field'])}
            qs = description['qs']
            if qs.count() > 0:
                rel_list =[]
                for item in qs:
                    rel_item = []
                    rel_item.append({'value': item.get_code(), 'title': 'View this edition', 'link': reverse('edition_details', kwargs={'pk': item.id})})
                    rel_item.append({'value': item.get_place()})
                    rel_item.append({'value': item.get_editors()})
                    rel_item.append({'value': item.get_date()})
                    rel_item.append({'value': item.has_notes()})
                    rel_list.append(rel_item)
                base['rel_list'] = rel_list
                base['columns'] = ['Code', 'Place', 'Editors', 'Date', 'Notes']
                related_objects.append(base)

        # Publisher listviews
        publisherdescriptions = [
            {'field': 'Information',    'display': 'info',    'head': 'Information',
             'qs': instance.publisher_infotags.all().order_by('name')}
            ]
        for description in publisherdescriptions:
            base = {'prefix': 'pub', 'title': 'Publisher descriptions that use this tag in their [{}]'.format(description['field'])}
            qs = description['qs']
            if qs.count() > 0:
                rel_list =[]
                displayfieldname = "get_{}_display".format(description['display'])
                for item in qs:
                    rel_item = []
                    rel_item.append({'value': item.name, 'title': 'View this publisher', 'link': reverse('publisher_details', kwargs={'pk': item.id})})
                    rel_item.append({'value': item.get_info_display})
                    rel_list.append(rel_item)
                base['rel_list'] = rel_list
                base['columns'] = ['Name', description['head']]
                related_objects.append(base)

        context['related_objects'] = related_objects
        # Return the resulting context
        return context


class ReportListView(ListView):
    """Listview of reports"""

    model = Report
    paginate_by = 20
    template_name = 'seeker/report_list.html'
    entrycount = 0
    bDoTime = True

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ReportListView, self).get_context_data(**kwargs)

        # Get parameters
        initial = self.request.GET

        # Prepare searching
        #search_form = ReportSearchForm(initial)
        #context['searchform'] = search_form

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the title of the application
        context['title'] = "Lentensermons reports"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_app_uploader'] = user_is_ingroup(self.request, app_uploader)
        context['is_app_editor'] = user_is_ingroup(self.request, app_editor)

        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, "Upload reports", True)
        context['prevpage'] = get_previous_page(self.request)

        # Return the calculated context
        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)
  
    def get_queryset(self):
        # Get the parameters passed on with the GET or the POST request
        get = self.request.GET if self.request.method == "GET" else self.request.POST
        get = get.copy()
        self.get = get

        # Calculate the final qs
        qs = Report.objects.all().order_by('-created')

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs


class ReportDetailsView(PassimDetails):
    model = Report
    mForm = ReportEditForm
    template_name = 'seeker/report_details.html'
    prefix = 'report'
    title = "ReportDetails"
    rtype = "html"

    def add_to_context(self, context, instance):
        context['is_app_editor'] = user_is_ingroup(self.request, app_editor)
        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, "Report edit", False)
        context['prevpage'] = get_previous_page(self.request)
        return context


class ReportDownload(BasicPart):
    MainModel = Report
    template_name = "seeker/download_status.html"
    action = "download"
    dtype = "csv"       # Download Type

    def custom_init(self):
        """Calculate stuff"""
        
        dt = self.qd.get('downloadtype', "")
        if dt != None and dt != '':
            self.dtype = dt

    def get_data(self, prefix, dtype):
        """Gather the data as CSV, including a header line and comma-separated"""

        # Initialize
        lData = []

        # Unpack the report contents
        sData = self.obj.contents

        if dtype == "json":
            # no need to do anything: the information is already in sData
            pass
        else:
            # Convert the JSON to a Python object
            oContents = json.loads(sData)
            # Get the headers and the list
            headers = oContents['headers']

            # Create CSV string writer
            output = StringIO()
            delimiter = "\t" if dtype == "csv" else ","
            csvwriter = csv.writer(output, delimiter=delimiter, quotechar='"')

            # Write Headers
            csvwriter.writerow(headers)

            # Two lists
            todo = [oContents['list'], oContents['read'] ]
            for lst_report in todo:

                # Loop
                for item in lst_report:
                    row = []
                    for key in headers:
                        if key in item:
                            row.append(item[key])
                        else:
                            row.append("")
                    csvwriter.writerow(row)

            # Convert to string
            sData = output.getvalue()
            output.close()

        return sData


class SermonDetailsView(PassimDetails):
    model = Sermon
    mForm = None
    template_name = 'generic_details.html'  # 'seeker/sermon_view.html'
    prefix = ""
    title = "SermonDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        # Get the link to the sermon collection
        sc = reverse('collection_details', kwargs={'pk': instance.collection.id})
        context['mainitems'] = [
            {'type': 'bold',  'label': "Collection:", 'value': instance.collection.title, 'link': sc},
            {'type': 'plain', 'label': "Code:", 'value': instance.get_code()},
            {'type': 'plain', 'label': "Liturgical day:", 'value': instance.litday},
            {'type': 'safe',  'label': "Thema:", 'value': instance.get_full_thema()},
            {'type': 'line',  'label': "Topics:", 'value': instance.get_topics_markdown()},
            {'type': 'line',  'label': "Concepts:", 'value': instance.get_concepts_markdown()},
            ]

        context['sections'] = [
            {'name': 'Main division', 'id': 'sermo_division', 'fields': [
                {'type': 'safeline',    'label': "Original:", 'value': instance.get_divisionL_display.strip()},
                {'type': 'safeline',    'label': "Translation:", 'value': instance.get_divisionE_display.strip()},
                ]},
            {'name': 'Summary', 'id': 'sermo_summary', 'fields': [
                {'type': 'line',    'label': "", 'value': instance.get_summary_markdown()}                ]},
            {'name': 'General notes', 'id': 'sermo_general', 'fields': [
                {'type': 'safeline',    'label': "", 'value': instance.get_note_display.strip()}                ]}
            ]

        return context


class EditionList(BasicList):
    """Listview of editions"""

    model = Edition
    listform = EditionListForm
    prefix = "edi" 
    admin_editable = True
    basic_add = 'edition_add'
    has_select2 = True
    plural_name = "Editions"
    order_default = ['sermoncollection__idno;idno', 'sermoncollection__firstauthor__name', 'sermoncollection__title', 'place__name', 'firstpublisher__name', 'date', '']
    order_cols = order_default
    order_heads = [{'name': 'Code',       'order': 'o=1', 'type': 'int', 'custom': 'code',      'linkdetails': True}, 
                   {'name': 'Authors',    'order': 'o=2', 'type': 'str', 'custom': 'authors'}, 
                   {'name': 'Collection', 'order': 'o=3', 'type': 'str', 'custom': 'coltitle',  'main': True}, 
                   {'name': 'Place',      'order': 'o=4', 'type': 'str', 'custom': 'place'},
                   {'name': 'Publishers', 'order': 'o=5', 'type': 'str', 'custom': 'publishers'},
                   {'name': 'Year',       'order': 'o=6', 'type': 'str', 'custom': 'year'},
                   {'name': 'Notes?',     'order': '',    'type': 'str', 'custom': 'hasnotes'}]
    filters = [ {"name": "Collection",  "id": "filter_collection",  "enabled": False},
                {"name": "Author",      "id": "filter_author",      "enabled": False},
                {"name": "Place",       "id": "filter_place",       "enabled": False}
                ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'collection','fkfield': 'sermoncollection',          'keyS': 'colltitle',  'keyFk': 'title', 'keyList': 'colllist', 'infield': 'id'},
            {'filter': 'author',    'fkfield': 'sermoncollection__authors', 'keyS': 'authorname', 'keyFk': 'title', 'keyList': 'authorlist', 'infield': 'id'},
            {'filter': 'place',     'fkfield': 'place',                     'keyS': 'placename',  'keyFk': 'name',  'keyList': 'placelist', 'infield': 'id' }
            ]},
        {'section': 'other', 'filterlist': [
            {'filter': 'tagnoteid', 'fkfield': 'notetags',  'keyS': 'tagnoteid', 'keyFk': 'id' }
            ]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        if custom == "code":
            html.append(instance.get_code())
            sTitle = "view the edition"
        elif custom == "authors":
            if instance.sermoncollection:
                html.append(instance.sermoncollection.get_authors())
            else:
                html.append("-")
        elif custom == 'coltitle':
            if instance.sermoncollection:
                url = reverse( 'collection_details', kwargs={'pk': instance.sermoncollection.id})
                html.append("<span><a class='nostyle' href='{}'>{}</a></span>".format(url, instance.sermoncollection.title))
                sTitle = "view the collection"
            else:
                html.append("-")
                sTitle = "no collection"
        elif custom == 'place':
            place = "-" if instance.place == None else instance.place.name
            html.append(place)
        elif custom == 'publishers':
            sTitle = instance.get_publisher()
            html.append('<span style="font-size: smaller;">{}</span>'.format(sTitle[:20]))
        elif custom == 'year':
            html.append(instance.get_date())
        elif custom == "hasnotes":
            html.append(instance.has_notes())
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle

    def initializations(self):
        publishers_done = Information.get_kvalue("publishers")
        if publishers_done != "done":
            if Edition.do_publishers():
                Information.set_kvalue("publishers", "done")

        return None


class EditionDetailsView(PassimDetails):
    model = Edition
    mForm = None
    template_name = 'generic_details.html'  # 'seeker/sermon_view.html'
    prefix = ""
    title = "EditionDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        sLocation = ""
        if hasattr(instance, 'place') and instance.place:
            sLocation = instance.place.name
        context['mainitems'] = [
            {'type': 'plain',   'label': "Code:", 'value': instance.get_code(), 'title': 'Collection number / Edition number within that collection'},
            {'type': 'safeline', 'label': "Date:", 'value': instance.get_full_date()},
            {'type': 'plain',   'label': "Place:", 'value': sLocation},
            {'type': 'plain',   'label': "Publisher:", 'value': instance.get_publisher() },
            {'type': 'plain',   'label': "Format:", 'value': instance.get_format_display() },
            {'type': 'plain',   'label': "Folia:", 'value': instance.folia},
            {'type': 'plain',   'label': "Number of sermons:", 'value': instance.numsermons},
            {'type': 'plain',   'label': "External databases:", 'value': instance.dbcodes.all().order_by('name'),
             'multiple': True}
            # MORE INFORMATION SHOULD FOLLOW
            ]
        
        context['sections'] = [
            {'name': 'Paratextual elements', 'id': 'edi_paratextual', 'fields': [
                {'type': 'safeline', 'label': "Front page:", 'value': instance.get_frontpage_display.strip() , 'title': 'Front page / Title page' },
                {'type': 'safeline', 'label': "Prologue:", 'value': instance.get_prologue_display.strip()},
                {'type': 'safeline', 'label': "Dedicatory letter:", 'value': instance.get_dedicatory_display.strip()},
                {'type': 'safeline', 'label': "Table of contents:", 'value': instance.get_contents_display.strip()},
                {'type': 'safeline', 'label': "List of sermons:", 'value': instance.get_sermonlist_display.strip()},
                {'type': 'safeline', 'label': "Other texts:", 'value': instance.get_othertexts_display.strip()},
                {'type': 'safeline', 'label': "Images:", 'value': instance.get_images_display.strip()},
                {'type': 'safeline', 'label': "Full title:", 'value': instance.get_fulltitle_display.strip()},
                {'type': 'safeline', 'label': "Colophon:", 'value': instance.get_colophon_display.strip()},
                ]},
            {'name': 'General notes', 'id': 'coll_general', 'fields': [
                {'type': 'safeline',    'label': "Notes:", 'value': instance.get_note_display.strip()}                ]}
            ]

        # Add link objects: link to the SermonCollection I am part of
        link_objects = []
        sc = reverse('collection_details', kwargs={'pk': instance.sermoncollection.id})
        link = dict(name="Sermon collection for this edition", label="{}".format(instance.sermoncollection.title), value=sc )
        link_objects.append(link)
        context['link_objects'] = link_objects

        related_objects = []

        # Show the CONSULTINGS of this edition
        consultings = {'prefix': 'cns', 'title': 'Consultings of this edition'}
        # Show the list of sermons that are part of this collection
        qs = instance.consultings.all().order_by('location')
        rel_list =[]
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.location, 'location': 'View this consulting', 'link': reverse('consulting_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.ownership})
            rel_list.append(rel_item)
        consultings['rel_list'] = rel_list
        consultings['columns'] = ['Location', 'Ownership']
        related_objects.append(consultings)

        context['related_objects'] = related_objects

        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, "Edition details", False)
        context['prevpage'] = get_previous_page(self.request)
        return context


class PublisherDetailsView(PassimDetails):
    model = Publisher
    mForm = None
    template_name = 'generic_details.html' 
    prefix = "publ"
    title = "PublisherDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",         'value': instance.name},
            {'type': 'line',  'label': "Information:",  'value': instance.get_info_markdown()}
            ]
        return context


class AuthorListView(BasicList):
    """Listview of authors"""

    model = Author
    listform = AuthorListForm
    prefix = "auth"
    # template_name = 'seeker/author_list.html'
    admin_editable = True
    order_cols = ['name', 'info']
    order_default = order_cols
    order_heads = [{'name': 'Name',        'order': 'o=1', 'type': 'str', 'custom': 'name', 'default': "-", 'linkdetails': True},
                   {'name': 'Information', 'order': 'o=2', 'type': 'str', 'custom': 'info',  'main': True}]
    filters = [ {"name": "Name", "id": "filter_author",     "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'author',   'dbfield': 'name', 'keyS': 'name' }]},
        {'section': 'other', 'filterlist': [
            {'filter': 'tagnoteid',     'fkfield': 'infotags',      'keyS': 'tagnoteid',    'keyFk': 'id' },
            ]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        if custom == "name":
            html.append(instance.name)
        elif custom == "info":
            html.append(instance.get_info_markdown())
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle


class AuthorDetailsView(PassimDetails):
    model = Author
    mForm = None
    template_name = 'generic_details.html'  # 'seeker/sermon_view.html'
    prefix = ""
    title = "AuthorDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        context['mainitems'] = [
            {'type': 'plain',  'label': "Name:",        'value': instance.name},
            {'type': 'line',   'label': "Information:", 'value': instance.get_info_markdown()}
            ]
        related_objects = []

        # Show the collections containing this author
        collections = {'prefix': 'col', 'title': 'Sermon collections that have this author'}
        # Show the list of collections using this author
        qs = SermonCollection.objects.filter(authors__id=instance.id).order_by('idno')
        rel_list =[]
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.idno, 'title': 'View this collection', 'link': reverse('collection_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.title})
            rel_item.append({'value': item.datecomp})
            rel_item.append({'value': item.get_place()})
            rel_list.append(rel_item)
        collections['rel_list'] = rel_list
        collections['columns'] = ['Collection', 'Title', 'Date', 'Place']
        related_objects.append(collections)

        context['related_objects'] = related_objects
        # Return the context we have made
        return context


class ConceptDetailsView(PassimDetails):
    model = Concept
    mForm = None
    template_name = 'generic_details.html' 
    prefix = "cnc"
    title = "ConceptDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        context['mainitems'] = [
            {'type': 'plain', 'label': "Concept:",  'value': instance.name},
            {'type': 'plain', 'label': "Language:", 'value': instance.get_language_display()}
            ]
        return context


class ManuscriptListView(BasicList):
    """Listview of manuscripts"""

    model = Manuscript
    listform = ManuscriptForm
    prefix = "manu"
    admin_editable = True
    basic_add = "manuscript_add"
    has_select2 = True
    order_cols = ['collection__authors__name', 'collection__title', 'name', '']
    order_default = order_cols
    order_heads = [{'name': 'Author',       'order': 'o=1', 'type': 'str', 'custom': 'author'},
                   {'name': 'Collection',   'order': 'o=2', 'type': 'str', 'custom': 'collection'},
                   {'name': 'Name',         'order': 'o=3', 'type': 'str', 'custom': 'name',       'linkdetails': True,  'main': True},
                   {'name': 'Link?',        'order': '',    'type': 'str', 'custom': 'link'},
                   {'name': 'Notes?',       'order': '',    'type': 'str', 'custom': 'notes'}]
    filters = [ {"name": "Collection",  "id": "filter_collection",  "enabled": False},
                {"name": "Name",        "id": "filter_name",        "enabled": False},
                {"name": "Link",        "id": "filter_link",        "enabled": False},
                {"name": "Information", "id": "filter_info",        "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'collection','fkfield': 'collection','keyS': 'collname', 'keyFk': 'title', 'keyList': 'collectionlist', 'infield': 'id'},
            {'filter': 'name',      'dbfield': 'name',      'keyS': 'name' },
            {'filter': 'link',      'dbfield': 'link',      'keyS': 'link' },
            {'filter': 'info',      'dbfield': 'info',      'keyS': 'info' }]},
        {'section': 'other', 'filterlist': [
            {'filter': 'tagnoteid', 'fkfield': 'infotags',  'keyS': 'tagnoteid', 'keyFk': 'id' }
            ]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        if custom == "collection":
            url = reverse("collection_details", kwargs={'pk': instance.collection.id})
            html.append("<span><a class='nostyle' href='{}'>{}</a></span>".format(url, instance.collection.title))
            sTitle = "View the sermon collection"
        elif custom == "author":
            # Get the name of the first author
            authors = instance.collection.authors.all()
            if authors.count() == 0:
                html.append("(none)")
            else:
                url = reverse("author_details", kwargs={'pk': authors.first().id})
                html.append("<span><a class='nostyle' href='{}'>{}</a></span>".format(url, authors.first().name))
                sTitle = "View the author details"
        elif custom == "name":
            sName = instance.name[:80]
            if len(instance.name) > 80:
                sName = "{}...".format(sName)
            html.append(sName)
            sTitle = instance.name
        elif custom == "info":
            html.append(instance.get_info_markdown())
        elif custom == "notes":
            if instance.info and instance.info != "":
                html.append("*")
        elif custom == "link":
            if instance.has_link():
                html.append("*")
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle


class ManuscriptDetailsView(PassimDetails):
    model = Manuscript
    mForm = None
    template_name = 'generic_details.html'  # 'seeker/sermon_view.html'
    prefix = ""
    title = "ManuscriptDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        context['mainitems'] = [
            {'type': 'bold',  'label': "Collection:",  'value': instance.collection.title, 'link': reverse('collection_details', kwargs={'pk': instance.collection.id})},
            {'type': 'plain', 'label': "Manuscript:", 'value': instance.name},
            {'type': 'line',  'label': "Information:", 'value': instance.get_info_markdown()},
            {'type': 'safe',  'label': "Link name (if available):", 'value': instance.get_link_markdown(), 'link': instance.url},
            {'type': 'safe',  'label': "Author[s] (collection):", 'value': instance.collection.authorbadges()}
            ]
        related_objects = []

        ## Show the SERMONS of this manuscript
        #sermons = {'prefix': 'srm', 'title': 'Sermons that are part of this manuscript'}
        ## Show the list of sermons that are part of this manuscript
        #qs = Sermon.objects.filter(collection=instance.collection).order_by('code')
        #rel_list =[]
        #for item in qs:
        #    rel_item = []
        #    rel_item.append({'value': item.code, 'title': 'View this sermon', 'link': reverse('sermon_details', kwargs={'pk': item.id})})
        #    rel_item.append({'value': item.litday})
        #    rel_item.append({'value': item.get_bibref()})
        #    rel_list.append(rel_item)
        #sermons['rel_list'] = rel_list
        #sermons['columns'] = ['Code', 'Liturgical day', 'Reference']
        #related_objects.append(sermons)

        context['related_objects'] = related_objects
        # Return the context we have made
        return context


class NewsListView(BasicListView):
    """Allow user to view news items"""

    model = NewsItem
    listform = NewsForm
    prefix = "news"
    template_name = 'seeker/news_list.html'
    plural_name = "News items"
    entrycount = 0
    order_default = ['status', '-saved', 'title']
    order_cols = ['title', 'util', 'status', 'created', 'saved']
    order_heads = [{'name': 'Title',     'order': 'o=1', 'type': 'str'},
                   {'name': 'Remove at', 'order': 'o=2', 'type': 'str'},
                   {'name': 'Status',    'order': 'o=3', 'type': 'str'},
                   {'name': 'Created',   'order': 'o=4', 'type': 'str'},
                   {'name': 'Saved',     'order': 'o=5', 'type': 'str'}]
    filters = [ {"name": "Title",  "id": "filter_title",    "enabled": False},
                {"name": "Status", "id": "filter_status",   "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'title',  'dbfield': 'title',   'keyS': 'title'},
            {'filter': 'status', 'dbfield': 'status',  'keyS': 'status'} ]}
        ]


class NewsDetailsView(PassimDetails):
    model = NewsItem
    mForm = NewsForm
    template_name = 'generic_details.html'
    prefix = "news"
    title = "NewsDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        context['mainitems'] = [
            {'type': 'bold',  'label': "Title:",  'value': instance.title, 'link': reverse('newsitem_details', kwargs={'pk': instance.id})},
            {'type': 'safe',  'label': "Message:", 'value': instance.msg},
            {'type': 'plain', 'label': "Status:", 'value': instance.get_status_display()},
            {'type': 'safe',  'label': "Created:", 'value': get_date_display( instance.created)},
            {'type': 'safe',  'label': "Savid:", 'value': get_date_display(instance.saved)},
            {'type': 'safe',  'label': "Valid until:", 'value': get_date_display(instance.until)}
            ]
        related_objects = []

        context['related_objects'] = related_objects
        # Return the context we have made
        return context


class LitrefListView(BasicList):
    model = Litref
    listform = LitrefForm
    prefix = "lit"
    plural_name = "References"
    sg_name = "Reference"
    order_cols = ['short', 'full']
    order_default = ['full', 'short']
    order_heads = [{'name': 'Short',          'order': 'o=1', 'type': 'str', 'custom': 'short', 'default': "-", 'linkdetails': True},
                   {'name': 'Full reference', 'order': 'o=2', 'type': 'str', 'custom': 'full',  'main': True}]
    filters = [ {"name": "Reference", "id": "filter_reference",     "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'reference',   'dbfield': 'full', 'keyS': 'full' }]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        if custom == "short":
            html.append(instance.get_short_markdown())
        elif custom == "full":
            html.append(instance.get_full_markdown())
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle


class LitrefEditView(BasicDetails):
    model = Litref
    mForm = LitrefForm
    prefix = "lit"
    titlesg = "Reference"
    title = "Reference Edit"
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'safe', 'label': "Full reference:", 'value': instance.get_full_markdown(), 'field_key': 'full'},
            {'type': 'safe', 'label': "Short reference:", 'value': instance.get_short_markdown(), 'field_key': 'short'}
            ]
        # Return the context we have made
        return context


class LitrefDetailsView(LitrefEditView):
    rtype = "html"
