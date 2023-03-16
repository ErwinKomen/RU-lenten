"""Models for the BASIC app.

"""
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.query import QuerySet 
from django.utils import timezone

import json

# provide error handling
from .utils import ErrHandle

LONG_STRING=255
MAX_TEXT_LEN = 200

def get_current_datetime():
    """Get the current time"""
    return timezone.now()


# Create your models here.


class Address(models.Model):
    """IP addresses that have been blocked"""

    # [1] The IP address itself
    ip = models.CharField("IP address", max_length = MAX_TEXT_LEN)
    # [1] The reason for blocking
    reason = models.TextField("Reason")

    # [0-1] The date when blocked
    created = models.DateTimeField(default=get_current_datetime)

    # [0-1] The path that the user has used
    path = models.TextField("Path", null=True, blank=True)

    # [0-1] The whole body of the request
    body = models.TextField("Body", null=True, blank=True)

    def __str__(self):
        sBack = self.ip
        return sBack

    def add_address(ip, request, reason):
        """Add an IP to the blocked ones"""

        bResult = True
        oErr = ErrHandle()
        try:
            if ip != "127.0.0.1":
                # Check if it is on there already
                obj = Address.objects.filter(ip=ip).first()
                if obj is None:
                    # It is not on there, so continue
                    path = request.path
                    get = request.POST if request.POST else request.GET
                    body = json.dumps(get)
                    obj = Address.objects.create(ip=ip, path=path, body=body, reason=reason)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Address/add_address")
            bResult = False

        return bResult

    def is_blocked(ip, request):
        """Check if an IP address is blocked or not"""

        bResult = False
        oErr = ErrHandle()
        look_for = [
            ".php", "win.ini", "/passwd", "jasperserver"
            ]
        try:
            # Check if it is on there already
            obj = Address.objects.filter(ip=ip).first()
            if obj is None:
                # Double check
                path = request.path.lower()
                if path != "/":
                    # We need to look further
                    for item in look_for:
                        if item in path:
                            # Block it
                            Address.add_address(ip, request, item)
                            bResult = True
                            break
            else:
                # It is already blocked
                bResult = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Address/is_blocked")

        return bResult


