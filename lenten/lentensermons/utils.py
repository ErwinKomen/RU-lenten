import sys
from django.conf import settings
from django import http

class ErrHandle:
    """Error handling"""

    # ======================= CLASS INITIALIZER ========================================
    def __init__(self):
        # Initialize a local error stack
        self.loc_errStack = []

    # ----------------------------------------------------------------------------------
    # Name :    Status
    # Goal :    Just give a status message
    # History:
    # 6/apr/2016    ERK Created
    # ----------------------------------------------------------------------------------
    def Status(self, msg):
        # Just print the message
        print(msg, file=sys.stderr)

    # ----------------------------------------------------------------------------------
    # Name :    DoError
    # Goal :    Process an error
    # History:
    # 6/apr/2016    ERK Created
    # ----------------------------------------------------------------------------------
    def DoError(self, msg, bExit = False):
        # Append the error message to the stack we have
        self.loc_errStack.append(msg)
        # get the message
        sErr = self.get_error_message()
        # Print the error message for the user
        print("Error: {}\nSystem:{}".format(msg, sErr), file=sys.stderr)
        # Is this a fatal error that requires exiting?
        if (bExit):
            sys.exit(2)
        # Otherwise: return the string that has been made
        return "<br>".join(self.loc_errStack)

    def get_error_message(self):
        arInfo = sys.exc_info()
        if len(arInfo) == 3:
            sMsg = str(arInfo[1])
            if arInfo[2] != None:
                sMsg += " at line " + str(arInfo[2].tb_lineno)
            return sMsg
        else:
            return ""

    def get_error_stack(self):
        return " ".join(self.loc_errStack)

class BlockedIpMiddleware(object):

    bot_list = ['googlebot', 'bot.htm', 'bot.com', '/petalbot', 'crawler.com', 'robot', 'crawler' ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_request(self, request):
        oErr = ErrHandle()
        remote_ip = request.META['REMOTE_ADDR']
        if remote_ip in settings.BLOCKED_IPS:
            oErr.Status("Blocking IP: {}".format(remote_ip))
            return http.HttpResponseForbidden('<h1>Forbidden</h1>')
        else:
            # Try the IP addresses the other way around
            for block_ip in settings.BLOCKED_IPS:
                if block_ip in remote_ip:
                    oErr.Status("Blocking IP: {}".format(remote_ip))
                    return http.HttpResponseForbidden('<h1>Forbidden</h1>')
            # Get the user agent
            user_agent = request.META.get('HTTP_USER_AGENT')
            if user_agent == None or user_agent == "":
                # This is forbidden...
                oErr.Status("Blocking empty user agent")
                return http.HttpResponseForbidden('<h1>Forbidden</h1>')
            else:
                # Check what the user agent is...
                user_agent = user_agent.lower()
                for bot in self.bot_list:
                    if bot in user_agent:
                        ip = request.META.get('REMOTE_ADDR')
                        # Print it for logging
                        msg = "blocking bot: [{}] {}: {}".format(ip, bot, user_agent)
                        print(msg, file=sys.stderr)
                        return http.HttpResponseForbidden('<h1>Forbidden</h1>')
        return None
