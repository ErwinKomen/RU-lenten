"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelMultipleChoiceField
from django.forms.utils import flatatt
from django.forms.widgets import *
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget, ModelSelect2MultipleWidget, ModelSelect2TagWidget, Select2Widget

# Application specific
from lentensermons.seeker.models import *

CHOICE_YESNO = ( ("undefined", "----"), ("yes", "Yes"), ("no", "No") )

def init_choices(obj, sFieldName, sSet, maybe_empty=False, bUseAbbr=False):
    if (obj.fields != None and sFieldName in obj.fields):
        if bUseAbbr:
            obj.fields[sFieldName].choices = build_abbr_list(sSet, maybe_empty=maybe_empty)
        else:
            obj.fields[sFieldName].choices = build_choice_list(sSet, maybe_empty=maybe_empty)
        obj.fields[sFieldName].help_text = get_help(sSet)


# ===================== WIDGETS ======================================
class LocationWidget(ModelSelect2MultipleWidget):
    model = Location
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        sLabel = "{} ({})".format(obj.name, obj.loctype)
        return sLabel


class ConceptWidget(ModelSelect2MultipleWidget):
    model = Concept
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Concept.objects.all().order_by('name').distinct()


class TopicWidget(ModelSelect2MultipleWidget):
    model = Topic
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Topic.objects.all().order_by('name').distinct()


class PublisherWidget(ModelSelect2MultipleWidget):
    model = Publisher
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Publisher.objects.all().order_by('name').distinct()


class YesNoWidget(ModelSelect2Widget):
    model = FieldChoice
    search_fields = ['english_name__icontains']

    def label_from_instance(self, obj):
        return obj.english_name

    def get_queryset(self):
        return FieldChoice.objects.filter(field='seeker.yesno').order_by('english_name').distinct()


class FormatWidget(ModelSelect2MultipleWidget):
    model = FieldChoice
    search_fields = [ 'english_name__icontains']

    def label_from_instance(self, obj):
        return obj.english_name

    def get_queryset(self):
        return FieldChoice.objects.filter(field=FORMAT_TYPE).order_by("english_name")


class LanguageWidget(ModelSelect2MultipleWidget):
    model = FieldChoice
    search_fields = ['english_name__icontains']

    def label_from_instance(self, obj):
        return obj.english_name

    def get_queryset(self):
        return FieldChoice.objects.filter(field='seeker.language').order_by('english_name').distinct()


class BookWidget(ModelSelect2MultipleWidget):
    model = Book
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Book.objects.all().order_by('name').distinct()


class CollectionWidget(ModelSelect2MultipleWidget):
    model = SermonCollection
    search_fields = [ 'title__icontains' ]

    def label_from_instance(self, obj):
        return obj.title

    def get_queryset(self):
        return SermonCollection.objects.all().order_by('title').distinct()


class AuthorWidget(ModelSelect2MultipleWidget):
    model = Author
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Author.objects.all().order_by('name').distinct()


class LocationWidget(ModelSelect2MultipleWidget):
    model = Location
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Location.objects.all().order_by('name').distinct()


class TgroupWidget(ModelSelect2MultipleWidget):
    model = Tgroup
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return self.model.objects.all().order_by('name').distinct()


class TagWidget(ModelSelect2MultipleWidget):
    model = None
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return self.model.objects.all().order_by('name').distinct()


#class TagLiturWidget(TagWidget):
#    model = TagLiturgical


#class TagCommWidget(TagWidget):
#    model = TagCommunicative


class TagKeywordWidget(TagWidget):
    model = TagKeyword


# ===================== STANDARD FORMS ================================
class BootstrapAuthenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(max_length=254,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Password'}))


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )


class UploadFileForm(forms.Form):
    """This is for uploading just one file"""

    file_source = forms.FileField(label="Specify which file should be loaded")


class UploadFilesForm(forms.Form):
    """This is for uploading multiple files"""

    files_field = forms.FileField(label="Specify which file(s) should be loaded",
                                  widget=forms.ClearableFileInput(attrs={'multiple': True}))


class SearchUrlForm(forms.Form):
    """Specify an URL"""

    search_url = forms.URLField(label="Give the URL",
                                widget=forms.URLInput(attrs={'placeholder': 'Enter the search URL...', 'style': 'width: 100%;'}))


# ====================== APPLICATION MODEL FORMS =============================
class LocationForm(forms.ModelForm):

    locationlist = ModelMultipleChoiceField(queryset=None, required=False,
                            widget=LocationWidget(attrs={'data-placeholder': 'Select containing locations...', 'style': 'width: 100%;'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Location
        fields = ['name', 'loctype']
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'loctype':     forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(LocationForm, self).__init__(*args, **kwargs)
        # Some fields are not required?
        # All fields are required
        # Get the instance
        if 'instance' in kwargs:
            # Set the items that *may* be shown
            instance = kwargs['instance']
            qs = Location.objects.exclude(id=instance.id).order_by('loctype__level', 'name')
            self.fields['locationlist'].queryset = qs
            self.fields['locationlist'].widget.queryset = qs

            # Set the list of initial items
            my_list = [x.id for x in instance.hierarchy(False)]
            #qs = Location.objects.filter(id__in=my_list).order_by('loctype__level')
            #id_list = [x for x in qs.values_list('id', flat=True)]
            # self.fields['locationlist'].initial = id_list
            self.initial['locationlist'] = my_list
        else:
            self.fields['locationlist'].queryset = Location.objects.all().order_by('loctype__level', 'name')


class LocationRelForm(forms.ModelForm):
    partof_ta = forms.CharField(label=_("Part of"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Part of...',  'style': 'width: 100%;'}))
    partof = forms.CharField(required=False)

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = LocationRelation
        fields = ['container', 'contained']

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(LocationRelForm, self).__init__(*args, **kwargs)

        # Set other parameters
        self.fields['partof_ta'].required = False
        self.fields['partof'].required = False
        self.fields['container'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.container != None:
                self.fields['partof_ta'].initial = instance.container.get_loc_name()


class ReportEditForm(forms.ModelForm):

    class Meta:
        model = Report
        fields = ['user', 'created', 'reptype', 'contents']
        widgets={'user':         forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'created':      forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'reptype':      forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'contents':     forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'})
                 }
        

class InstructionForm(forms.ModelForm):

    class Meta:
        model = Instruction
        fields = ['title', 'msg', 'status', 'created', 'saved']
        widgets={'title':     forms.TextInput(attrs={'style': 'width: 100%;', 'class': "searching"}),
                 'msg':       forms.Textarea(attrs={'rows': 2, 'cols': 60, 'style': 'height: 70px; width: 100%;'}),
                 'status':    forms.Select(attrs={'style': 'width: 100%;'}),
                 'created':   forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'saved':     forms.TextInput(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(InstructionForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['title'].required = False
        self.fields['status'].required = False
        self.fields['created'].required = False
        self.fields['saved'].required = False
    

class NewsForm(forms.ModelForm):

    class Meta:
        model = NewsItem
        fields = ['title', 'msg', 'status', 'created', 'saved', 'until']
        widgets={'title':     forms.TextInput(attrs={'style': 'width: 100%;', 'class': "searching"}),
                 'msg':       forms.Textarea(attrs={'rows': 2, 'cols': 60, 'style': 'height: 70px; width: 100%;'}),
                 'status':    forms.Select(attrs={'style': 'width: 100%;'}),
                 'created':   forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'saved':     forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'until':     forms.TextInput(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(NewsForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['title'].required = False
        self.fields['status'].required = False
        self.fields['created'].required = False
        self.fields['saved'].required = False
        self.fields['until'].required = False
    

class SermonListForm(forms.ModelForm):
    collname = forms.CharField(label=_("Collection"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection...', 'style': 'width: 100%;'}))
    collectionlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionWidget(attrs={'data-placeholder': 'Select multiple collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    descr = forms.CharField(label=_("Description"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching input-sm', 'placeholder': 'Text in division, summary or general note...', 'style': 'width: 100%;'}))
    bookname = forms.CharField(label=_("Collection"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching books input-sm', 'placeholder': 'Collection...', 'style': 'width: 100%;'}))
    booklist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=BookWidget(attrs={'data-placeholder': 'Select multiple books...', 'style': 'width: 100%;', 'class': 'searching'}))
    concept = forms.CharField(label=_("Concept"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching concepts input-sm', 'placeholder': 'Concept(s)...', 'style': 'width: 100%;'}))
    cnclist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ConceptWidget(attrs={'data-placeholder': 'Select multiple concepts...', 'style': 'width: 100%;', 'class': 'searching'}))
    toplist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=TopicWidget(attrs={'data-placeholder': 'Select multiple concepts...', 'style': 'width: 100%;', 'class': 'searching'}))
    tagsummid = forms.CharField(label=_("Summary tag"), required = False)
    tagnoteid = forms.CharField(label=_("Keyword tag"), required = False)

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Sermon
        fields = ['code', 'collection', 'litday', 'book', 'chapter', 'verse' ]
        widgets={'code':        forms.TextInput(attrs={'class': 'typeahead searching codes input-sm', 'placeholder': 'Code...', 'style': 'width: 100%;'}),
                 'collection':  forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection...', 'style': 'width: 100%;'}),
                 'litday':      forms.TextInput(attrs={'class': 'typeahead searching litdays input-sm', 'placeholder': 'Liturgical day...', 'style': 'width: 100%;'}),
                 'book':        forms.TextInput(attrs={'class': 'typeahead searching books input-sm', 'placeholder': 'Book...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(SermonListForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['code'].required = False
        self.fields['collection'].required = False
        self.fields['litday'].required = False
        self.fields['book'].required = False
        self.fields['chapter'].required = False
        self.fields['verse'].required = False
        self.fields['cnclist'].queryset = Concept.objects.all().order_by('name')
        self.fields['toplist'].queryset = Topic.objects.all().order_by('name')
        self.fields['booklist'].queryset = Book.objects.all().order_by('name')
        self.fields['collectionlist'].queryset = SermonCollection.objects.all().order_by('title')

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class ConceptListForm(forms.ModelForm):
    cncname = forms.CharField(label=_("Concept"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching concepts input-sm', 'placeholder': 'Concept...', 'style': 'width: 100%;'}))
    cnclist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ConceptWidget(attrs={'data-placeholder': 'Select multiple concepts...', 'style': 'width: 100%;', 'class': 'searching'}))
    lngname = forms.CharField(label=_("Language"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching languages input-sm', 'placeholder': 'Language...', 'style': 'width: 100%;'}))
    lnglist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=LanguageWidget(attrs={'data-placeholder': 'Select multiple languages...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Concept
        fields = ['name', 'language' ]
        widgets={'name':        forms.TextInput(attrs={'class': 'typeahead searching concept input-sm', 'placeholder': 'Concept...', 'style': 'width: 100%;'}),
                 'language':    forms.TextInput(attrs={'class': 'typeahead searching languages input-sm', 'placeholder': 'Language...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ConceptListForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['language'].required = False
        self.fields['cnclist'].queryset = Concept.objects.all().order_by('name')
        self.fields['lnglist'].queryset = FieldChoice.objects.filter(field='seeker.language').order_by('english_name')


class LitrefForm(forms.ModelForm):
    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Litref
        fields = ['full', 'short' ]
        widgets={'full':    forms.Textarea(attrs={'rows': 1, 'cols': 60, 'class': 'searching input-sm', 'placeholder': 'Full reference...', 'style': 'height: 40px; width: 100%;'}),
                 'short':   forms.Textarea(attrs={'rows': 1, 'cols': 60, 'class': 'searching input-sm', 'placeholder': 'Short reference...', 'style': 'height: 40px; width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(LitrefForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['full'].required = False
        self.fields['short'].required = False


class AuthorListForm(forms.ModelForm):
    tagnoteid = forms.CharField(label=_("Note tag"), required = False)

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Author
        fields = ['name', 'info' ]
        widgets={'name':    forms.TextInput(attrs={'class': 'searching input-sm', 
                                                  'placeholder': 'Name of the author...', 'style': 'width: 100%;'}),
                 'info':    forms.Textarea(attrs={'rows': 1, 'cols': 60, 'class': 'searching input-sm', 
                                                  'placeholder': 'Additional information...', 'style': 'height: 40px; width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(AuthorListForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['info'].required = False


class ManuscriptForm(forms.ModelForm):
    """Viewing and processing a manuscript"""

    collname = forms.CharField(label=_("Collection"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection...', 'style': 'width: 100%;'}))
    collectionlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionWidget(attrs={'data-placeholder': 'Select multiple collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    tagnoteid = forms.CharField(label=_("Keyword tag"), required = False)

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Manuscript
        fields = ['name', 'info', 'link', 'collection', 'url' ]
        widgets={'name':    forms.TextInput(attrs={'class': 'searching input-sm', 
                                                  'placeholder': 'Name of the manuscript...', 'style': 'width: 100%;'}),
                 'link':    forms.TextInput(attrs={'class': 'searching input-sm', 
                                                  'placeholder': 'Label for a link to the manuscript...', 'style': 'width: 100%;'}),
                 'url':     forms.URLInput(attrs={'class': 'searching input-sm', 
                                                  'placeholder': 'URL to the manuscript (optional)...', 'style': 'width: 100%;'}),
                 'info':    forms.Textarea(attrs={'rows': 1, 'cols': 60, 'class': 'searching input-sm', 
                                                  'placeholder': 'Additional information...', 'style': 'height: 40px; width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['link'].required = False
        self.fields['url'].required = False
        self.fields['info'].required = False
        self.fields['collection'].required = False
        self.fields['collectionlist'].queryset = SermonCollection.objects.all().order_by('title')


class PublisherListForm(forms.ModelForm):
    pbname = forms.CharField(label=_("Publisher"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching publishers input-sm', 'placeholder': 'Publisher...', 'style': 'width: 100%;'}))
    pblist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=PublisherWidget(attrs={'data-placeholder': 'Select multiple publishers...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Publisher
        fields = ['name' ]
        widgets={'name':        forms.TextInput(attrs={'class': 'typeahead searching publishers input-sm', 'placeholder': 'Publisher...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(PublisherListForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['pblist'].queryset = Publisher.objects.all().order_by('name')


class TgroupForm(forms.ModelForm):
    tgrname = forms.CharField(label=_("Tag group"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching input-sm', 'placeholder': 'Tag group...', 'style': 'width: 100%;'}))
    tgrlist = ModelMultipleChoiceField(queryset=None, required=False)

    class Meta:
        model = Tgroup
        ATTRS_FOR_FORMS = {'class': 'form-control'};
        fields = ['name' ]
        widgets={'name':        forms.TextInput(attrs={'class': 'searching input-sm', 'placeholder': 'Tag group...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(TgroupForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['tgrname'].required = False
        self.fields['tgrlist'].queryset = Tgroup.objects.all().order_by('name')


class CollectionListForm(forms.ModelForm):
    authorname = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Author...', 'style': 'width: 100%;'}))
    authorlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    placename = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Place...', 'style': 'width: 100%;'}))
    placelist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=LocationWidget(attrs={'data-placeholder': 'Select multiple places...', 'style': 'width: 100%;', 'class': 'searching'}))
    firstedition = forms.CharField(label=_("Date of first edition"), required = False)
    numeditions = forms.CharField(label=_("Number of editions"), required = False)
    taglituid = forms.CharField(label=_("Liturgical tag"), required = False)
    tagcommid = forms.CharField(label=_("Communicative tag"), required = False)
    tagnoteid = forms.CharField(label=_("Note tag"), required = False)
    tagexmpid = forms.CharField(label=_("Exemplar tag"), required = False)
    tagqsrcid = forms.CharField(label=_("Quoted source tag"), required = False)
    tagbiblid = forms.CharField(label=_("Bibliography tag"), required = False)
    hasmanu = forms.ChoiceField(label=_(""), required=False, widget=forms.Select(attrs={'style': 'width: 100%;'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = SermonCollection
        fields = ['idno', 'title', 'datecomp', 'place' ]
        widgets={'idno':        forms.NumberInput(attrs={'class': 'typeahead searching codes input-sm', 'placeholder': 'Identifier...', 'style': 'width: 100%;'}),
                 'title':       forms.TextInput(attrs={'class': 'typeahead searching titles input-sm', 'placeholder': 'Title...', 'style': 'width: 100%;'}),
                 'datecomp':    forms.TextInput(attrs={'class': 'typeahead searching litdays input-sm', 'placeholder': 'Year of composition...', 'style': 'width: 100%;'}),
                 'place':       forms.TextInput(attrs={'class': 'typeahead searching books input-sm', 'placeholder': 'Place...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CollectionListForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['idno'].required = False
        self.fields['title'].required = False
        self.fields['datecomp'].required = False
        self.fields['place'].required = False
        self.fields['authorlist'].queryset = Author.objects.all().order_by('name')
        self.fields['placelist'].queryset = Location.objects.all().order_by('name')
        # Initialise the choices for [hasmanu]
        self.fields['hasmanu'].choices = CHOICE_YESNO

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class EditionListForm(forms.ModelForm):
    authorname  = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching authors input-sm', 'placeholder': 'Author...', 'style': 'width: 100%;'}))
    authorlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    publishername = forms.CharField(label=_("Publisher"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching authors input-sm', 'placeholder': 'Publisher...', 'style': 'width: 100%;'}))
    publisherlist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=PublisherWidget(attrs={'data-placeholder': 'Select multiple publishers...', 'style': 'width: 100%;', 'class': 'searching'}))
    colltitle   = forms.CharField(label=_("Collection"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection...', 'style': 'width: 100%;'}))
    colllist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionWidget(attrs={'data-placeholder': 'Select multiple collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    formatlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=FormatWidget(attrs={'data-placeholder': 'Select multiple format types...', 'style': 'width: 100%;'}))
    date_from   = forms.IntegerField(label=_("Year from"), required = False,
                                     widget=forms.TextInput(attrs={'placeholder': 'Starting from...',  'style': 'width: 30%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Year until"), required = False,
                                     widget=forms.TextInput(attrs={'placeholder': 'Until (including)...',  'style': 'width: 30%;', 'class': 'searching'}))
    placename   = forms.CharField(label=_("Place"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Place...', 'style': 'width: 100%;'}))
    placelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=LocationWidget(attrs={'data-placeholder': 'Select multiple places...', 'style': 'width: 100%;', 'class': 'searching'}))
    tagnoteid   = forms.CharField(label=_("Note tag"), required = False)
    xfrontpage  = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    xprologue   = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    xdedicatory = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    xcontents   = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    xsermonlist = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    xothertexts = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    ximages     = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    xfulltitle  = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))
    xcolophon   = forms.CharField(label=_("Select yes/no"), required=False,
                widget=YesNoWidget(attrs={'class': 'input-sm', 'data-placeholder': 'Select one option...',  'style': 'width: 100%;'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Edition
        fields = ['code', 'date', 'place', 'format', 'folia', 'numsermons', 'format', 'folia', 'numsermons',
                 'ffrontpage', 'fprologue', 'fdedicatory', 'fcontents', 'fsermonlist', 'fothertexts', 'fimages', 'ffulltitle', 'fcolophon' ]
        widgets={'code':        forms.TextInput(attrs={'class': 'typeahead searching codes input-sm', 'placeholder': 'Code...', 'style': 'width: 100%;'}),
                 'date':        forms.TextInput(attrs={'class': 'typeahead searching titles input-sm', 'placeholder': 'Year of publicstion...', 'style': 'width: 100%;'}),
                 'place':       forms.TextInput(attrs={'class': 'typeahead searching books input-sm', 'placeholder': 'Place...', 'style': 'width: 100%;'}),
                 'format':      forms.TextInput(attrs={'class': 'typeahead searching input-sm', 'placeholder': 'Format...', 'style': 'width: 100%;'}),
                 'folia':       forms.TextInput(attrs={'class': 'typeahead searching input-sm', 'placeholder': 'Number of folia...', 'style': 'width: 100%;'}),
                 'numsermons':  forms.TextInput(attrs={'class': 'typeahead searching input-sm', 'placeholder': 'Number of sermons...', 'style': 'width: 100%;'}),
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(EditionListForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['code'].required = False
            self.fields['date'].required = False
            self.fields['place'].required = False
            self.fields['format'].required = False
            self.fields['folia'].required = False
            self.fields['numsermons'].required = False
            self.fields['colltitle'].required = False

            self.fields['ffrontpage'].required = False
            self.fields['fprologue'].required = False
            self.fields['fdedicatory'].required = False
            self.fields['fcontents'].required = False
            self.fields['fsermonlist'].required = False
            self.fields['fothertexts'].required = False
            self.fields['fimages'].required = False
            self.fields['ffulltitle'].required = False
            self.fields['fcolophon'].required = False

            #init_choices(self, 'xfrontpage', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'xprologue', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'xdedicatory', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'xcontents', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'xsermonlist', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'xothertexts', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'ximages', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'xfulltitle', YESNO_TYPE, bUseAbbr=True)
            #init_choices(self, 'xcolophon', YESNO_TYPE, bUseAbbr=True)

            self.fields['authorlist'].queryset = Author.objects.all().order_by('name')
            self.fields['publisherlist'].queryset = Publisher.objects.all().order_by('name')
            self.fields['placelist'].queryset = Location.objects.all().order_by('name')
            self.fields['colllist'].queryset = SermonCollection.objects.all().order_by('title')
            self.fields['formatlist'].queryset = FieldChoice.objects.filter(field=FORMAT_TYPE).order_by("english_name")

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
        except:
            msg = oErr.get_error_message()
            oErr.DoError("EditionListForm-init")
        return None


# ====================== APPLICATION TAG FORMS =============================
class TagForm(forms.ModelForm):
    tag_widget = None
    ta_class = ""
    plural_name = ""
    tagname = forms.CharField(label=_("Tag"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching {} input-sm'.format(ta_class), 'placeholder': 'Tag...', 'style': 'width: 100%;'}))
    taglist = ModelMultipleChoiceField(queryset=None, required=False)
    tgrlist = ModelMultipleChoiceField(queryset=None, required=False,
                widget=TgroupWidget(attrs={'data-placeholder': 'Select multiple groups...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        abstract = True
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        # model = super(Meta, self).mymodel # TagLiturgical
        fields = ['name' ]
        # ta_class = super(Meta, self).ta_class
        ta_class = ""
        widgets={'name':        forms.TextInput(attrs={'class': 'typeahead searching {} input-sm'.format(ta_class), 'placeholder': 'Tag...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(TagForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        wdg = self.tag_widget(attrs={'data-placeholder': 'Select multiple {}...'.format(self.plural_name), 'style': 'width: 100%;', 'class': 'searching'})
        self.fields['taglist'].widget = wdg
        self.fields['taglist'].queryset = self.Meta.model.objects.all().order_by('name')
        self.fields['tgrlist'].queryset = Tgroup.objects.all().order_by('name')


#class TagLiturListForm(TagForm):
#    ta_class = "liturtags"
#    plural_name = "liturgical tags"
#    tag_widget = TagLiturWidget
#    class Meta(TagForm.Meta):
#        model = TagLiturgical
#        ta_class = "liturtags"
        

#class TagCommListForm(TagForm):
#    ta_class = "commtags"
#    plural_name = "communicative tags"
#    tag_widget = TagCommWidget
#    class Meta(TagForm.Meta):
#        model = TagCommunicative
#        ta_class = "commtags"


class TagKeywordListForm(TagForm):
    ta_class = "notetags"
    plural_name = "note tags"
    tag_widget = TagKeywordWidget
    class Meta(TagForm.Meta):
        model = TagKeyword
        ta_class = "notetags"


