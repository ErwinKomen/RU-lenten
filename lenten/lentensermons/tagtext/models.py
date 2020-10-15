import sys
from django.db import models
from django.shortcuts import redirect, reverse
from markdown import markdown
import json


# Create your models here.
class TagtextModel(models.Model):
    """A models.Model adaptation that deals with tagged text fields"""

    class Meta:
        abstract = True

    mixed_tag_fields = [ ]


    def __init__(self, *args, **kwargs):
        # Perform standard initialisations
        response = super(TagtextModel, self).__init__(*args, **kwargs)

        try:
            for item in self.mixed_tag_fields:
                textfield = item['textfield']
                textvalue = getattr(self, textfield)
                url = None if 'url' not in item else item['url']
                # Make sure the get_FIELD_display is set
                self.adapt_display(textfield, textvalue, url)
        except:
            sMsg = self.get_error_message()

        # Return our initial response
        return response

    def adapt_display(self, textfield, sText,  url=None, debug=False):
        
        try:
            if debug:
                self.Status("TagtextModel.adapt_display url={}".format(url))

            # Make sure the get_FIELD_display is adapted
            if sText == None or sText == "":
                showvalue = ""
            elif sText[0] != "[":
                # Plain text, not something else...
                showvalue = sText
            else:
                # Double check: are there parts in here?
                if "{" not in sText:
                    # Automatically convert into one huge part
                    item = dict(type="text", value=sText)
                    sText = json.dumps([item])
                arPart = json.loads(sText)
                html = []
                for item in arPart:
                    # Make sure to get the markdown of the item
                    mditem = item['value']
                    # Now look further...
                    if item['type'] == "text":
                        html.append(mditem)
                    elif item['type'] == "new":
                        html.append('@{}@'.format(mditem))
                    else:
                        # This means the field type is 'tag'
                        if url:
                            href = reverse(url, kwargs= {'pk': item['tagid']})
                            if 'style' in item and item['style'] == "italic":
                                html.append('<span tagid="{}" contenteditable="false"><a href="{}"><i>{}</i></a></span>'.format(item['tagid'], href, mditem))
                            else:
                                html.append('<span tagid="{}" contenteditable="false"><a href="{}">{}</a></span>'.format(item['tagid'], href, mditem))
                        else:
                            if 'style' in item and item['style'] == "italic":
                                html.append('<span tagid="{}" contenteditable="false"><i>{}</i></span>'.format(item['tagid'], mditem))
                            else:
                                html.append('<span tagid="{}" contenteditable="false">{}</span>'.format(item['tagid'], mditem))
                showvalue = "".join(html)
                # Now perform MD
                showvalue = markdown(showvalue).replace("<p>", "").replace("</p>", "")
            setattr(self, "get_{}_display".format(textfield), showvalue)
            return True
        except:
            sMsg = self.get_error_message()
            return False

    def delete(self, using=None, keep_parents=False):
        response = super(TagtextModel, self).delete(using=using, keep_parents=keep_parents)
        return response
    
    def get_error_message(self):
        arInfo = sys.exc_info()
        if len(arInfo) == 3:
            sMsg = str(arInfo[1])
            if arInfo[2] != None:
                sMsg += " at line " + str(arInfo[2].tb_lineno)
            return sMsg
        else:
            return ""

    def get_flat(self, textfield):
        """Get the flat text"""

        try:
            sText = getattr(self, textfield)
            if sText != None and sText != "" and sText[0] == "[":

                # Parse the string into a list
                arPart = json.loads(sText)
                lFlat = []
                # Add new tags where appropriate
                for tagobj in arPart:
                    # Get the value
                    tagname = tagobj['value']
                    lFlat.append(tagname)
                # Combine to get the text
                sText = " ".join(lFlat)
                sText = sText.strip()
                # Double check if there is anything in the text
                if sText in "-": sText = ""
            return True, sText
        except:
            sMsg = self.get_error_message()
            return False, sMsg

    def process_tags(self, textfield, tagitems, cls, url=None):
        """Extract the tags from [sText] and then make sure that the many-to-many field [m2m] only has these tags
        
        This assumes we receive a (stringified) JSON list with three types of elements:
        1 - text            {"type": "text",    "value": "this is some text"                }
        2 - existing tag    {"type": "tag",     "value": "my tag text",      "tagid": 21, "style": "italic"   }
        3 - new tag         {"type": "new",     "value": "new tag text"                     }
        """

        try:
            sText = getattr(self, textfield)
            if sText != None and sText != "" and sText[0] == "[":

                if sText[0] == "[" and "{" in sText:

                    # Parse the string into a list
                    arPart = json.loads(sText)

                    # Start a list of tag ids that are in this text
                    taglist = []

                    # Add new tags where appropriate
                    for tagobj in arPart:
                        # Get the value
                        tagname = tagobj['value']
                        # Check if this is a new tag or an existing tag
                        if tagobj['type'] == "new":
                            # Check if there is a representation followed by a lexical entry
                            arTagname = tagname.split("|")
                            visual = ""
                            if len(arTagname) > 1:
                                tagname = arTagname[1]
                                visual = arTagname[0]
                                tagobj['value'] = visual
                            # Add this tag, if the lower case comparison yields nothing
                            obj = cls.objects.filter(name__iexact=tagname.lower()).first()
                            if obj == None:
                                # Create a new tag
                                obj = cls.objects.create(name=tagname)
                            # Add the tag to the list
                            taglist.append(obj)
                            # Repair the entry in arPart
                            tagobj['tagid'] = obj.id
                            tagobj['type'] = "tag"
                            style = obj.get_style()
                            if style != None and style != "": tagobj['style'] = style
                            # Make sure to add it to [tagitems]
                            tagitems.add(obj)
                        elif tagobj['type'] == "tag":
                            obj = cls.objects.filter(id=tagobj['tagid']).first()
                            if obj == None:
                                # Need to create it anyway
                                obj = cls.objects.create(name=tagname)
                                # Repair the id
                                tagobj['tagid'] = obj.id
                                style = obj.get_style()
                                if style != None and style != "": tagobj['style'] = style
                            else:
                                style = obj.get_style()
                                if style != None and style != "": tagobj['style'] = style
                            taglist.append(obj)
                            # Check if it is in the m2m tagitems
                            if obj not in tagitems.all():
                                tagitems.add(obj)
                        # Note: no need to do anything with the text items

                    # Break the link with tags that are *not* in my current list
                    tagids = [x.id for x in taglist]
                    for obj in tagitems.all():
                        if obj.id not in tagids:
                            # Must be broken
                            tagitems.remove(obj)

                    # Process the *first* in the list
                    if len(arPart) > 0:
                        item = arPart[0]
                        if item['type'] == "text":
                            sValue = item['value']
                            sStripped = sValue.lstrip()
                            if sValue != sStripped:
                                item['value'] = sStripped

                    # Process the *last* in the list if the list is larger
                    if len(arPart) > 1:
                        item = arPart[-1]
                        if item['type'] == "text":
                            sValue = item['value']
                            sStripped = sValue.rstrip()
                            if sValue != sStripped:
                                item['value'] = sStripped
                                bChanged = True


                    # Fix the stringified text
                    sText = json.dumps(arPart)
                else:
                    # This is flat text: code it
                    sText = json.dumps([ dict(type="text", value=sText) ])

            # Make sure the get_FIELD_display is adapted
            self.adapt_display(textfield, sText, url)
        
            return True, sText
        except:
            sMsg = self.get_error_message()
            return False, sMsg

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):

        response = None
        try:
            # Perform the actual saving
            response = super(TagtextModel, self).save(force_insert, force_update, using, update_fields)

            bChanged = False
            # Process all the mixed_tag_fields
            for item in self.mixed_tag_fields:
                textfield = item['textfield']
                m2mfield = item['m2mfield']
                textflat = item.get('textflat')
                cls = item['class']
                url = None if 'url' not in item else item['url']

                # Note: this is only possible of there already is a saved ID
                if self.id:
                    bOkay, sText = self.process_tags(textfield, getattr(self, m2mfield), cls, url)
                    if bOkay:
                        if getattr(self, textfield) != sText:
                            setattr(self, textfield, sText)
                            bChanged  = True
                    else:
                        # SOmething is not okay
                        err = "Notokay"
                    # Possibly process [textflat]
                    if textflat != None:
                        bOkay, sFlat = self.get_flat(textfield)
                        if bOkay:
                            if getattr(self, textflat) != sFlat:
                                setattr(self, textflat, sFlat)
                                bChanged = True
                        else:
                            err = "Notokay"

        
            # Perform additional saving if something changed
            if bChanged:
                response = super(TagtextModel, self).save(force_insert, force_update, using, update_fields)
        except:
            sMsg = self.get_error_message()
            response = None

        # Return the saving result
        return response

    def Status(self, msg):
        # Just print the message
        print(msg, file=sys.stderr)

    def tagtext_url(self):
        """Get the correct API url"""
        return "/api/tagtext/"

