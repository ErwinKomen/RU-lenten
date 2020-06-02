"""Models for the SEEKER app.

"""
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.html import mark_safe
from django.utils import timezone
from django.forms.models import model_to_dict
from django.template.loader import render_to_string
import pytz
from django.urls import reverse
from datetime import datetime
from markdown import markdown
from lentensermons.utils import *
from lentensermons.settings import APP_PREFIX, WRITABLE_DIR
from lentensermons import tagtext
import sys, os, io, re
import copy
import json
import time
import fnmatch
import csv
import math
from io import StringIO

STANDARD_LENGTH=100
LONG_STRING=255
MEDIUM_LENGTH = 200

VIEW_STATUS = "view.status"     # For news items
REPORT_TYPE = "seeker.reptype"
LINK_TYPE = "seeker.linktype"
EDI_TYPE = "seeker.editype"
STATUS_TYPE = "seeker.stype"
DATE_TYPE = "seeker.datetype"
FORMAT_TYPE = "seeker.formattype"
LANGUAGE_tYPE = "seeker.language"


class FieldChoice(models.Model):

    field = models.CharField(max_length=50)
    english_name = models.CharField(max_length=100)
    dutch_name = models.CharField(max_length=100)
    abbr = models.CharField(max_length=20, default='-')
    machine_value = models.IntegerField(help_text="The actual numeric value stored in the database. Created automatically.")

    def __str__(self):
        return "{}: {}, {} ({})".format(
            self.field, self.english_name, self.dutch_name, str(self.machine_value))

    class Meta:
        ordering = ['field','machine_value']


class HelpChoice(models.Model):
    """Define the URL to link to for the help-text"""
    
    field = models.CharField(max_length=200)        # The 'path' to and including the actual field
    searchable = models.BooleanField(default=False) # Whether this field is searchable or not
    display_name = models.CharField(max_length=50)  # Name between the <a></a> tags
    help_url = models.URLField(default='')          # THe actual help url (if any)

    def __str__(self):
        return "[{}]: {}".format(
            self.field, self.display_name)

    def Text(self):
        help_text = ''
        # is anything available??
        if (self.help_url != ''):
            if self.help_url[:4] == 'http':
                help_text = "See: <a href='{}'>{}</a>".format(
                    self.help_url, self.display_name)
            else:
                help_text = "{} ({})".format(
                    self.display_name, self.help_url)
        return help_text

def get_current_datetime():
    return timezone.now()

def adapt_search(val):
    if val == None: return None
    # First trim
    val = val.strip()
    val = '^' + fnmatch.translate(val) + '$'
    return val

def adapt_latin(val):
    """Change the three dots into a unicode character"""

    val = val.replace('...', u'\u2026')
    return val

def adapt_markdown(val, lowercase=True):
    sBack = ""
    if val != None:
        val = val.replace("***", "\*\*\*")
        sBack = mark_safe(markdown(val, safe_mode='escape'))
        sBack = sBack.replace("<p>", "")
        sBack = sBack.replace("</p>", "")
        if lowercase:
            sBack = sBack.lower()
    return sBack

def is_number(s_input):
    return re.match(r'^[[]?(\d+)[]]?', s_input)

def get_linktype_abbr(sLinkType):
    """Convert a linktype into a valid abbreviation"""

    options = [{'abbr': LINK_EQUAL, 'input': 'equals' },
               {'abbr': 'prt', 'input': 'partially equals' },
               {'abbr': 'prt', 'input': 'partialy equals' },
               {'abbr': 'sim', 'input': 'similar_to' },
               {'abbr': 'sim', 'input': 'similar' },
               {'abbr': 'sim', 'input': 'similar to' },
               {'abbr': 'neq', 'input': 'nearly equals' },
               {'abbr': 'use', 'input': 'uses' },
               {'abbr': 'use', 'input': 'makes_use_of' },
               ]
    for opt in options:
        if sLinkType == opt['abbr']:
            return sLinkType
        elif sLinkType == opt['input']:
            return opt['abbr']
    # Return default
    return LINK_EQUAL

def get_help(field):
    """Create the 'help_text' for this element"""

    # find the correct instance in the database
    help_text = ""
    try:
        entry_list = HelpChoice.objects.filter(field__iexact=field)
        entry = entry_list[0]
        # Note: only take the first actual instance!!
        help_text = entry.Text()
    except:
        help_text = "Sorry, no help available for " + field

    return help_text

def get_crpp_date(dtThis):
    """Convert datetime to string"""

    # Model: yyyy-MM-dd'T'HH:mm:ss
    sDate = dtThis.strftime("%Y-%m-%dT%H:%M:%S")
    return sDate

def get_now_time():
    return time.clock()

def obj_text(d):
    stack = list(d.items())
    lBack = []
    while stack:
        k, v = stack.pop()
        if isinstance(v, dict):
            stack.extend(v.iteritems())
        else:
            # Note: the key is [k]
            lBack.append(v)
    return ", ".join(lBack)

def obj_value(d):
    def NestedDictValues(d):
        for k, v in d.items():
            # Treat attributes differently
            if k[:1] == "@":
                yield "{}={}".format(k,v)
            elif isinstance(v, dict):
                yield from NestedDictValues(v)
            else:
                yield v
    a = list(NestedDictValues(d))
    return ", ".join(a)

def getText(nodeStart):
    # Iterate all Nodes aggregate TEXT_NODE
    rc = []
    for node in nodeStart.childNodes:
        if node.nodeType == node.TEXT_NODE:
            sText = node.data.strip(' \t\n')
            if sText != "":
                rc.append(sText)
        else:
            # Recursive
            rc.append(getText(node))
    return ' '.join(rc)

def get_searchable(sText):
    sRemove = r"/\<|\>|\_|\,|\.|\:|\;|\?|\!|\(|\)|\[|\]/"

    # Move to lower case
    sText = sText.lower()

    # Remove punctuation with nothing
    sText = re.sub(sRemove, "", sText)

    # Make sure to TRIM the text
    sText = sText.strip()
    return sText

def build_choice_list(field, position=None, subcat=None, maybe_empty=False):
    """Create a list of choice-tuples"""

    choice_list = [];
    unique_list = [];   # Check for uniqueness

    try:
        # check if there are any options at all
        if FieldChoice.objects == None:
            # Take a default list
            choice_list = [('0','-'),('1','N/A')]
            unique_list = [('0','-'),('1','N/A')]
        else:
            if maybe_empty:
                choice_list = [('0','-')]
            for choice in FieldChoice.objects.filter(field__iexact=field):
                # Default
                sEngName = ""
                # Any special position??
                if position==None:
                    sEngName = choice.english_name
                elif position=='before':
                    # We only need to take into account anything before a ":" sign
                    sEngName = choice.english_name.split(':',1)[0]
                elif position=='after':
                    if subcat!=None:
                        arName = choice.english_name.partition(':')
                        if len(arName)>1 and arName[0]==subcat:
                            sEngName = arName[2]

                # Sanity check
                if sEngName != "" and not sEngName in unique_list:
                    # Add it to the REAL list
                    choice_list.append((str(choice.machine_value),sEngName));
                    # Add it to the list that checks for uniqueness
                    unique_list.append(sEngName)

            choice_list = sorted(choice_list,key=lambda x: x[1]);
    except:
        print("Unexpected error:", sys.exc_info()[0])
        choice_list = [('0','-'),('1','N/A')];

    # Signbank returns: [('0','-'),('1','N/A')] + choice_list
    # We do not use defaults
    return choice_list;

def build_abbr_list(field, position=None, subcat=None, maybe_empty=False):
    """Create a list of choice-tuples"""

    choice_list = [];
    unique_list = [];   # Check for uniqueness

    try:
        # check if there are any options at all
        if FieldChoice.objects == None:
            # Take a default list
            choice_list = [('0','-'),('1','N/A')]
            unique_list = [('0','-'),('1','N/A')]
        else:
            if maybe_empty:
                choice_list = [('0','-')]
            for choice in FieldChoice.objects.filter(field__iexact=field):
                # Default
                sEngName = ""
                # Any special position??
                if position==None:
                    sEngName = choice.english_name
                elif position=='before':
                    # We only need to take into account anything before a ":" sign
                    sEngName = choice.english_name.split(':',1)[0]
                elif position=='after':
                    if subcat!=None:
                        arName = choice.english_name.partition(':')
                        if len(arName)>1 and arName[0]==subcat:
                            sEngName = arName[2]

                # Sanity check
                if sEngName != "" and not sEngName in unique_list:
                    # Add it to the REAL list
                    choice_list.append((str(choice.abbr),sEngName));
                    # Add it to the list that checks for uniqueness
                    unique_list.append(sEngName)

            choice_list = sorted(choice_list,key=lambda x: x[1]);
    except:
        print("Unexpected error:", sys.exc_info()[0])
        choice_list = [('0','-'),('1','N/A')];

    # Signbank returns: [('0','-'),('1','N/A')] + choice_list
    # We do not use defaults
    return choice_list;

def choice_english(field, num):
    """Get the english name of the field with the indicated machine_number"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(machine_value=num)
        if (result_list == None):
            return "(No results for "+field+" with number="+num
        return result_list[0].english_name
    except:
        return "(empty)"

def choice_value(field, term):
    """Get the numerical value of the field with the indicated English name"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(english_name__iexact=term)
        if result_list == None or result_list.count() == 0:
            # Try looking at abbreviation
            result_list = FieldChoice.objects.filter(field__iexact=field).filter(abbr__iexact=term)
        if result_list == None:
            return -1
        else:
            return result_list[0].machine_value
    except:
        return -1

def choice_abbreviation(field, num):
    """Get the abbreviation of the field with the indicated machine_number"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(machine_value=num)
        if (result_list == None):
            return "{}_{}".format(field, num)
        return result_list[0].abbr
    except:
        return "-"

def import_data_file(sContents, arErr):
    """Turn the contents of [data_file] into a json object"""

    try:
        # Validate
        if sContents == "":
            return {}
        # Adapt the contents into an object array
        lines = []
        for line in sContents:
            lines.append(line.decode("utf-8").strip())
        # Combine again
        sContents = "\n".join(lines)
        oData = json.loads(sContents)
        # This is the data
        return oData
    except:
        sMsg = errHandle.get_error_message()
        arErr.DoError("import_data_file error:")
        return {}

def tag_combine_html(obj, sParts, sWhole):
    """a"""

    # Initialisations
    lHtml = []
    CUTOFF = 50
    method = "word-based"   # Or: "character-based"
    oErr = ErrHandle()

    def parts_to_string(parts, idxBeg, idxEnd, size, type):
        """COmbine parts from idxBeg until idxEnd into a string"""

        if idxBeg <0 or idxEnd == 0 or idxEnd < idxBeg:
            combi = ""
        else:
            lst_combi = []
            mysize = 0
            # Action depends on type
            if type == "from_end":
                idx = idxEnd
                while idx >=0:
                    contents = parts[idx]['value'].strip().replace('\n', ' ').replace('*', '')
                    lst_combi.insert(0,contents)
                    mysize += len(contents)
                    if mysize > size:
                        break
                    idx -= 1
            else:
                for part in parts[idxBeg:idxEnd]:
                    contents = part['value'].strip().replace('\n', ' ').replace('*', '')
                    lst_combi.append(contents)
                    mysize += len(contents)
                    if mysize > size:
                        break

            combi = " ".join(lst_combi)
        return combi

    try:
        # Get the id as a string
        obj_id = str(obj.id)
        # The whole
        lHtml.append('<div class="tag-combi tag-combi-whole tag-{} hidden"><button class="btn btn-xs jumbo-1" onclick="ru.lenten.seeker.toggle_tag(this);">Hide</button>{}</div>'.format(obj_id, sWhole))
        # Start the partial stuff
        lHtml.append('<div class="tag-combi tag-combi-part tag-{}" >'.format(obj_id))
        parts = json.loads(sParts)
        lFound = []
        for idx, item in enumerate(parts):
            # Check if this is a focus item
            if item['type'] == 'tag' and item['tagid'] == obj_id:
                if method == "word-based":
                    # Get preceding and following parts
                    prev_item = parts_to_string(parts, 0, idx, CUTOFF, "from_end")
                    next_item = parts_to_string(parts, idx+1, len(parts), CUTOFF, "from_start")
                elif method == "character-based":
                    # Just get the single one preceding and following part
                    prev_item = "" if idx == 0 else parts[idx-1]
                    next_item = "" if idx+1 >= len(parts) else parts[idx+1]
                    # And then cut it off to 50 chars before and after
                    if len(prev_item) > 0: prev_item = prev_item['value'].strip().replace('\n', ' ').replace('*', '')[-50:]
                    if len(next_item) > 0: next_item = next_item['value'].strip().replace('\n', ' ').replace('*', '')[:50]
                # Get the focus item
                this_item = item['value']
                # Add the line to the table that shows the results
                lFound.append("<tr class='clickable' onclick='ru.lenten.seeker.toggle_tag(this);'>")
                lFound.append("<td align='right'>...{}</td><td align='center'><b>{}</b></td><td>{}...</td></tr>".format(
                    prev_item, this_item, next_item ))
        if len(lFound) > 0:
            lHtml.append("<table class='no-border-table'>{}</table>".format("\n".join(lFound)))
        # Finish this off
        lHtml.append("</div>")
    except:
        msg = oErr.get_error_message()
        oErr.DoError("tag_combine_html")
        lHtml = [ "error", msg ]
    return "\n".join(lHtml)



# ============= GENERAL CLASSES =================================================================

class Status(models.Model):
    """Intermediate loading of sync information and status of processing it"""

    # [1] Status of the process
    status = models.CharField("Status of synchronization", max_length=50)
    # [1] Counts (as stringified JSON object)
    count = models.TextField("Count details", default="{}")
    # [0-1] Synchronisation type
    type = models.CharField("Type", max_length=255, default="")
    # [0-1] User
    user = models.CharField("User", max_length=255, default="")
    # [0-1] Error message (if any)
    msg = models.TextField("Error message", blank=True, null=True)

    class Meta:
        verbose_name_plural = "Statuses"

    def __str__(self):
        # Refresh the DB connection
        self.refresh_from_db()
        # Only now provide the status
        return self.status

    def set(self, sStatus, oCount = None, msg = None):
        self.status = sStatus
        if oCount != None:
            self.count = json.dumps(oCount)
        if msg != None:
            self.msg = msg
        self.save()


class Action(models.Model):
    """Track actions made by users"""

    # [1] The user
    user = models.ForeignKey(User)
    # [1] The item (e.g: Manuscript, SermonDescr, SermonGold)
    itemtype = models.CharField("Item type", max_length=MEDIUM_LENGTH)
    # [1] The kind of action performed (e.g: create, edit, delete)
    actiontype = models.CharField("Action type", max_length=MEDIUM_LENGTH)
    # [0-1] Room for possible action-specific details
    details = models.TextField("Detail", blank=True, null=True)
    # [1] Date and time of this action
    when = models.DateTimeField(default=get_current_datetime)

    def __str__(self):
        action = "{}|{}".format(self.user.username, self.when)
        return action

    def add(user, itemtype, actiontype, details=None):
        """Add an action"""

        # Check if we are getting a string user name or not
        if isinstance(user, str):
            # Get the user object
            oUser = User.objects.filter(username=user).first()
        else:
            oUser = user
        # If there are details, make sure they are stringified
        if details != None and not isinstance(details, str):
            details = json.dumps(details)
        # Create the correct action
        action = Action(user=oUser, itemtype=itemtype, actiontype=actiontype)
        if details != None: action.details = details
        action.save()
        return action


class Report(models.Model):
    """Report of an upload action or something like that"""

    # [1] Every report must be connected to a user and a date (when a user is deleted, the Report is deleted too)
    user = models.ForeignKey(User)
    # [1] And a date: the date of saving this report
    created = models.DateTimeField(default=get_current_datetime)
    # [1] A report should have a type to know what we are reporting about
    reptype = models.CharField("Report type", choices=build_abbr_list(REPORT_TYPE), 
                            max_length=5)
    # [0-1] A report should have some contents: stringified JSON
    contents = models.TextField("Contents", default="{}")

    def __str__(self):
        sType = self.reptype
        sDate = get_crpp_date(self.created)
        return "{}: {}".format(sType, sDate)

    def make(username, rtype, contents):
        """Create a report"""

        # Retrieve the user
        user = User.objects.filter(username=username).first()
        obj = Report(user=user, reptype=rtype, contents=contents)
        obj.save()
        # Add a create action
        details = {'reptype': rtype, 'id': obj.id}
        Action.add(user, "Report", "create", json.dumps(details))
        # Return the object
        return obj


class Information(models.Model):
    """Specific information that needs to be kept in the database"""

    # [1] The key under which this piece of information resides
    name = models.CharField("Key name", max_length=255)
    # [0-1] The value for this piece of information
    kvalue = models.TextField("Key value", default = "", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Information Items"

    def __str__(self):
        return "-" if self == None else self.name

    def get_kvalue(name):
        info = Information.objects.filter(name=name).first()
        if info == None:
            return ''
        else:
            return info.kvalue

    def set_kvalue(name, value):
        info = Information.objects.filter(name=name).first()
        if info == None:
            info = Information(name=name)
            info.save()
        info.kvalue = value
        info.save()
        return True

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        return super(Information, self).save(force_insert, force_update, using, update_fields)


class Profile(models.Model):
    """Information about the user"""

    # [1] Every profile is linked to a user
    user = models.ForeignKey(User)
    # [1] Every user has a stack: a list of visit objects
    stack = models.TextField("Stack", default = "[]")

    ## [1] Current size of the user's basket
    #basketsize = models.IntegerField("Basket size", default=0)
    ## Many-to-many field for the contents of a search basket per user
    #basketitems = models.ManyToManyField("SermonDescr", through="Basket", related_name="basketitems_user")

    def __str__(self):
        sStack = self.stack
        return sStack

    def add_visit(self, name, path, is_menu, **kwargs):
        """Process one visit in an adaptation of the stack"""

        oErr = ErrHandle()
        bNeedSaving = False
        try:
            # Check if this is a menu choice
            if is_menu:
                # Rebuild the stack
                path_home = reverse("home")
                oStack = []
                oStack.append({'name': "Home", 'url': path_home })
                if path != path_home:
                    oStack.append({'name': name, 'url': path })
                self.stack = json.dumps(oStack)
                bNeedSaving = True
            else:
                # Unpack the current stack
                lst_stack = json.loads(self.stack)
                # Check if this path is already on the stack
                bNew = True
                for idx, item in enumerate(lst_stack):
                    # Check if this item is on it already
                    if item['url'] == path:
                        # The url is on the stack, so cut off the stack from here
                        lst_stack = lst_stack[0:idx+1]
                        # But make sure to add any kwargs
                        if kwargs != None:
                            item['kwargs'] = kwargs
                        bNew = False
                        break
                    elif item['name'] == name:
                        # Replace the url
                        item['url'] = path
                        # But make sure to add any kwargs
                        if kwargs != None:
                            item['kwargs'] = kwargs
                        bNew = False
                        break
                if bNew:
                    # Add item to the stack
                    lst_stack.append({'name': name, 'url': path })
                # Add changes
                self.stack = json.dumps(lst_stack)
                bNeedSaving = True
            # All should have been done by now...
            if bNeedSaving:
                self.save()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("profile/add_visit")

    def get_stack(username):
        """Get the stack as a list from the current user"""

        # Sanity check
        if username == "":
            # Rebuild the stack
            path_home = reverse("home")
            oStack = []
            oStack.append({'name': "Home", 'url': path_home })
            return oStack
        # Get the user
        user = User.objects.filter(username=username).first()
        # Get to the profile of this user
        profile = Profile.objects.filter(user=user).first()
        if profile == None:
            # Return an empty list
            return []
        else:
            # Return the stack as object (list)
            return json.loads(profile.stack)

    def get_user_profile(username):
        # Sanity check
        if username == "":
            # Rebuild the stack
            return None
        # Get the user
        user = User.objects.filter(username=username).first()
        # Get to the profile of this user
        profile = Profile.objects.filter(user=user).first()
        return profile


class Visit(models.Model):
    """One visit to part of the application"""

    # [1] Every visit is made by a user
    user = models.ForeignKey(User)
    # [1] Every visit is done at a certain moment
    when = models.DateTimeField(default=get_current_datetime)
    # [1] Every visit is to a 'named' point
    name = models.CharField("Name", max_length=STANDARD_LENGTH)
    # [1] Every visit needs to have a URL
    path = models.URLField("URL")

    def __str__(self):
        msg = "{} ({})".format(self.name, self.path)
        return msg

    def add(username, name, path, is_menu = False, **kwargs):
        """Add a visit from user [username]"""

        oErr = ErrHandle()
        try:
            # Sanity check
            if username == "": return True
            # Get the user
            user = User.objects.filter(username=username).first()
            # Adapt the path if there are kwargs
            # Add an item
            obj = Visit(user=user, name=name, path=path)
            obj.save()
            # Get to the stack of this user
            profile = Profile.objects.filter(user=user).first()
            if profile == None:
                # There is no profile yet, so make it
                profile = Profile(user=user)
                profile.save()

            # Process this visit in the profile
            profile.add_visit(name, path, is_menu, **kwargs)
            # Return success
            result = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("visit/add")
            result = False
        # Return the result
        return result


class NewsItem(models.Model):
    """A news-item that can be displayed for a limited time"""

    # [1] title of this news-item
    title = models.CharField("Title",  max_length=MEDIUM_LENGTH)
    # [1] the date when this item was created
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)
    # [0-1] optional time after which this should not be shown anymore
    until = models.DateTimeField("Remove at", null=True, blank=True)
    # [1] the message that needs to be shown (in html)
    msg = models.TextField("Message")
    # [1] the status of this message (can e.g. be 'archived')
    status = models.CharField("Status", choices=build_abbr_list(VIEW_STATUS), 
                              max_length=5, help_text=get_help(VIEW_STATUS))

    def __str__(self):
        # A news item is the tile and the created
        sDate = get_crpp_date(self.created)
        sItem = "{}-{}".format(self.title, sDate)
        return sItem

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
      # Adapt the save date
      self.saved = get_current_datetime()
      response = super(NewsItem, self).save(force_insert, force_update, using, update_fields)
      return response

    def check_until():
        """Check all news items for the until date and emend status where needed"""

        # Get current time
        now = timezone.now()
        for obj in NewsItem.objects.all():
            if obj.until and obj.until < now:
                # This should be set invalid
                obj.status = "ext"
                obj.save()
        # Return valid
        return True


# ============================= APPLICATION-SPECIFIC CLASSES =====================================

# ============================= LOCATION related CLASSES =========================================

class LocationType(models.Model):
    """Kind of location and level on the location hierarchy"""

    # [1] obligatory name
    name = models.CharField("Name", max_length=STANDARD_LENGTH)
    # [1] obligatory level of this location on the scale
    level = models.IntegerField("Hierarchy level", default=0)

    def __str__(self):
        return "-" if self == None else self.name

    def find(sname):
        obj = LocationType.objects.filter(name__icontains=sname).first()
        return obj


class Location(models.Model):
    """One location element can be a city, village, cloister, region"""

    # [1] obligatory name in ENGLISH
    name = models.CharField("Name (eng)", max_length=STANDARD_LENGTH)
    # [1] Link to the location type of this location
    loctype = models.ForeignKey(LocationType)

    # Many-to-many field that identifies relations between locations
    relations = models.ManyToManyField("self", through="LocationRelation", symmetrical=False, related_name="relations_location", blank=True)

    def __str__(self):
        return "-" if self == None else  self.name

    def get_loc_name(self):
        lname = "{} ({})".format(self.name, self.loctype)
        return lname

    def get_location(city="", country=""):
        """Get the correct location object, based on the city and/or the country"""

        obj = None
        lstQ = []
        qs_country = None
        if country != "" and country != None:
            # Specify the country
            lstQ.append(Q(loctype__name="country"))
            lstQ.append(Q(name__iexact=country))
            qs_country = Location.objects.filter(*lstQ)
            if city == "" or city == None:
                obj = qs_country.first()
            else:
                lstQ = []
                lstQ.append(Q(loctype__name="city"))
                lstQ.append(Q(name__iexact=city))
                lstQ.append(relations_location__in=qs_country)
                obj = Location.objects.filter(*lstQ).first()
        elif city != "" and city != None:
            lstQ.append(Q(loctype__name="city"))
            lstQ.append(Q(name__iexact=city))
            obj = Location.objects.filter(*lstQ).first()
        return obj

    def partof(self):
        """give a list of locations (and their type) of which I am part"""

        lst_main = []
        lst_back = []

        def get_above(loc, lst_this):
            """Perform depth-first recursive procedure above"""

            above_lst = LocationRelation.objects.filter(contained=loc)
            for item in above_lst:
                # Add this item
                lst_this.append(item.container)
                # Add those above this item
                get_above(item.container, lst_this)

        # Calculate the aboves
        get_above(self, lst_main)

        # Walk the main list
        for item in lst_main:
            lst_back.append("{} ({})".format(item.name, item.loctype.name))

        # Return the list of locations
        return " | ".join(lst_back)

    def hierarchy(self, include_self=True):
        """give a list of locations (and their type) of which I am part"""

        lst_main = []
        if include_self:
            lst_main.append(self)

        def get_above(loc, lst_this):
            """Perform depth-first recursive procedure above"""

            above_lst = LocationRelation.objects.filter(contained=loc)
            for item in above_lst:
                # Add this item
                lst_this.append(item.container)
                # Add those above this item
                get_above(item.container, lst_this)

        # Calculate the aboves
        get_above(self, lst_main)

        # Return the list of locations
        return lst_main

    def above(self):
        return self.hierarchy(False)

    
class LocationName(models.Model):
    """The name of a location in a particular language"""

    # [1] obligatory name in vernacular
    name = models.CharField("Name", max_length=STANDARD_LENGTH)
    # [1] the language in which this name is given - ISO 3 letter code
    language = models.CharField("Language", max_length=STANDARD_LENGTH, default="eng")
    # [1] the Location to which this (vernacular) name belongs
    location = models.ForeignKey(Location, related_name="location_names")

    def __str__(self):
        return "{} ({})".format(self.name, self.language)


class LocationRelation(models.Model):
    """Container-contained relation between two locations"""

    # [1] Obligatory container
    container = models.ForeignKey(Location, related_name="container_locrelations")
    # [1] Obligatory contained
    contained = models.ForeignKey(Location, related_name="contained_locrelations")


# ============================= Different TAG related CLASSES =====================================

class Tgroup(models.Model):
    """Tags can be part of a group"""

    # [1] A group obligatorily has a name
    name = models.CharField("Name", max_length=LONG_STRING)

    class Meta:
        verbose_name = "Tag group"
        verbose_name_plural = "Tag groups"

    def __str__(self):
        return "-" if self == None else  self.name

    def get_url_edit(self):
        url = reverse('admin:seeker_tgroup_change', args=[self.id])
        return url

    def get_url_view(self):
        url = reverse('tgroup_details', kwargs={'pk': self.id})
        return url

    def get_default():
        """The default Tgroup must be [new]"""

        default_group = "New"   # Used to be 'general'

        obj = Tgroup.objects.filter(name=default_group).first()
        if obj == None:
            obj = Tgroup(name__iexact=default_group)
            obj.save()
        return obj


class TagLiturgical(models.Model):
    """The field 'liturgical' can have [0-n] tag words associated with it"""

    # [1] Any tag has a name
    name = models.CharField("Name", max_length=LONG_STRING)
    # [1] Each tag must be part of a group
    tgroup = models.ForeignKey(Tgroup, on_delete=models.CASCADE, related_name="tgroupslitu")

    class Meta:
        verbose_name_plural = "Liturgical Tags"

    def __str__(self):
        return "-" if self == None else  self.name

    def save(self, *args, **kwargs):
        if not self.pk and not self.tgroup_id:
            # Get the default tgroup
            tgroup = Tgroup.get_default()
            self.tgroup = tgroup
        super(TagLiturgical, self).save(*args, **kwargs)
        return None

    def get_list(self):
        """Get a list of type/count items"""

        lst_back = []
        # Communicative counts
        count = self.collection_liturtags.all().count()
        url = reverse("collection_list")
        params = "coll-taglituid={}".format(self.id)
        css ="jumbo-1"
        item = dict(count=count, type="Collection Liturgical tags", url=url, params=params, css=css)
        lst_back.append(item)

        return lst_back

    def get_url_edit(self):
        url = reverse('admin:seeker_tagliturgical_change', args=[self.id])
        return url

    def get_url_view(self):
        url = reverse('taglitu_details', kwargs={'pk': self.id})
        return url


class TagCommunicative(models.Model):
    """The field 'communicative' can have [0-n] tag words associated with it"""

    # [1] Any tag has a name
    name = models.CharField("Name", max_length=LONG_STRING)
    # [1] Each tag must be part of a group
    tgroup = models.ForeignKey(Tgroup, on_delete=models.CASCADE, related_name="tgroupscomm")

    class Meta:
        verbose_name_plural = "Communicative Tags"

    def __str__(self):
        return "-" if self == None else  self.name

    def save(self, *args, **kwargs):
        if not self.pk and not self.tgroup_id:
            # Get the default tgroup
            tgroup = Tgroup.get_default()
            self.tgroup = tgroup
        super(TagCommunicative, self).save(*args, **kwargs)
        return None

    def get_list(self):
        """Get a list of type/count items"""

        lst_back = []
        # Communicative counts
        count = self.collection_commtags.all().count()
        url = reverse("collection_list")
        params = "coll-tagcommid={}".format(self.id)
        css ="jumbo-1"
        item = dict(count=count, type="Collection Communicative tags", url=url, params=params, css=css)
        lst_back.append(item)

        return lst_back

    def get_url_edit(self):
        url = reverse('admin:seeker_tagcommunicative_change', args=[self.id])
        return url

    def get_url_view(self):
        url = reverse('tagcomm_details', kwargs={'pk': self.id})
        return url


class TagKeyword(models.Model):
    """The field 'notes' can have [0-n] tag words associated with it"""

    # [1] Any tag has a name
    name = models.CharField("Name", max_length=LONG_STRING)
    # [1] Each tag must be part of a group
    tgroup = models.ForeignKey(Tgroup, on_delete=models.CASCADE, related_name="tgroupskeyw")

    class Meta:
        verbose_name_plural = "Keyword Tags"

    def __str__(self):
        return "-" if self == None else self.name

    def save(self, *args, **kwargs):
        if not self.pk and not self.tgroup_id:
            # Get the default tgroup
            tgroup = Tgroup.get_default()
            self.tgroup = tgroup
        super(TagKeyword, self).save(*args, **kwargs)
        return None

    def get_list(self):
        """Get a list of type/count items"""

        lst_back = []

        # Counts in: collection.exempla
        count = self.collection_exempla.all().count()
        url = reverse("collection_list")
        params = "coll-tagexmpid={}".format(self.id)
        css ="jumbo-1"
        item = dict(count=count, type="Collection Example tags", url=url, params=params, css=css)
        lst_back.append(item)

        # Counts in: collection.sources
        count = self.collection_sourcenotes.all().count()
        url = reverse("collection_list")
        params = "coll-tagsrcid={}".format(self.id)
        css ="jumbo-2"
        item = dict(count=count, type="Collection Source tags", url=url, params=params, css=css)
        lst_back.append(item)

        # Counts in: collection.notes
        count = self.collection_notes.all().count()
        url = reverse("collection_list")
        params = "coll-tagnoteid={}".format(self.id)
        css ="jumbo-2"
        item = dict(count=count, type="Collection Notes tags", url=url, params=params, css=css)
        lst_back.append(item)

        # Counts in: sermon.summary
        count = self.sermon_summarynotes.all().count()
        url = reverse("sermon_list")
        params = "sermo-tagsummid={}".format(self.id)
        css ="jumbo-3"
        item = dict(count=count, type="Sermon Summary tags", url=url, params=params, css=css)
        lst_back.append(item)

        # Counts in: sermon.notes
        count = self.sermon_notetags.all().count()
        url = reverse("sermon_list")
        params = "sermo-tagnoteid={}".format(self.id)
        css ="jumbo-3"
        item = dict(count=count, type="Sermon Note tags", url=url, params=params, css=css)
        lst_back.append(item)

        # Counts in: edition.notes
        count = self.edition_notetags.all().count()
        url = reverse("edition_list")
        params = "edi-tagnoteid={}".format(self.id)
        css ="jumbo-4"
        item = dict(count=count, type="Edition Note tags", url=url, params=params, css=css)
        lst_back.append(item)

        # Counts in: author.notes
        count = self.author_infotags.all().count()
        url = reverse("author_list")
        params = "auth-tagnoteid={}".format(self.id)
        css ="jumbo-5"
        item = dict(count=count, type="Author Info tags", url=url, params=params, css=css)
        lst_back.append(item)

        # Counts in: manuscript.notes
        count = self.manuscript_infotags.all().count()
        url = reverse("manuscript_list")
        params = "manu-tagnoteid={}".format(self.id)
        css ="jumbo-6"
        item = dict(count=count, type="Manuscript Info tags", url=url, params=params, css=css)
        lst_back.append(item)

        return lst_back

    def get_url_edit(self):
        url = reverse('admin:seeker_tagkeyword_change', args=[self.id])
        return url

    def get_url_view(self):
        url = reverse('tagkeyword_details', kwargs={'pk': self.id})
        return url

    def find_or_create(sName):
        """Find or create [sName] and return its obj"""

        sName = sName.lower()
        obj = TagKeyword.objects.filter(name__iexact=sName).first()
        if obj == None:
            obj = TagKeyword.objects.create(name=sName)
        return obj



# ============================= Other CLASSES =====================================================

class Litref(models.Model):
    """One reference from literature"""

    # [0-1] The full reference, including possible markdown symbols
    full = models.TextField("Full reference", blank=False, null=False)
    # [0-1] A short reference: including possible markdown symbols
    short = models.TextField("Short reference", blank=True, default="")

    def __str__(self):
        return self.full

    def get_full_markdown(self):
        """Get the full text in markdown"""

        return adapt_markdown(self.full, lowercase=False)

    def get_short_markdown(self):
        """Get the short text in markdown"""

        return adapt_markdown(self.short, lowercase=False)


class Author(tagtext.models.TagtextModel):
    """We have a set of authors that are the 'golden' standard"""

    # [1] Name of the author
    name = models.CharField("Name", max_length=LONG_STRING)
    # [0-1] Information per author and bibliography
    info = models.TextField("Information", blank=True, null=True)

    # --------- MANY-TO-MANY connections ------------------
    # [0-n] = zero or more notetags in the 'info' field
    infotags = models.ManyToManyField(TagKeyword, blank=True, related_name="author_infotags")

    mixed_tag_fields = [
            {"textfield": "info", "m2mfield": "infotags",     "class": TagKeyword, "url": "tagkeyword_details"}
        ]

    def __str__(self):
        return "-" if self == None else  self.name

    def find_or_create(sName):
        """Find an author or create it."""

        qs = Author.objects.filter(Q(name__iexact=sName))
        if qs.count() == 0:
            # Create one
            hit = Author(name=sName)
            hit.save()
        else:
            hit = qs[0]
        # Return what we found or created
        return hit

    def find(sName):
        """Find an author."""

        # Check for the author's full name as well as the abbreviation
        hit = Author.objects.filter(Q(name__iexact=sName)).first()
        # Return what we found
        return hit

    def get_info_markdown(self):
        sBack = ""
        if self.info:
            sBack = markdown(self.get_info_display)
            sBack = sBack.strip()
        return sBack


class SermonCollection(tagtext.models.TagtextModel):

    # [0-1] Identification number assigned by the researcher
    # idno = models.CharField("Identification", max_length=MEDIUM_LENGTH, blank=True, null=True)
    idno = models.IntegerField("Identification", blank=True, null=True)
    # [1] Title is obligatory for any sermon collection
    title = models.CharField("Title", max_length=MEDIUM_LENGTH)
    # [0-1] Author information and bibliography
    bibliography = models.TextField("Info author and bibliography", blank=True, null=True)
    # [0-1] Date of composition
    datecomp = models.IntegerField("Year of composition", blank=True, null=True)
    # [0-1] Type of this date: fixed, approximate?
    datetype = models.CharField("Composition date type", choices=build_abbr_list(DATE_TYPE), 
                            max_length=5)
    # [0-1] Place of manuscript: may be city or country
    place = models.ForeignKey(Location, blank=True, null=True, on_delete=models.SET_NULL)

    # FOr sorting purposes: automatically add the FIRST author in a list of authors
    firstauthor = models.ForeignKey(Author, blank=True, null=True, on_delete=models.SET_NULL, related_name="collection_firstauthor")

    # Edition information: editions are linked to [SermonCollection]
    #   - first edition' information is derived by first_edition()
    #   - the number of editions is derived by edicount()

    # Typology / Structure 
    # [0-1] short structure description (one or two words)
    structure = models.CharField("Structure", max_length=MEDIUM_LENGTH, blank=True, null=True)
    # [0-1] Relationship with liturgical texts - use markdown '_' to identify repetative elements
    liturgical = models.TextField("Relationship with liturgical texts", blank=True, null=True)
    # [0-1] Communicative strategy - use markdown '_' to identify repetative elements
    communicative = models.TextField("Communicative strategy", blank=True, null=True)

    # General notes
    # [0-1] Particular sources quoted
    sources = models.TextField("Sources quoted", blank=True, null=True)
    # [0-1] Exempla
    exempla = models.TextField("Exempla", blank=True, null=True)
    # [0-1] Notes
    notes = models.TextField("Notes", blank=True, null=True)
    
    # ----------- calculated fields for sorting and filtering ----------
    firstedition = models.IntegerField("First edition date", default=0)
    numeditions = models.IntegerField("number of editions", default=0)
    nummanu = models.IntegerField("number of manuscripts", default=0)

    # --------- MANY-TO-MANY connections ------------------
    # [n-n] Author: each sermoncollection may have 1 or more authors
    authors = models.ManyToManyField(Author, blank=True, related_name="collection_authors")
    # [n-n] Liturgical tags
    liturtags = models.ManyToManyField(TagLiturgical, blank=True, related_name="collection_liturtags")
    # [n-n] Communicative tags
    commutags = models.ManyToManyField(TagCommunicative, blank=True, related_name="collection_commtags")
    # [n-n] Tags in the sources
    # sourcetags = models.ManyToManyField(TagQsource, blank=True, related_name="collection_sources")
    sourcenotetags = models.ManyToManyField(TagKeyword, blank=True, related_name="collection_sourcenotes")
    # [n-n] Tags in the exempla
    exemplatags = models.ManyToManyField(TagKeyword, blank=True, related_name="collection_exempla")
    # [n-n] Tags in the notes
    notetags = models.ManyToManyField(TagKeyword, blank=True, related_name="collection_notes")

    mixed_tag_fields = [
            {"textfield": "liturgical",     "m2mfield": "liturtags",        "class": TagLiturgical,   "url": "tagliturgical_details"},
            {"textfield": "communicative",  "m2mfield": "commutags",        "class": TagCommunicative,"url": "tagcommunicative_details"},
            {"textfield": "sources",        "m2mfield": "sourcenotetags",   "class": TagKeyword,      "url": "tagkeyword_details"},
            {"textfield": "exempla",        "m2mfield": "exemplatags",      "class": TagKeyword,      "url": "tagkeyword_details"},
            {"textfield": "notes",          "m2mfield": "notetags",         "class": TagKeyword,      "url": "tagkeyword_details"}
        ]

    def __str__(self):
        sBack = "{} {}".format(self.idno, self.title)
        return sBack

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        # CHeck who the 'firstauthor' is and adapt
        obj = self.authors.all().first()
        if self.firstauthor == None or (obj != None and self.firstauthor is not obj):
            self.firstauthor = obj
        response = super(SermonCollection, self).save(force_insert, force_update, using, update_fields)
        return None

    def tagtext_url(self):
        url = reverse('api_tributes')
        return url

    def first_edition_obj(self):
        """Find the first edition from those linked to me"""

        # Order the editions by ascending date and then take the first
        hit = self.editions.all().order("date").first()
        return hit

    def edicount(self):
        """Calculate the number of editions linked to me"""

        return self.editions.all().count()

    def authorlist(self):

        lst_author = [x.id for x in self.authors.all()]
        qs = Author.objects.filter(id__in=lst_author)
        return qs

    def authorbadges(self):
        """Get HTML code for a series of badges with author names"""

        lHtml = []
        qs = self.authors.all()
        for obj in qs:
            sBadge = "<span class='badge jumbo-1'>{}</span>".format(obj.name)
            lHtml.append(sBadge)

        return "\n".join(lHtml)

    def get_firstauthor(self):
        f = self.authors.all().first()
        sBack = "" if f == None else f.name
        return sBack

    def get_authors(self):
        auth_list = [x.name for x in self.authors.all()]
        return ", ".join(auth_list)

    def get_place(self):
        place = "-"
        if self.place != None:
            place = self.place.name
        return place

    def num_editions(self):
        count = self.editions.all().count()
        return count

    def first_edition(self):
        obj = self.editions.all().order_by('date', 'date_late').first()
        year = "-"
        if obj != None:
            year = obj.date
            if year == None:
                year = obj.date_late
        return year

    def get_firstedition(self):
        """Get the first edition and its author"""

        sBack = ""
        year = self.firstedition
        author = self.get_firstauthor()
        if author == "": author = "(unknown)"
        sBack = "{} {}".format(author, year)
        return sBack

    def adapt_editions(self):
        """This gets called when an edition changes"""

        bNeedSaving = False
        firstedition = self.first_edition()
        numeditions = self.num_editions()
        if firstedition != self.firstedition:
            self.firstedition = firstedition
            bNeedSaving = True
        if numeditions != self.numeditions:
            self.numeditions = numeditions
            bNeedSaving = True
        # Check if saving is needed
        if bNeedSaving:
            self.save()
        return True

    def adapt_manucount(self):
        """This gets called when manuscripts for a sermoncollection change"""

        bNeedSaving = False
        # Calculate the number of manuscripts
        nummanu = self.manuscripts.all().count()
        if nummanu != self.nummanu:
            self.nummanu = nummanu
            self.save()
        return True

    def do_manu_count():
        """Count manuscripts for all collections"""

        oErr = ErrHandle()
        try:
            with transaction.atomic():
                for obj in SermonCollection.objects.all():
                    obj.adapt_manucount()
                    obj.adapt_editions()
            return True
        except:
            msg = oErr.get_error_message()
            return False


class Manuscript(tagtext.models.TagtextModel):
    """Information on the manuscripts that belong to a sermon collection""" 

    # [1] Name of the manuscript
    name = models.TextField("Name", default="-")
    # [1] If there are manuscripts there must be information on them
    info = models.TextField("Info on manuscripts", blank=True, null=True, default="-")
    # [0-1] Possibly provide a link to the manuscript online
    link = models.TextField("Link (if available)", blank=True, null=True)
    # [0-1] And the associated URL for this link
    url = models.URLField("URL of this link", blank=True, null=True)
    # [1] Each Manuscript belongs to a collection
    collection = models.ForeignKey(SermonCollection, related_name="manuscripts", on_delete=models.CASCADE)

    # --------- MANY-TO-MANY connections ------------------
    # [0-n] = zero or more notetags in the 'info' field
    infotags = models.ManyToManyField(TagKeyword, blank=True, related_name="manuscript_infotags")

    mixed_tag_fields = [
            {"textfield": "info", "m2mfield": "infotags",     "class": TagKeyword, "url": "tagkeyword_details"}
        ]

    def __str__(self):
        return self.info

    def get_link_markdown(self):
        sBack = ""
        if self.link:
            sBack = markdown(self.link)
            sBack = sBack.strip()
        return sBack

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        response = super(Manuscript, self).save(force_insert, force_update, using, update_fields)
        # Adapt the information in sermoncollection
        self.collection.adapt_manucount()
        return response

    def delete(self, using = None, keep_parents = False):
        response = super(Manuscript, self).delete(using, keep_parents)
        # Adapt the information in sermoncollection
        self.collection.adapt_manucount()
        return response

    def get_info_markdown(self):
        sBack = ""
        if self.info:
            sBack = markdown(self.get_info_display)
            sBack = sBack.strip()
        return sBack

    def has_link(self):
        """Return '*' if a link is defined"""
        return "*" if self.url and self.url != "" else ""
    
    def has_info(self):
        """Return '*' if info is defined"""
        return "*" if self.info and self.info != "" and self.info != "-" else ""
    

class Book(models.Model):
    """Book in the Bible""" 

    # [1] Every book must have a number
    num = models.IntegerField("Number")
    # [1] Every book must have a standard abbreviations
    abbr = models.CharField("Abbreviation", max_length=MEDIUM_LENGTH)
    # [1] Every book must have a full name
    name = models.CharField("Name", max_length = MEDIUM_LENGTH)
    # [1] The number of chapters in this book
    chapters = models.IntegerField("Chapters")
    # [0-1] The chapter/verse layout of this book (JSON list of objects)
    layout = models.TextField("Chapter/verse layout (JSON)", default="[]")

    def __str__(self):
        return self.abbr


class Topic(models.Model):
    # [1] Every topic consists of a name
    name = models.CharField("Name", max_length = MEDIUM_LENGTH)

    def __str__(self):
        return "-" if self == None else  self.name


class Concept(models.Model):
    # [1] Every concept consists of a name
    name = models.CharField("Name", max_length = MEDIUM_LENGTH)
    # [1] Every concept must belong to language English or Latin
    language = models.CharField("Language", choices=build_abbr_list(LANGUAGE_tYPE),  max_length=5)

    def __str__(self):
        combi = "{} - {}".format(self.name, self.language)
        return combi


class Publisher(models.Model):
    """A publisher is defined by a name"""

    # [1]
    name = models.CharField("name", max_length=MEDIUM_LENGTH, null=True, blank=True)

    def __str__(self):
        return "-" if self == None else  self.name


class Edition(tagtext.models.TagtextModel):
    """An edition belonging to a particular sermon collection"""

    # [0-1] Code: first number collection, second edition
    code = models.CharField("Code", max_length=MEDIUM_LENGTH, null=True, blank=True)

    # [0-1] Identification number assigned by the researcher
    idno = models.IntegerField("Edition number", blank=True, null=True)

    # ------------ DATE DEFINITION -----------------
    # [0-1] Date when this edition was published
    date = models.IntegerField("Year of publication (earliest)", blank=True, null=True)
    date_late = models.IntegerField("Year of publication (latest)", blank=True, null=True)
    # [0-1] Type of this date: fixed, approximate?
    datetype = models.CharField("Date type", choices=build_abbr_list(DATE_TYPE), max_length=5)
    # [0-1] Comment on the date
    datecomment = models.TextField("Comment on the date", blank=True, null=True)

    # [0-1] Place of manuscript: may be city or country
    place = models.ForeignKey(Location, blank=True, null=True, on_delete=models.SET_NULL)
    # [0-1] Format: a fixed number of choices
    format = models.CharField("Format", choices=build_abbr_list(FORMAT_TYPE), max_length=5, blank=True, null=True)
    # [0-1] Number of folia: this may include the text layout 
    folia = models.TextField("Number of folia", blank=True, null=True)

    # [1] Number of sermons: this is free text
    numsermons = models.TextField("Number of sermons", default="-")

    # [0-1] Notes on this Edition
    note = models.TextField("Note", null=True, blank=True)

    # ----------- PARATEXTUAL ELEMENTS -------------
    # [0-1] Front or title page
    frontpage = models.TextField("Front page / title page", blank=True, null=True)
    # [0-1] Prologue
    prologue = models.TextField("Prologue", blank=True, null=True)
    # [0-1] Dedicatory letter
    dedicatory = models.TextField("Dedicatory letter", blank=True, null=True)
    # [0-1] Table of contents
    contents = models.TextField("Table of contents", blank=True, null=True)
    # [0-1] List of sermons
    sermonlist = models.TextField("List of sermons", blank=True, null=True)
    # [0-1] Other texts
    othertexts = models.TextField("Other texts", blank=True, null=True)
    # [0-1] Other texts
    images = models.TextField("Images", blank=True, null=True)
    # [0-1] Other texts
    fulltitle = models.TextField("Full title", blank=True, null=True)
    # [0-1] Other texts
    colophon = models.TextField("Colophon", blank=True, null=True)

    # ======================== HELPER ===============================
    firstpublisher = models.ForeignKey(Publisher, blank=True, null=True, related_name="firstpublisher_editions")

    # [1] Each edition belongs to a sermoncollection. 
    #     (When the SermonCollection is deleted, I should be deleted too - CASCADE)
    sermoncollection = models.ForeignKey(SermonCollection, related_name="editions", on_delete=models.CASCADE)

    # --------- MANY-TO-MANY connections ------------------
    # [n-n] Each edition may have any number of publishers
    publishers = models.ManyToManyField(Publisher, related_name="publisher_editions", blank=True)
    # [0-n] = zero or more notetags in the note field
    notetags = models.ManyToManyField(TagKeyword, blank=True, related_name="edition_notetags")

    mixed_tag_fields = [
            {"textfield": "note",           "m2mfield": "notetags",     "class": TagKeyword, "url": "tagkeyword_details"}
        ]

    def __str__(self):
        code = self.get_code()
        return code

    def tagtext_url(self):
        url = reverse('api_tributes')
        return url

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        # CHeck who the 'firstpublisher' is and adapt
        self.firstpublisher = self.get_firstpublisher()

        response = super(Edition, self).save(force_insert, force_update, using, update_fields)
        # Adapt the information in sermoncollection
        self.sermoncollection.adapt_editions()
        return response

    def delete(self, using = None, keep_parents = False):
        response = super(Edition, self).delete(using, keep_parents)
        # Adapt the information in sermoncollection
        self.sermoncollection.adapt_editions()
        return response

    def do_publishers():
        qs = Edition.objects.all()
        with transaction.atomic():
            for edi in qs:
                obj = edi.get_firstpublisher()
                if obj != edi.firstpublisher:
                    edi.firstpublisher = obj
                    edi.save()
        return True

    def get_code(self):
        """Get the code of collection/edition"""

        sBack = ""
        if self.sermoncollection == None or self.sermoncollection.idno == None:
            collnum = "-"
        else:
            collnum = self.sermoncollection.idno
        if self.idno == None:
            idno = "-"
        else:
            idno = self.idno
        sBack = "{}/{}".format(collnum, idno)

        return sBack

    def get_firstpublisher(self):
        # CHeck who the 'firstpublisher' is and adapt
        obj = self.publishers.all().order_by('name').first()
        return obj

    def get_sermons(self):
        """Recover all the sermons that fall under this edition"""

        oErr = ErrHandle()
        qs = []
        try:
            # Get the basic collection/sermons
            qs = self.sermoncollection.sermons.all()
            # TODO: order the sermons somehow??
        except:
            sMsg = oErr.get_error_message()
            oErr.DoError("Edition/get_sermons")
            qs = None
        return qs

    def sermon_count(self):
        """The number of sermons under this edition"""

        count = self.sermoncollection.sermons.all().count()
        return count

    def get_date(self):
        """Combine the date fields into a listview-showable version"""

        lCombi = []
        if self.date != None:
            if self.date_late == None or self.date == self.date_late:
                lCombi.append("{}".format(self.date))
            else:
                lCombi.append( "{}-{}".format(self.date, self.date_late))
        elif self.date_late != None:
            lCombi.append( "{}".format(self.date_late))
        else:
            lCombi.append( "-")
        lCombi.append(self.get_datetype_display())
        date = " ".join(lCombi)
        return date

    def get_full_date(self):
        """Combine the date fields including datecomment and so on"""

        lCombi = []
        lCombi.append(self.get_date())
        if self.datecomment:
            lCombi.append("; ")
            lCombi.append(self.datecomment)
        date = "".join(lCombi)
        return date

    def get_place(self):
        """Combine the place/location fields into a listview-showable version"""

        place = ""
        if self.place != None:
            place = self.place.name
        return place

    def get_editors(self):
        """Get a list of editors"""

        sBack = ""

        return sBack

    def get_publisher(self):
        """Return the publisher(s)"""

        lPublisher = []
        for obj in self.publishers.all():
            lPublisher.append(obj.name)
        return "; ".join(lPublisher)

    def get_publishers(self):
        """Return the publishers (printable)"""

        lPublisher = []
        for obj in self.publishers.all():
            url = reverse('publisher_details', kwargs={'pk': obj.id})
            lPublisher.append("<a href='{}'><span class='publisher'>{}</span></a>".format(url, obj.name))
        return ", ".join(lPublisher)

    def has_notes(self):
        """Return asterisk if has notes"""

        sBack = ""
        if self.note: sBack = "*"
        return sBack


class Sermon(tagtext.models.TagtextModel):
    """The layout of one particular sermon (level three)"""

    # [0-1] Each sermon must be recognizable by a particular code
    #       The code x/y/z of the sermon refers to the collection, the edition used for the analysis, the number of the sermon
    code = models.CharField("Code", max_length=MEDIUM_LENGTH, null=True, blank=True)

    # [0-1] Identification number assigned by the researcher
    idno = models.IntegerField("Sermon number", blank=True, null=True)

    # [0-1] Liturgical day (e.g. T18/4 = sermon 'de tempore', week 18, day 4)
    litday = models.CharField("Liturgical day", max_length=MEDIUM_LENGTH, null=True, blank=True)
    # [0-1] Thema = initial line of a sermon
    thema = models.TextField("Thema", null=True, blank=True)
    # [0-1] Biblical reference (optional), consisting of three parts: book, chapter, verse
    book = models.ForeignKey(Book, related_name="book_sermons", null=True, blank=True, on_delete=models.SET_NULL)
    chapter = models.IntegerField("Chapter", null=True, blank=True)
    verse = models.IntegerField("Verse", null=True, blank=True)
    # [0-1] The main division of the sermon: both in Latin as well as in English
    divisionL = models.TextField("Division (Latin)", null=True, blank=True)
    divisionE = models.TextField("Division (English)", null=True, blank=True)
    # [0-1] Summary of the sermon
    summary = models.TextField("Summary", null=True, blank=True)
    # [0-1] Notes on this sermon
    note = models.TextField("Note", null=True, blank=True)

    # [0-1] This is a helper field that gets automatically filled with the first topic in 'topics'
    firsttopic = models.ForeignKey(Topic, blank=True, null=True)

    # [1] Each sermon belongs to a collection
    collection = models.ForeignKey(SermonCollection, related_name="collection_sermons", on_delete=models.CASCADE)
    # [0-1] Each sermon *MAY* belong to an edition
    edition = models.ForeignKey(Edition, related_name="collection_editions", null=True, blank=True, on_delete=models.SET_NULL)

    # =================== many-to-many fields =================================================
    # [0-n] zero or more topics
    topics = models.ManyToManyField(Topic, blank=True, related_name="sermon_topics")
    # [0-n] Zero or more concepts linked to each Sermon
    concepts = models.ManyToManyField(Concept, blank=True)
    # [0-n] = zero or more qsource tags in the summary field
    # summarytags = models.ManyToManyField(TagQsource, blank=True, related_name="sermon_summarytags")
    summarynotetags = models.ManyToManyField(TagKeyword, blank=True, related_name="sermon_summarynotes")
    # [0-n] = zero or more notetags in the note field
    notetags = models.ManyToManyField(TagKeyword, blank=True, related_name="sermon_notetags")

    mixed_tag_fields = [
            {"textfield": "summary",    "m2mfield": "summarynotetags",  "class": TagKeyword,    "url": "tagkeyword_details"},
            {"textfield": "note",       "m2mfield": "notetags",         "class": TagKeyword,    "url": "tagkeyword_details"}
        ]

    def tagtext_url(self):
        url = reverse('api_tributes')
        return url

    def __str__(self):
        return self.code if self.code else ""

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        # CHeck who the 'firstauthor' is and adapt
        if self.id:
            obj = self.topics.all().first()
            if self.firsttopic == None or (obj != None and self.firsttopic is not obj):
                self.firsttopic = obj
        response = super(Sermon, self).save(force_insert, force_update, using, update_fields)
        return None

    def get_code(self):
        """Get the code of collection/edition/sermon"""

        sBack = ""
        if self.collection == None or self.collection.idno == None:
            collnum = "0"
        else:
            collnum = self.collection.idno
        if self.edition == None or self.edition.idno == None:
            edinum = "0"
        else:
            edinum = self.edition.idno
        if self.idno == None:
            idno = "-"
        else:
            idno = self.idno
        sBack = "{}/{}/{}".format(collnum, edinum, idno)

        return sBack

    def get_bibref(self):
        sRef = "-"
        if self.book != None:
            sBook = self.book.name
            if self.chapter:
                if self.verse:
                    sRef = "{} {}:{}".format(sBook, self.chapter, self.verse)
                else:
                    sRef = "{} {}".format(sBook, self.chapter)
            else:
                sRef = sBook
        return sRef

    def get_concepts(self):
        cnc_list = [x.name for x in self.concepts.all()]
        return ", ".join(cnc_list)

    def get_concepts_markdown(self):
        lHtml = []
        # Visit all concepts
        for concept in self.concepts.all():
            # Determine where clicking should lead to
            url = "{}?sermo-cnclist={}".format(reverse('sermon_list'), concept.id)
            # Create a display for this concept
            lHtml.append("<span class='topic'><a href='{}'>{}</a></span>".format(url,concept.name))

        sBack = ", ".join(lHtml)
        return sBack

    def get_full_thema(self):
        sBack = ""
        if self.thema: 
            sBack = "_{}_ ({})".format(self.thema, self.get_bibref())
        else:
            sBack = self.get_bibref()
        sBack = markdown(sBack.strip())
        return sBack

    def get_topics(self):
        """Get a list of topics"""

        topics = [x.name for x in self.topics.all()]
        sBack = ", ".join(topics)
        return sBack

    def get_topics_markdown(self):
        lHtml = []
        # Visit all topics
        for topic in self.topics.all():
            # Determine where clicking should lead to
            url = "{}?sermo-toplist={}".format(reverse('sermon_list'), topic.id)
            # Create a display for this topic
            lHtml.append("<span class='topic'><a href='{}'>{}</a></span>".format(url,topic.name))

        sBack = ", ".join(lHtml)
        return sBack

    def get_authors(self):
        """Get the name of the author"""

        sBack = "-"
        if self.collection:
            lCombi = []
            for obj in self.collection.authors.all():
                lCombi.append(obj.name)
            sBack = ", ".join(lCombi)
        return sBack

    def get_summary_markdown(self, obj=None):
        sBack = ""
        if self.summary:
            # Retrieve the whole
            sWhole = markdown(self.get_summary_display).strip()
            if obj:
                sWhole = tag_combine_html(obj, self.summary, sWhole)
            # Combine everything
            sBack = sWhole
        return sBack


class Consulting(models.Model):
    """An actual copy that the researcher has consulted or has seen"""

    # [0-1] Location
    location = models.TextField("Location", blank=True, null=True)
    # [0-1] link
    link = models.URLField("Link to online edition", blank=True, null=True)
    label = models.CharField("Name for the link", blank=True, null=True, max_length=MEDIUM_LENGTH)
    # [0-1] Ownership
    ownership = models.TextField("Ownership", blank=True, null=True)
    # [0-1] Marginalia
    marginalia = models.TextField("Marginalia", blank=True, null=True)
    # [0-1] Images
    images = models.TextField("Images", blank=True, null=True)
    # [1] Each consulting pertains to a particular edition
    edition = models.ForeignKey(Edition, blank=True, null=True, on_delete=models.SET_NULL, related_name="consultings")

    def __str__(self):
        return "-" if self == None else self.location


class Dbcode(models.Model):
    """Code of edition in other database"""

    # [1] Obligatory name for this link
    name = models.CharField("Name", max_length = MEDIUM_LENGTH)
    # [1] URL 
    url = models.URLField("URL")
    # [1] Link to the edition
    edition = models.ForeignKey(Edition, related_name="dbcodes", on_delete=models.CASCADE)

    def __str__(self):
        sBack = "{}: {}".format(self.name, self.url)
        return sBack

    def get_link(self):
        return self.url

    def get_label(self):
        return self.name


class Signature(models.Model):
    """Each edition may have a code/id in a widely used db (ISTC, GW, Edit16)"""

    # [1] The actual code
    code = models.CharField("Code", max_length=MEDIUM_LENGTH, null=True, blank=True)
    # [0-1] The link to that database
    link = models.URLField("Link to external database", null=True, blank=True)
    # [1] One signature belongs to exactly one Edition
    #     (When an edition is removed, the signature needs to be removed too)
    edition = models.ForeignKey(Edition, related_name="signatures", on_delete=models.CASCADE)

    def __str__(self):
        return "-" if self == None else  self.code


