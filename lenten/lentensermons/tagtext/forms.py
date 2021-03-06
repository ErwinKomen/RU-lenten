"""
Definition of forms.
"""

from django import forms
from django.forms.widgets import *
import json

class TagTextarea(forms.widgets.Textarea):
    template_name = 'tagtext/tagtextarea.html'
    remote = '/api/tagtext/'

    class Media:
        js = (
            'tagtext/js/tribute.js',
            'tagtext/js/tagtextarea.js',
            )
        css = { 'all': ("tagtext/css/tribute.css", 
                        "tagtext/css/tagtextarea.css", )
               } 

    def __init__(self, attrs=None):
        # Use slightly better defaults than HTML's 20x2 box
        default_attrs = {'cols': '80', 'rows': '2'}
        if attrs:
            default_attrs.update(attrs)
            if 'tclass' in attrs:
                self.tclass = attrs['tclass'] 
        super(TagTextarea, self).__init__(default_attrs)

    def get_context(self, name, value, attrs):
        context = {}

        # Determine how the stuff will look like
        if value == None or value == "":
            showvalue = ""
        elif value[0] != "[":
            # Plain text, not something else...
            showvalue = value
        else:
            part_list = json.loads(value)
            html = []
            for item in part_list:
                if item['type'] == "text":
                    html.append(item['value'])
                elif item['type'] == "new":
                    html.append('@{}@'.format(item['value']))
                else:
                    html.append('<span tagid="{}" contenteditable="false">{}</span>'.format(item['tagid'], item['value']))
            showvalue = "".join(html)
        # Initialize the remote call
        remote = "" if not self.remote else self.remote
        # Possibly let user adapt it
        remote = self.attrs.pop('remote', remote)
        # Get any additional class values from [self.attrs]
        extra_class= self.attrs.pop('class', "")
                
        context['widget'] = {
            'name': name,
            'is_hidden': self.is_hidden,
            'required': self.is_required,
            'value': self.format_value(value),
            'showvalue': showvalue,
            'attrs': self.build_attrs(self.attrs, attrs),
            'extra_class': extra_class,
            'remote': remote,
            'template_name': self.template_name,
        }
        return context

    
