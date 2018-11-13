"""
wiim.api.services

Include Models management for API

:copyright: © 2018 by José Almeida.
:license: CC BY-NC 4.0, see LICENSE for more details.
"""

from flask import current_app as app
# application imports
from .models import *


class BaseService():
    """ Base service class

    keyword arguments:
    name -- tuple with (singular, plural) names(required)
    model -- model class (required)
    schema -- marshmallow schema class (required)
    """

    def __init__(self, name, model, schema, relation=None):
        self.name = name
        self.Model = model
        self.Schema = schema
        self.Relation = relation

    def create(self, *args, **kwargs):
        """ Create a new entry """
        item = self.Model(*args, **kwargs)

        # commit to database
        db.session.add(item)
        db.session.commit()

        return dict(success={
            'message': self.name[0] + ' was created successfully!'
        })  # created

    def get_all(self, page=1, count=0, filters=None):
        """ Get all items from specified relation

        keyword arguments:
        page -- page number (default 1)
        count -- tags per page, use zero for WIIM_COUNT_LIMIT (default 0)
        """
        items_schema = self.Schema(many=True)

        # limit fetch quantity
        if not count or count > app.config['WIIM_COUNT_LIMIT']:
            count = app.config['WIIM_COUNT_LIMIT']

        # apply filters or not
        if filters is None:
            items = self.Model.query.paginate(page, count).items
        else:
            items = self.Model.query.filter(filters).paginate(page, count).items

        items = items_schema.dump(items).data

        return {self.name[1]: items}

    def get_by_id(self, id):
        """ Get single item by id

        keyword arguments:
        id -- Item id (required)
        """
        item_schema = self.Schema()

        item = self.Model.query.get(id)
        item = item_schema.dump(item).data

        return {self.name[0]: item}

    def update():
        pass

    def destroy_by_id(self, id):
        """ Remove a entry by id

        keyword arguments:
        id -- Item id (required)
        """
        item = self.Model.query.get(id)

        # commit to database
        db.session.delete(item)
        db.session.commit()

        return dict(success={
            'message': self.name[0] + ' was destroyed successfully!'
        })  # created


class SinceService(BaseService):
    """ Add since methods to Base"""

    def __init__(self, *args, **kwargs):
        super(SinceService, self).__init__(*args, **kwargs)

    def create(self, name, alias, comment, unit, icon, server_id, processes):
        """ Create a new Model """
        tag = Tag(name=name, alias=alias, comment=comment,
                  unit=unit, icon=icon, server_id=server_id)

        for process_id in processes:
            process = Process.query.get(process_id)
            # set tag to related process
            process.tags.append(tag)
            db.session.add(process)

        # commit to database
        db.session.add(tag)
        db.session.commit()

        return dict(success={
            'message': self.name[0] + ' was created successfully!'
        })  # created

    def since(self):
        session = db.session

        tag_records_schema = TagRecordsSchema(many=True)
        tag_records = session.query(Tag, Record).filter(Tag.id == Record.tag_id).all()
        # tag_records = Tag.query.all()
        tags = []
        for x, y in tag_records:
            x.record = y
            tags.append(x)

        data, errors = tag_records_schema.dump(tags)
        # data = tag_records_schema.dump(tag_records).data
        # print(tag_records)
        # result = tag_records_schema.dump(tag_records).data

        return data

        # return item


# Initialize services
SiteService = BaseService(('Site', 'Sites'), Site, SiteSchema)
ZoneService = BaseService(('Zone', 'Zones'), Zone, ZoneSchema, Site)
ProcessService = BaseService(('Process', 'Processes'), Process, ProcessSchema, Zone)
ServerService = BaseService(('Server', 'Servers'), Server, ServerSchema)
TagService = SinceService(('Tag', 'Tags'), Tag, TagSchema, Server)
RecordService = BaseService(('Record', 'Records'), Record, RecordSchema, Tag)
