from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse
from django.shortcuts import redirect


from lentensermons.seeker.models import *
from lentensermons.seeker.forms import *
from lentensermons.tagtext.forms import *

class LogEntryAdmin(admin.ModelAdmin):

    date_hierarchy = 'action_time'

    # readonly_fields = LogEntry._meta.get_all_field_names()
    readonly_fields = [f.name for f in LogEntry._meta.get_fields()]

    list_filter = ['user', 'content_type', 'action_flag' ]
    search_fields = [ 'object_repr', 'change_message' ]    
    list_display = ['action_time', 'user', 'content_type', 'object_link', 'action_flag_', 'change_message', ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False

    def action_flag_(self, obj):
        flags = { 1: "Addition", 2: "Changed", 3: "Deleted", }
        return flags[obj.action_flag]

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = '<a href="{}">{}</a>'.format(
                reverse('admin:{}_{}_change'.format(ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return link
    object_link.allow_tags = True
    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'object'


class FieldChoiceAdmin(admin.ModelAdmin):
    readonly_fields=['machine_value']
    list_display = ['english_name','dutch_name','abbr', 'machine_value','field']
    list_filter = ['field']

    def save_model(self, request, obj, form, change):

        if obj.machine_value == None:
            # Check out the query-set and make sure that it exists
            qs = FieldChoice.objects.filter(field=obj.field)
            if len(qs) == 0:
                # The field does not yet occur within FieldChoice
                # Future: ask user if that is what he wants (don't know how...)
                # For now: assume user wants to add a new field (e.g: wordClass)
                # NOTE: start with '0'
                obj.machine_value = 0
            else:
                # Calculate highest currently occurring value
                highest_machine_value = max([field_choice.machine_value for field_choice in qs])
                # The automatic machine value we calculate is 1 higher
                obj.machine_value= highest_machine_value+1

        obj.save()


class LocationTypeAdmin(admin.ModelAdmin):
    """Definition of each location type"""

    fields = ['name', 'level']
    list_display = ['name', 'level']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class LocationRelationInline(admin.TabularInline):
    model = LocationRelation
    fk_name = 'contained'
    extra = 0                   # Number of rows to show


class LocationAdmin(admin.ModelAdmin):
    """Definition of each location"""

    fields = ['name', 'loctype']
    list_display = ['name', 'loctype']
    list_filter = ['loctype']
    inlines = [LocationRelationInline]
    filter_horizontal = ('relations',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class LocationRelationAdmin(admin.ModelAdmin):
    """All kinds of relations between locations"""

    fields = ['container', 'contained']
    list_display = ['container', 'contained']


class ActionAdmin(admin.ModelAdmin):
    """Display and edit Action moments"""

    list_display = ['user', 'when', 'itemtype', 'actiontype', 'details']
    list_filter = ['user', 'itemtype', 'actiontype']
    search_fields = ['user']
    fields = ['user', 'when', 'itemtype', 'actiontype', 'details']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class VisitAdmin(admin.ModelAdmin):
    """Display and edit Visit moments"""

    list_display = ['user', 'when', 'name', 'path']
    list_filter = ['user', 'name']
    search_fields = ['user']
    fields = ['user', 'when', 'name', 'path']


class InformationAdmin(admin.ModelAdmin):
    """Information k/v pairs"""

    list_display = ['name', 'kvalue']
    fields = ['name', 'kvalue']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class ReportAdmin(admin.ModelAdmin):
    """Information k/v pairs"""

    list_display = ['user', 'created', 'reptype', 'contents']
    fields = ['user', 'created', 'reptype', 'contents']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class NewsItemAdmin(admin.ModelAdmin):
    """Display and edit of [NewsItem] definitions"""

    list_display = ['title', 'until', 'status', 'created', 'saved' ]
    search_fields = ['title', 'status']
    fields = ['title', 'created', 'until', 'status', 'msg']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('newsitem_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('newsitem_list'))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('newsitem_list'))
        return sUrl


class ManuscriptAdminForm(forms.ModelForm):
    class Meta:
        model = Manuscript
        fields = ['name', 'info', 'link', 'url', 'collection']
        widgets = {
            'name': forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'link': forms.TextInput(attrs={'class': 'searching input-sm', 
                                                  'placeholder': 'Label for the link to the manuscript...', 'style': 'width: 100%;'}),
            'url': forms.URLInput(attrs={'class': 'searching input-sm', 
                                                  'placeholder': 'URL to the manuscript (optional)...', 'style': 'width: 100%;'}),
            'info': TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            }


class ManuscriptAdmin(admin.ModelAdmin):
    """Define a Manuscript"""

    form = ManuscriptAdminForm

    list_display = ['name', 'info', 'link', 'collection']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('manuscript_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('manuscript_list'))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('manuscript_list'))
        return sUrl


class ManuscriptInline(admin.StackedInline):
    model = Manuscript
    extra = 0
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }


class ConsultingInline(admin.StackedInline):
    model = Consulting
    fk_name = 'edition'
    extra = 0                   # Number of rows to show
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }


class DbcodeInline(admin.TabularInline):
    model = Dbcode
    fk_name = "edition"
    extra = 0
    verbose_name = "External link"
    verbose_name_plural = "External links"


class EditionAdminForm(forms.ModelForm):
    class Meta:
        model = Edition
        fields = ['sermoncollection', 'idno', 'date', 'date_late', 'datetype', 'datecomment', 'place', 'format', \
                 'folia', 'numsermons', 'frontpage', 'prologue', 'dedicatory', 'contents', 'sermonlist', \
                 'othertexts', 'images', 'fulltitle', 'colophon', 'publishers', 'note']
        # filter_horizontal = ('publishers',)
        widgets = {
            'datecomment':  TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'folia':        forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'frontpage':    TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'prologue':     TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'dedicatory':   TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'contents':     TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'sermonlist':   TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'othertexts':   TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'images':       TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'fulltitle':    TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'colophon':     TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'note':         TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            }


class EditionAdmin(admin.ModelAdmin):
    """Define an edition""" 

    form = EditionAdminForm
    filter_horizontal = ('publishers',)
    inlines = [DbcodeInline, ConsultingInline]
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('edition_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('edition_list'))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('edition_list'))
        return sUrl


class EditionInline(admin.StackedInline):
    model = Edition
    extra = 0
    filter_horizontal = ('publishers',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }


class ConsultingAdmin(admin.ModelAdmin):
    """Define the elements of a consulting:"""

    fields = ['location', 'link', 'label', 'ownership', 'marginalia', 'images']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('consulting_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        # Return to the Edition details view of the correct one
        sUrl = redirect(reverse('edition_details', kwargs={'pk': obj.edition.id}))
        return sUrl


class DbcodeAdmin(admin.ModelAdmin):
    """Define the elements of a consulting:"""

    fields = ['name', 'url']

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('dbcode_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        # Return to the Edition details view of the correct one
        sUrl = redirect(reverse('edition_details', kwargs={'pk': obj.edition.id}))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('edition_list'))
        return sUrl


class PublisherAdminForm(forms.ModelForm):
    class Meta:
        model = Publisher
        fields = ['name', 'info']
        widgets = {
            'name':         forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'info':         TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            }


class PublisherAdmin(admin.ModelAdmin):
    """Define the elements of a consulting:"""

    form = PublisherAdminForm
    fields = ['name', 'info']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('publisher_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('publisher_list'))
        return sUrl


class SermonCollectionAdminForm(forms.ModelForm):
    class Meta:
        model = SermonCollection
        fields = ['idno', 'title', 'statussrm', 'statusedi', 'bibliography', 'datecomp', 'datetype', 'place', 'structure', 
                  'liturgical', 'communicative', 'sources', 'exempla', 'notes', 'authors']
        widgets = {
            'bibliography':     TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'liturgical':       TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'communicative':    TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'sources':          TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'exempla':          TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'notes':            TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            }


class SermonCollectionAdmin(admin.ModelAdmin):
    """Admin interface to SermonCollection""" 

    form = SermonCollectionAdminForm
    list_display = ['idno', 'title', 'datecomp', 'authorlist']
    search_fields =  ['idno', 'title']
    list_filter = ['place', 'authors']
    inlines = [ManuscriptInline, EditionInline]
    filter_horizontal = ('authors',)

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('collection_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('collection_list'))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('collection_list'))
        return sUrl


class TagKeywordAdmin(admin.ModelAdmin):
    list_display = ['name', 'tgroup']
    fields = ['name', 'tgroup']
    search_fields = ['name']

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('tagkeyword_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('tagkeyword_list'))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('tagkeyword_list'))
        return sUrl


class TgroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    fields = ['name']
    search_fields = ['name']


class TopicAdmin(admin.ModelAdmin):
    list_display = ['name']
    fields = ['name']
    search_fields = ['name']


class ConceptAdmin(admin.ModelAdmin):
    list_display = ['name', 'language']
    fields = ['name', 'language']
    list_filter = ['language'] 
    search_fields = ['name']


class BookAdmin(admin.ModelAdmin):
    fields = ['num', 'abbr', 'name', 'chapters', 'layout']
    list_display = ['num', 'abbr', 'name', 'chapters'] 
    search_fields = ['abbr', 'name']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class SermonAdminForm(forms.ModelForm):
    class Meta:
        model = Sermon
        fields = ['collection', 'edition', 'idno', 'statussrm', 'litday', 'thema', 'book', 'chapter', 'verse', 'topics', 'concepts', 'divisionL', 'divisionE', 'summary', 'note']
        widgets = {
            'thema':        forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'divisionL':    TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'divisionE':    TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'summary':      TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            'note':         TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            }


class SermonAdmin(admin.ModelAdmin):
    form = SermonAdminForm

    list_display = ['code', 'litday', 'book', 'chapter', 'verse', 'collection', 'edition']
    search_fields = ['code', 'litday', 'book']
    list_filter = ['litday', 'book']
    fields = ['collection', 'edition', 'idno', 'statussrm', 'litday', 'thema', 'book', 'chapter', 'verse', 'topics', 'concepts', 'divisionL', 'divisionE', 'summary', 'note']

    filter_horizontal = ('topics', 'concepts',)

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('sermon_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('sermon_list'))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('sermon_list'))
        return sUrl


class AuthorAdminForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['name', 'info']
        widgets = {
            'name':         forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'info':         TagTextarea(attrs={'remote': '/api/tagtext/?tclass=notes' }),
            }


class AuthorAdmin(admin.ModelAdmin):
    form = AuthorAdminForm

    fields = ['name', 'info']
    list_display = ['name', 'info']
    search_fields = ['name', 'info']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('author_details', kwargs={'pk': obj.id}))
        return sUrl

    def response_add(self, request, obj, post_url_continue = None):
        sUrl = redirect(reverse('author_list'))
        return sUrl

    def response_delete(self, request, obj_display, obj_id):
        sUrl = redirect(reverse('author_list'))
        return sUrl




# Models that serve others
admin.site.register(FieldChoice, FieldChoiceAdmin)
admin.site.register(NewsItem, NewsItemAdmin)
admin.site.register(Information, InformationAdmin)

# Main program models
admin.site.register(LocationType, LocationTypeAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(LocationRelation, LocationRelationAdmin)
admin.site.register(SermonCollection, SermonCollectionAdmin)
admin.site.register(Manuscript, ManuscriptAdmin)
admin.site.register(Edition, EditionAdmin)
admin.site.register(Consulting, ConsultingAdmin)
admin.site.register(Dbcode, DbcodeAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Tgroup, TgroupAdmin)
#admin.site.register(TagCommunicative, TagCommunicativeAdmin)
admin.site.register(TagKeyword, TagKeywordAdmin)
#admin.site.register(TagLiturgical, TagLiturgicalAdmin)
admin.site.register(Concept, ConceptAdmin)
admin.site.register(Sermon, SermonAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Author, AuthorAdmin)

admin.site.register(Report, ReportAdmin)

# Logbook of activities
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Action, ActionAdmin)
admin.site.register(Visit, VisitAdmin)

# How to display user information
admin.site.unregister(User)
# What to display in a list
UserAdmin.list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'last_login']
# Turn it on again
admin.site.register(User, UserAdmin)

