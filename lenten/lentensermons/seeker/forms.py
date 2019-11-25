"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelMultipleChoiceField
from django.forms.utils import flatatt
from django.forms.widgets import *
from django_select2.forms import Select2MultipleWidget, ModelSelect2MultipleWidget, ModelSelect2TagWidget

# Application specific
from lentensermons.seeker.models import *

def init_choices(obj, sFieldName, sSet, maybe_empty=False, bUseAbbr=False):
    if (obj.fields != None and sFieldName in obj.fields):
        if bUseAbbr:
            obj.fields[sFieldName].choices = build_abbr_list(sSet, maybe_empty=maybe_empty)
        else:
            obj.fields[sFieldName].choices = build_choice_list(sSet, maybe_empty=maybe_empty)
        obj.fields[sFieldName].help_text = get_help(sSet)


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


#class MultiTagTextareaWidget(forms.Textarea):
#    def render(self, name, value, attrs = None, renderer = None):
#        response = super().render(name, value, attrs, renderer)
#        flat_attrs = flatatt(attrs)
#        html = '''
#        <textarea name="{{ widget.name }}"{% include "django/forms/widgets/attrs.html" %}>
#        {% if widget.value %}{{ widget.value }}{% endif %}
#        </textarea>
#       ''' % {'attrs': flat_attrs, 'id': attrs['id'], 'value': value}

#        return mark_safe(html)


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


class LocationWidget(ModelSelect2MultipleWidget):
    model = Location
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        sLabel = "{} ({})".format(obj.name, obj.loctype)
        return sLabel


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


class KeywordWidget(ModelSelect2MultipleWidget):
    model = Keyword
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Keyword.objects.all().order_by('name').distinct()


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


class SermonListForm(forms.ModelForm):
    collname = forms.CharField(label=_("Collection"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection...', 'style': 'width: 100%;'}))
    collectionlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionWidget(attrs={'data-placeholder': 'Select multiple collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    bookname = forms.CharField(label=_("Collection"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching books input-sm', 'placeholder': 'Collection...', 'style': 'width: 100%;'}))
    booklist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=BookWidget(attrs={'data-placeholder': 'Select multiple books...', 'style': 'width: 100%;', 'class': 'searching'}))
    keyword = forms.CharField(label=_("Keyword"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching keywords input-sm', 'placeholder': 'Keyword(s)...', 'style': 'width: 100%;'}))
    kwlist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))

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
        self.fields['kwlist'].queryset = Keyword.objects.all().order_by('name')
        self.fields['booklist'].queryset = Book.objects.all().order_by('name')
        self.fields['collectionlist'].queryset = SermonCollection.objects.all().order_by('title')

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class KeywordListForm(forms.ModelForm):
    kwlist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    lnglist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=LanguageWidget(attrs={'data-placeholder': 'Select multiple languages...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Keyword
        fields = ['name', 'language' ]
        widgets={'name':        forms.TextInput(attrs={'class': 'typeahead searching keywords input-sm', 'placeholder': 'Identifier...', 'style': 'width: 100%;'}),
                 'language':    forms.TextInput(attrs={'class': 'typeahead searching languages input-sm', 'placeholder': 'Language...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(KeywordListForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['language'].required = False
        self.fields['kwlist'].queryset = Keyword.objects.all().order_by('name')
        self.fields['lnglist'].queryset = FieldChoice.objects.filter(field='seeker.language').order_by('english_name')
        
            

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

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = SermonCollection
        fields = ['idno', 'title', 'datecomp', 'place' ]
        widgets={'idno':        forms.TextInput(attrs={'class': 'typeahead searching codes input-sm', 'placeholder': 'Identifier...', 'style': 'width: 100%;'}),
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

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class EditionListForm(forms.ModelForm):
    authorname = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Author...', 'style': 'width: 100%;'}))
    authorlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    placename = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Place...', 'style': 'width: 100%;'}))
    placelist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=LocationWidget(attrs={'data-placeholder': 'Select multiple places...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Edition
        fields = ['code', 'date', 'place' ]
        widgets={'code':        forms.TextInput(attrs={'class': 'typeahead searching codes input-sm', 'placeholder': 'Code...', 'style': 'width: 100%;'}),
                 'date':        forms.TextInput(attrs={'class': 'typeahead searching titles input-sm', 'placeholder': 'Year of publicstion...', 'style': 'width: 100%;'}),
                 'place':       forms.TextInput(attrs={'class': 'typeahead searching books input-sm', 'placeholder': 'Place...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(EditionListForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['code'].required = False
        self.fields['date'].required = False
        self.fields['place'].required = False
        self.fields['authorlist'].queryset = Author.objects.all().order_by('name')
        self.fields['placelist'].queryset = Location.objects.all().order_by('name')

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']

