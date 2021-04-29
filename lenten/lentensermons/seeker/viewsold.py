

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
    

