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


class ManuscriptAdmin(admin.ModelAdmin):
    """Define a Manuscript"""

    list_display = ['info', 'link']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }


class ManuscriptInline(admin.StackedInline):
    model = Manuscript
    extra = 0
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }


class EditionAdmin(admin.ModelAdmin):
    """Define an edition""" 

    filter_horizontal = ('publishers',)
    fields = ['code', 'date', 'date_late', 'datetype', 'datecomment', 'place', 'format', 'folia', 'frontpage', 'prologue', 'dedicatory', 'contents',\
              'othertexts', 'images', 'fulltitle', 'colophon', 'publishers'] #, 'consultings']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }


class EditionInline(admin.StackedInline):
    model = Edition
    extra = 0
    filter_horizontal = ('publishers',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'})},
        }


class SermonCollectionAdminForm(forms.ModelForm):
    class Meta:
        model = SermonCollection
        fields = ['idno', 'title', 'bibliography', 'datecomp', 'datetype', 'place', 'structure', 'liturgical', 'communicative', 'sources', 'exempla', 'notes', 'authors']
        widgets = {
            'bibliography':     forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'liturgical':       TagTextarea(attrs={'class': 'hidden use_tribute', 'tclass': 'liturgical'}),
            'communicative':    TagTextarea(attrs={'class': 'hidden use_tribute', 'tclass': 'communicative'}),
            'sources':          TagTextarea(attrs={'class': 'hidden use_tribute', 'tclass': 'notes'}),
            'exempla':          TagTextarea(attrs={'class': 'hidden use_tribute', 'tclass': 'notes'}),
            'notes':            TagTextarea(attrs={'class': 'hidden use_tribute', 'tclass': 'notes'}),
            }


class SermonCollectionAdmin(admin.ModelAdmin):
    """Admin interface to SermonCollection""" 

    form = SermonCollectionAdminForm
    list_display = ['idno', 'title', 'datecomp', 'authorlist']
    search_fields =  ['idno', 'title']
    list_filter = ['place', 'authors']
    inlines = [ManuscriptInline, EditionInline]
    filter_horizontal = ('authors',)


class TagNoteAdmin(admin.ModelAdmin):
    list_display = ['name']
    fields = ['name']
    search_fields = ['name']


class TagCommunicativeAdmin(admin.ModelAdmin):
    list_display = ['name']
    fields = ['name']
    search_fields = ['name']


class TagLiturgicalAdmin(admin.ModelAdmin):
    list_display = ['name']
    fields = ['name']
    search_fields = ['name']


class TopicAdmin(admin.ModelAdmin):
    list_display = ['name']
    fields = ['name']
    search_fields = ['name']


class KeywordAdmin(admin.ModelAdmin):
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
        fields = ['collection', 'code', 'litday', 'thema', 'book', 'chapter', 'verse', 'topics', 'keywords', 'divisionL', 'divisionE', 'summary', 'note']
        widgets = {
            'thema':        forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'divisionL':    forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'divisionE':    forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'Summary':      forms.Textarea(attrs={'rows': 1, 'cols': 80, 'class': 'mytextarea'}),
            'note':         TagTextarea(attrs={'class': 'hidden use_tribute', 'tclass': 'notes'}),
            }


class SermonAdmin(admin.ModelAdmin):
    form = SermonAdminForm

    list_display = ['code', 'litday', 'book', 'chapter', 'verse', 'collection']
    search_fields = ['code', 'litday', 'book']
    list_filter = ['litday', 'book']
    fields = ['collection', 'code', 'litday', 'thema', 'book', 'chapter', 'verse', 'topics', 'keywords', 'divisionL', 'divisionE', 'summary', 'note']

    filter_horizontal = ('topics', 'keywords',)

    def response_post_save_change(self, request, obj):
        """When the user presses [Save], we want to redirect to a view of the model"""

        sUrl = redirect(reverse('sermon_details', kwargs={'pk': obj.id}))
        return sUrl


class AuthorAdmin(admin.ModelAdmin):
    fields = ['name', 'info']
    list_display = ['name', 'info']
    search_fields = ['name', 'info']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }



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
admin.site.register(Topic, TopicAdmin)
admin.site.register(TagCommunicative, TagNoteAdmin)
admin.site.register(TagNote, TagCommunicativeAdmin)
admin.site.register(TagLiturgical, TagLiturgicalAdmin)
admin.site.register(Keyword, KeywordAdmin)
admin.site.register(Sermon, SermonAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Author, AuthorAdmin)

admin.site.register(Report, ReportAdmin)

# Logbook of activities
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Action, ActionAdmin)

# How to display user information
admin.site.unregister(User)
# What to display in a list
UserAdmin.list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'last_login']
# Turn it on again
admin.site.register(User, UserAdmin)

