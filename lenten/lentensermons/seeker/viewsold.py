#class BasicListView(ListView):
#    """Basic listview"""

#    paginate_by = 15
#    entrycount = 0
#    qd = None
#    bFilter = False
#    basketview = False
#    initial = None
#    listform = None
#    plural_name = ""
#    prefix = ""
#    order_default = []
#    order_cols = []
#    order_heads = []
#    filters = []
#    searches = []
#    page_function = None
#    formdiv = None

#    def get_context_data(self, **kwargs):
#        # Call the base implementation first to get a context
#        context = super(BasicListView, self).get_context_data(**kwargs)

#        # Get parameters for the search
#        if self.initial == None:
#            initial = self.request.POST if self.request.POST else self.request.GET
#        else:
#            initial = self.initial

#        # Need to load the correct form
#        if self.listform:
#            context['{}Form'.format(self.prefix)] = self.listform(initial, prefix=self.prefix)

#        # Determine the count 
#        context['entrycount'] = self.entrycount # self.get_queryset().count()

#        # Set the prefix
#        context['app_prefix'] = APP_PREFIX

#        # Make sure the paginate-values are available
#        context['paginateValues'] = paginateValues

#        if 'paginate_by' in initial:
#            context['paginateSize'] = int(initial['paginate_by'])
#        else:
#            context['paginateSize'] = paginateSize

#        # Need to pass on a pagination function
#        # if self.page_function:
#        context['page_function'] = self.page_function
#        context['formdiv'] = self.formdiv

#        # Set the page number if needed
#        if 'page_obj' in context and 'page' in initial and initial['page'] != "":
#            # context['page_obj'].number = initial['page']
#            page_num = int(initial['page'])
#            context['page_obj'] = context['paginator'].page( page_num)
#            # Make sure to adapt the object_list
#            context['object_list'] = context['page_obj']

#        # Set the title of the application
#        context['title'] = self.plural_name

#        # Make sure we pass on the ordered heads
#        context['order_heads'] = self.order_heads
#        context['has_filter'] = self.bFilter
#        context['filters'] = self.filters

#        # Check if user may upload
#        context['is_authenticated'] = user_is_authenticated(self.request)
#        context['is_app_uploader'] = user_is_ingroup(self.request, app_uploader)
#        context['is_app_editor'] = user_is_ingroup(self.request, app_editor)

#        # Process this visit and get the new breadcrumbs object
#        context['breadcrumbs'] = process_visit(self.request, self.plural_name, True)
#        context['prevpage'] = get_previous_page(self.request)

#        # Allow others to add to context
#        context = self.add_to_context(context, initial)

#        # Return the calculated context
#        return context

#    def add_to_context(self, context, initial):
#        return context

#    def get_paginate_by(self, queryset):
#        """
#        Paginate by specified value in default class property value.
#        """
#        return self.paginate_by
  
#    def get_basketqueryset(self):
#        """User-specific function to get a queryset based on a basket"""
#        return None
  
#    def get_queryset(self):
#        # Get the parameters passed on with the GET or the POST request
#        get = self.request.GET if self.request.method == "GET" else self.request.POST
#        get = get.copy()
#        self.qd = get

#        self.bHasParameters = (len(get) > 0)
#        bHasListFilters = False
#        if self.basketview:
#            self.basketview = True
#            # We should show the contents of the basket
#            # (1) Reset the filters
#            for item in self.filters: item['enabled'] = False
#            # (2) Indicate we have no filters
#            self.bFilter = False
#            # (3) Set the queryset -- this is listview-specific
#            qs = self.get_basketqueryset()

#            # Do the ordering of the results
#            order = self.order_default
#            qs, self.order_heads = make_ordering(qs, self.qd, order, self.order_cols, self.order_heads)
#        elif self.bHasParameters:
#            # y = [x for x in get ]
#            bHasListFilters = len([x for x in get if self.prefix in x and get[x] != ""]) > 0
#            if not bHasListFilters:
#                self.basketview = ("usebasket" in get and get['usebasket'] == "True")

#        if self.bHasParameters:
#            lstQ = []
#            # Indicate we have no filters
#            self.bFilter = False

#            # Read the form with the information
#            thisForm = self.listform(self.qd, prefix=self.prefix)

#            if thisForm.is_valid():
#                # Process the criteria for this form
#                oFields = thisForm.cleaned_data
                
#                self.filters, lstQ, self.initial = make_search_list(self.filters, oFields, self.searches, self.qd)
#                # Calculate the final qs
#                if len(lstQ) == 0:
#                    # Just show everything
#                    qs = self.model.objects.all()
#                else:
#                    # There is a filter, so apply it
#                    qs = self.model.objects.filter(*lstQ).distinct()
#                    # Only set the [bFilter] value if there is an overt specified filter
#                    for filter in self.filters:
#                        if filter['enabled']:
#                            self.bFilter = True
#                            break
#            else:
#                # Just show everything
#                qs = self.model.objects.all().distinct()

#            # Do the ordering of the results
#            order = self.order_default
#            qs, self.order_heads = make_ordering(qs, self.qd, order, self.order_cols, self.order_heads)
#        else:
#            # Just show everything
#            qs = self.model.objects.all().distinct()
#            order = self.order_default
#            qs, tmp_heads = make_ordering(qs, self.qd, order, self.order_cols, self.order_heads)

#        # Determine the length
#        self.entrycount = len(qs)

#        # Return the resulting filtered and sorted queryset
#        return qs

#    def post(self, request, *args, **kwargs):
#        return self.get(request, *args, **kwargs)
    

#class SermonListView(BasicListView):
#    """Listview of sermons"""

#    model = Sermon
#    listform = SermonListForm
#    prefix = "sermo"
#    template_name = 'seeker/sermon_list.html'
#    plural_name = "Sermons"
#    order_default = ['collection__idno;edition__idno;idno', 'collection__firstauthor__name', 'collection__title', 
#                     'litday', 'book;chapter;verse', 'firsttopic__name']
#    order_cols = order_default
#    order_heads = [{'name': 'Code',             'order': 'o=1', 'type': 'int'}, 
#                   {'name': 'Authors',          'order': 'o=2', 'type': 'str'}, 
#                   {'name': 'Collection',       'order': 'o=3', 'type': 'str'}, 
#                   {'name': 'Liturgical day',   'order': 'o=4', 'type': 'str'},
#                   {'name': 'Thema',            'order': 'o=5', 'type': 'str'},
#                   {'name': 'Main topic',       'order': 'o=6', 'type': 'str'}]
#    filters = [ {"name": "Code",           "id": "filter_code",         "enabled": False},
#                {"name": "Collection",     "id": "filter_collection",   "enabled": False},
#                {"name": "Liturgical day", "id": "filter_litday",       "enabled": False},
#                {"name": "Book",           "id": "filter_book",         "enabled": False},
#                {"name": "Concept",        "id": "filter_concept",      "enabled": False},
#                {"name": "Topic",          "id": "filter_topic",        "enabled": False}]
#    searches = [
#        {'section': '', 'filterlist': [
#            {'filter': 'code',      'dbfield': 'code',      'keyS': 'code'},
#            {'filter': 'collection','fkfield': 'collection','keyS': 'collname', 
#             'keyFk': 'title', 'keyList': 'collectionlist', 'infield': 'id'},
#            {'filter': 'litday',    'dbfield': 'litday',    'keyS': 'litday'},
#            {'filter': 'book',      'fkfield': 'book',      'keyS': 'bookname', 
#             'keyFk': 'name', 'keyList': 'booklist', 'infield': 'id'},
#            {'filter': 'concept',   'fkfield': 'concepts',  'keyS': 'concept',  
#             'keyFk': 'name', 'keyList': 'cnclist',  'infield': 'id' },
#            {'filter': 'topic',     'fkfield': 'topics',                        
#             'keyFk': 'name', 'keyList': 'toplist',  'infield': 'id' }
#            ]},
#        {'section': 'other', 'filterlist': [
#            {'filter': 'tagnoteid',  'fkfield': 'notetags',         'keyS': 'tagnoteid', 'keyFk': 'id' },
#            {'filter': 'tagsummid',  'fkfield': 'summarynotetags',  'keyS': 'tagsummid', 'keyFk': 'id' }
#            ]}
#        ]
    

