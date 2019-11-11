"""
Definition of views for the SEEKER app.
"""

from django.contrib import admin
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
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

# Application specific
from lentensermons.settings import APP_PREFIX, MEDIA_DIR
from lentensermons.utils import ErrHandle
from lentensermons.seeker.forms import UploadFileForm, UploadFilesForm, SearchUrlForm, LocationForm, LocationRelForm, ReportEditForm, \
    SignUpForm
from lentensermons.seeker.models import get_current_datetime, adapt_search, get_searchable, get_now_time, \
    User, Group, Action, Report, Status, NewsItem, Profile, Visit, \
    Location, LocationRelation, Author, \
    Sermon, SermonCollection, Edition, Manuscript, TagCommunicative, TagLiturgical, TagNote

# Some constants that can be used
paginateSize = 20
paginateSelect = 15
paginateValues = (100, 50, 20, 10, 5, 2, 1, )

# Global debugging 
bDebug = False


def treat_bom(sHtml):
    """REmove the BOM marker except at the beginning of the string"""

    # Check if it is in the beginning
    bStartsWithBom = sHtml.startswith(u'\ufeff')
    # Remove everywhere
    sHtml = sHtml.replace(u'\ufeff', '')
    # Return what we have
    return sHtml

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

def add_visit(request, name, is_menu):
    """Add the visit to the current path"""

    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous":
        Visit.add(username, name, request.path, is_menu)

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

def has_string_value(field, obj):
    response = (field in obj and obj[field] != None and obj[field] != "")
    return response

def has_list_value(field, obj):
    response = (field in obj and obj[field] != None and len(obj[field]) > 0)
    return response

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
    context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')
    context['is_lenten_editor'] = user_is_ingroup(request, 'lenten_editor')

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "Home", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}]

    # Create the list of news-items
    lstQ = []
    lstQ.append(Q(status='val'))
    newsitem_list = NewsItem.objects.filter(*lstQ).order_by('-saved', '-created')
    context['newsitem_list'] = newsitem_list

    # Render and return the page
    return render(request, template_name, context)

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'Contact',
                'message':'Pietro Delcorno',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "Contact", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}, {'name': 'Contact', 'url': reverse('contact')}]


    return render(request,'contact.html', context)

def more(request):
    """Renders the more page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'More',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "More", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}, {'name': 'More', 'url': reverse('more')}]


    return render(request,'more.html', context)

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'About',
                'message':'Radboud University passim utility.',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')

    # Process this visit
    # context['breadcrumbs'] = process_visit(request, "About", True)
    context['breadcrumbs'] = [{'name': 'Home', 'url': reverse('home')}, {'name': 'About', 'url': reverse('about')}]

    return render(request,'about.html', context)

def short(request):
    """Renders the page with the short instructions."""

    assert isinstance(request, HttpRequest)
    template = 'short.html'
    context = {'title': 'Short overview',
               'message': 'Radboud University passim short intro',
               'year': get_current_datetime().year}
    context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')
    return render(request, template, context)

def nlogin(request):
    """Renders the not-logged-in page."""
    assert isinstance(request, HttpRequest)
    context =  {    'title':'Not logged in', 
                    'message':'Radboud University passim utility.',
                    'year':get_current_datetime().year,}
    context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')
    return render(request,'nlogin.html', context)

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

def signup(request):
    """Provide basic sign up and validation of it """

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
                if sTclass == "communicative":
                    clsThis = TagCommunicative
                elif sTclass == "liturgical":
                    clsThis = TagLiturgical
                elif sTclass == "notes":
                    clsThis = TagNote
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

@csrf_exempt
def get_keywords(request):
    """Get a list of keywords for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            # Get the complete code line, which could use semicolon-separation
            kwline = request.GET.get("name", "")
            kwlist = kwline.split(";")
            kw = "" if len(kwlist) == 0 else kwlist[-1].strip()
            lstQ = []
            lstQ.append(Q(name__icontains=kw))
            items = Keyword.objects.filter(*lstQ).order_by("name").distinct()
            results = []
            for co in items:
                co_json = {'name': co.name, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
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
            context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')
            context['is_lenten_editor'] = user_is_ingroup(request, 'lenten_editor')
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
            context['is_lenten_uploader'] = user_is_ingroup(request, 'lenten_uploader')
            context['is_lenten_editor'] = user_is_ingroup(request, 'lenten_editor')
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
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')
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
        context['title'] = "Lentensermons location info"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')

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
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')
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


class SermonListView(ListView):
    """Listview of sermons"""

    model = Sermon
    paginate_by = 15
    template_name = 'seeker/sermon_list.html'
    entrycount = 0

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SermonListView, self).get_context_data(**kwargs)

        # Get parameters
        initial = self.request.GET

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Get parameters for the search
        initial = self.request.GET
        # The searchform is just a list form, but filled with the 'initial' parameters
        # context['searchform'] = LocationForm(initial)

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the title of the application
        context['title'] = "Sermons"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')

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

        # Check for liturgical day
        if 'litday' in get and get['litday'] != '':
            val = adapt_search(get['litday'])
            # Search in both the name field
            lstQ.append(Q(litday__iregex=val))

        # Check for the code of the sermon
        if 'code' in get and get['code'] != '':
            val = get['code']
            # Search in both the name field
            lstQ.append(Q(code=val))

        # Calculate the final qs
        qs = Sermon.objects.filter(*lstQ).order_by('code').distinct()

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs
    

class SermonCollectionListView(ListView):
    """Listview of sermon collections"""

    model = SermonCollection
    paginate_by = 15
    template_name = 'seeker/collection_list.html'
    entrycount = 0

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SermonCollectionListView, self).get_context_data(**kwargs)

        # Get parameters
        initial = self.request.GET

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Get parameters for the search
        initial = self.request.GET
        # The searchform is just a list form, but filled with the 'initial' parameters
        # context['searchform'] = LocationForm(initial)

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the title of the application
        context['title'] = "SermonCollections"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')

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

        # Check for liturgical day
        if 'title' in get and get['title'] != '':
            val = adapt_search(get['title'])
            # Search in both the name field
            lstQ.append(Q(title__iregex=val))

        # Check for the code of the sermon
        if 'idno' in get and get['idno'] != '':
            val = get['idno']
            # Search in both the name field
            lstQ.append(Q(idno=val))

        # Calculate the final qs
        qs = SermonCollection.objects.filter(*lstQ).order_by('title').distinct()

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs
    

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
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')

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
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')
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
        context['mainitems'] = [
            {'type': 'bold',  'label': "Collection:", 'value': instance.collection.title},
            {'type': 'plain', 'label': "Code:", 'value': instance.code},
            {'type': 'plain', 'label': "Liturgical day:", 'value': instance.litday},
            {'type': 'safe',  'label': "Thema:", 'value': instance.thema.strip()},
            {'type': 'plain', 'label': "Passage:", 'value': instance.get_bibref() },
            {'type': 'safeline',    'label': "Division (Latin):", 'value': instance.divisionL.strip()},
            {'type': 'safeline',    'label': "Division (English):", 'value': instance.divisionE.strip()},
            {'type': 'line',        'label': "Summary:", 'value': instance.summary.strip()},
            {'type': 'safeline',    'label': "Note:", 'value': instance.get_note_display.strip()},
            ]

        # Add link objects: link to the SermonCollection I am part of
        link_objects = []
        sc = reverse('collection_details', kwargs={'pk': instance.collection.id})
        link = dict(name="Sermon collection for this sermon", label="{}".format(instance.collection.title), value=sc )
        link_objects.append(link)
        context['link_objects'] = link_objects

        return context


class CollectionDetailsView(PassimDetails):
    model = SermonCollection
    mForm = None
    template_name = 'generic_details.html' 
    prefix = ""
    title = "CollectionDetails"
    rtype = "html"
    mainitems = []

    def add_to_context(self, context, instance):
        # Show the main items of this sermon collection
        context['mainitems'] = [
            {'type': 'plain', 'label': "Code:", 'value': instance.idno},
            {'type': 'bold',  'label': "Title:", 'value': instance.title},
            {'type': 'plain', 'label': "Authors:", 'value': instance.get_authors()},
            {'type': 'plain', 'label': "Date of composition:", 'value': "{} ({})".format(instance.datecomp, instance.get_datetype_display()) },
            {'type': 'plain', 'label': "Place:", 'value': instance.place.name },
            {'type': 'plain', 'label': "Structure:", 'value': instance.structure },
            {'type': 'safeline',    'label': "Liturgical relation:", 'value': instance.get_liturgical_display.strip(), 'title': "Relationship with liturgical texts"},
            {'type': 'safeline',    'label': "Communicative strategy:", 'value': instance.get_communicative_display.strip()},
            {'type': 'safeline',    'label': "Quoted sources:", 'value': instance.get_sources_display.strip()},
            {'type': 'safeline',    'label': "Exempla:", 'value': instance.get_exempla_display.strip()},
            {'type': 'safeline',    'label': "Notes:", 'value': instance.get_notes_display.strip()},
            ]

        related_objects = []

        # Show the SERMONS of this collection
        sermons = {'title': 'Sermons that are part of this collection'}
        # Show the list of sermons that are part of this collection
        qs = Sermon.objects.filter(collection=instance).order_by('code')
        rel_list =[]
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.code, 'title': 'View this sermon', 'link': reverse('sermon_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.litday})
            rel_item.append({'value': item.get_bibref()})
            rel_list.append(rel_item)
        sermons['rel_list'] = rel_list
        sermons['columns'] = ['Code', 'Liturgical day', 'Reference']
        related_objects.append(sermons)

        # Show the MANUSCRIPTS that point to this collection
        manuscripts = {'title': 'Manuscripts that contain this collection'}
        # Get the list of manuscripts
        qs = Manuscript.objects.filter(collection=instance).order_by('info')
        rel_list = []
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.info, 'title': 'View this manuscript', 'link': reverse('manuscript_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.link})
            rel_list.append(rel_item)
        manuscripts['rel_list'] = rel_list
        manuscripts['columns'] = ['Information', 'Link']
        related_objects.append(manuscripts)

        # Show the EDITIONS that point to this collection
        editions = {'title': 'Editions that contain this collection'}
        # Get the list of editions
        qs = Edition.objects.filter(sermoncollection=instance).order_by('code')
        rel_list = []
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.code, 'title': 'View this edition', 'link': reverse('edition_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.get_date()})
            rel_item.append({'value': item.get_place()})
            rel_list.append(rel_item)
        editions['rel_list'] = rel_list
        editions['columns'] = ['Code', 'Date', 'Place']
        related_objects.append(editions)

        context['related_objects'] = related_objects
        # Return the context we have made
        return context


class EditionListView(ListView):
    """Listview of sermons"""

    model = Edition
    paginate_by = 15
    template_name = 'seeker/edition_list.html'
    entrycount = 0

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(EditionListView, self).get_context_data(**kwargs)

        # Get parameters
        initial = self.request.GET

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Get parameters for the search
        initial = self.request.GET
        # The searchform is just a list form, but filled with the 'initial' parameters
        # context['searchform'] = LocationForm(initial)

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the title of the application
        context['title'] = "Editions"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')

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

        # Check for liturgical day
        if 'place' in get and get['place'] != '':
            val = adapt_search(get['place'])
            # Search in the name field of the place location
            lstQ.append(Q(place__name__iregex=val))

        # Check for the code of the sermon
        if 'code' in get and get['code'] != '':
            val = get['code']
            # Search in both the name field
            lstQ.append(Q(code=val))

        # Calculate the final qs
        qs = Edition.objects.filter(*lstQ).order_by('code').distinct()

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs
    

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
        if instance.place:
            sLocation = instance.place.name
        context['mainitems'] = [
            {'type': 'bold',  'label': "Year of publication (earliest):", 'value': instance.date},
            {'type': 'plain', 'label': "Year of publication (latest):", 'value': instance.date_late},
            {'type': 'plain', 'label': "Date type:", 'value': instance.get_datetype_display()},
            {'type': 'plain', 'label': "Comment on the date:", 'value': instance.datecomment},
            {'type': 'plain', 'label': "Place:", 'value': sLocation},
            {'type': 'plain', 'label': "Passage:", 'value': instance.get_format_display() },
            {'type': 'plain', 'label': "Folia:", 'value': instance.folia},
            # MORE INFORMATION SHOULD FOLLOW
            ]

        # Add link objects: link to the SermonCollection I am part of
        link_objects = []
        sc = reverse('collection_details', kwargs={'pk': instance.sermoncollection.id})
        link = dict(name="Sermon collection for this edition", label="{}".format(instance.sermoncollection.title), value=sc )
        link_objects.append(link)
        context['link_objects'] = link_objects

        return context


class AuthorListView(ListView):
    """Listview of authors"""

    model = Author
    paginate_by = 15
    template_name = 'seeker/author_list.html'
    entrycount = 0

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(AuthorListView, self).get_context_data(**kwargs)

        # Get parameters
        initial = self.request.GET

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Get parameters for the search
        initial = self.request.GET
        # The searchform is just a list form, but filled with the 'initial' parameters
        # context['searchform'] = LocationForm(initial)

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the title of the application
        context['title'] = "Authors"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')

        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, "Authors", True)
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

        # Check for author name
        if 'name' in get and get['name'] != '':
            val = adapt_search(get['name'])
            # Search in the name field
            lstQ.append(Q(name__iregex=val))

        # Calculate the final qs
        qs = Author.objects.filter(*lstQ).order_by('name').distinct()

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs
    

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
            {'type': 'plain',  'label': "Name:", 'value': instance.name},
            {'type': 'plain', 'label': "Information:", 'value': instance.info}
            ]
        related_objects = []

        # Show the collections containing this author
        collections = {'title': 'Sermon collections that have this author'}
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
        collections['columns'] = ['Idno', 'Title', 'Date', 'Place']
        related_objects.append(collections)

        context['related_objects'] = related_objects
        # Return the context we have made
        return context


class ManuscriptListView(ListView):
    """Listview of manuscripts"""

    model = Manuscript
    paginate_by = 15
    template_name = 'seeker/manuscript_list.html'
    entrycount = 0

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ManuscriptListView, self).get_context_data(**kwargs)

        # Get parameters
        initial = self.request.GET

        # Determine the count 
        context['entrycount'] = self.entrycount # self.get_queryset().count()

        # Set the prefix
        context['app_prefix'] = APP_PREFIX

        # Get parameters for the search
        initial = self.request.GET
        # The searchform is just a list form, but filled with the 'initial' parameters
        # context['searchform'] = LocationForm(initial)

        # Make sure the paginate-values are available
        context['paginateValues'] = paginateValues

        if 'paginate_by' in initial:
            context['paginateSize'] = int(initial['paginate_by'])
        else:
            context['paginateSize'] = paginateSize

        # Set the title of the application
        context['title'] = "Manuscripts"

        # Check if user may upload
        context['is_authenticated'] = user_is_authenticated(self.request)
        context['is_lenten_uploader'] = user_is_ingroup(self.request, 'lenten_uploader')
        context['is_lenten_editor'] = user_is_ingroup(self.request, 'lenten_editor')

        # Process this visit and get the new breadcrumbs object
        context['breadcrumbs'] = process_visit(self.request, "Manuscripts", True)
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

        # Check for manuscript information
        if 'info' in get and get['info'] != '':
            val = adapt_search(get['info'])
            # Search in the info field
            lstQ.append(Q(info__iregex=val))

        # Check for the link in the manuscript
        if 'link' in get and get['link'] != '':
            val = adapt_search(get['link'])
            # Search in the link field
            lstQ.append(Q(link__iregex=val))

        # Calculate the final qs
        qs = Manuscript.objects.filter(*lstQ).order_by('collection__idno').distinct()

        # Determine the length
        self.entrycount = len(qs)

        # Return the resulting filtered and sorted queryset
        return qs
    

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
            {'type': 'plain',  'label': "Information:", 'value': instance.info},
            {'type': 'plain', 'label': "Link (if available):", 'value': instance.link}
            ]
        related_objects = []

        # Show the SERMONS of this manuscript
        sermons = {'title': 'Sermons that are part of this manuscript'}
        # Show the list of sermons that are part of this manuscript
        qs = Sermon.objects.filter(collection=instance.collection).order_by('code')
        rel_list =[]
        for item in qs:
            rel_item = []
            rel_item.append({'value': item.code, 'title': 'View this sermon', 'link': reverse('sermon_details', kwargs={'pk': item.id})})
            rel_item.append({'value': item.litday})
            rel_item.append({'value': item.get_bibref()})
            rel_list.append(rel_item)
        sermons['rel_list'] = rel_list
        sermons['columns'] = ['Code', 'Liturgical day', 'Reference']
        related_objects.append(sermons)

        context['related_objects'] = related_objects
        # Return the context we have made
        return context


