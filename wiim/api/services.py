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

    Args:
        model (class): model class
        schema (class): marshmallow schema class

    Attributes:
        model (class): model class
        schema (class): marshmallow schema class
        order_by (str): model column to order
    """

    def __init__(self, model, schema):
        self.Model = model
        self.Schema = schema
        self.order_by = model.id

    def create(self, **kwargs):
        """ Create a new entry

        Args:
            **kwargs: model attributes

        Returns:
            A dict with the entry that was created
        """
        item_schema = self.Schema()

        # checks required fields
        data, errors = item_schema.load(kwargs)
        if errors:
            raise Exception(errors)

        # create new model
        item = self.Model(**kwargs)

        # commit to database
        db.session.add(item)
        db.session.commit()

        # get schema to return
        result = item_schema.dump(item).data

        return result  # created

    def get_query(self, query, count=0, since_id=0, order_by='desc', filters=None):
        """ Get all items from specified relation

        Args:
            query (sqlalchemy.orm.query): SQLAlchemy query object

        Kwargs:
            count (int): query limit, use zero for WIIM_COUNT_LIMIT
            since_id (int, optional): only results with id greater than
            order_by (str): order ascending (asc) or descending (desc)
            filters (dict, optional): filters for sqlalchemy query

        Returns:
            A list with table rows data mapped, every row is a dict
        """
        items_schema = self.Schema(many=True)

        # limit fetch quantity
        if not count or count > app.config['WIIM_COUNT_LIMIT']:
            count = app.config['WIIM_COUNT_LIMIT']

        # only results with id greater than
        if since_id:
            query = query.filter(self.Model.id > since_id)

        # set default order
        order = self.order_by.desc() if order_by == 'desc' else self.order_by.asc()

        # apply filters or not
        if filters is not None:
            # for attr, value in filters.iteritems():
            #     query = query.filter(getattr(self.Model, attr) == value)
            query = query.filter_by(**filters)  # smart filter by kwargs

        # do query
        items = query.order_by(order).limit(count).all()
        result = items_schema.dump(items).data

        return result

    def get_all(self, *args, **kwargs):
        """ Get all items from specified relation

        Kwargs:
            count (int): query limit, use zero for WIIM_COUNT_LIMIT
            since_id (int, optional): only results with id greater than
            order_by (str): order ascending (asc) or descending (desc)
            filters (dict, optional): filters for sqlalchemy query

        Returns:
            A list with table rows data mapped, every row is a dict
        """
        query = self.Model.query

        return self.get_query(query, *args, **kwargs)

    def get_by_id(self, id):
        """ Get single item by id

        Args:
            id (int): Item id to query

        Returns:
            A dict with table row data mapped
        """
        item_schema = self.Schema()

        item = self.Model.query.get(id)
        result = item_schema.dump(item).data

        return result

    def update():
        """ Update existing entry

        TODO
        """
        pass

    def destroy_by_id(self, id):
        """ Remove a entry by id

        keyword arguments:
            id (int): Item id to remove

        Returns:
            True if it was a success
        """
        item = self.Model.query.get(id)

        # commit to database
        db.session.delete(item)
        db.session.commit()

        return True  # destroyed


class TagService(BaseService):
    """ Tags methods with Base Service """

    def __init__(self, *args, **kwargs):
        super(TagService, self).__init__(*args, **kwargs)

    def create(self, *args, **kwargs):
        """ Create a new Model """
        # get processes field
        if 'processes' in kwargs:
            procs = kwargs['processes']
            del kwargs['processes']
        else:
            # raise error
            raise Exception('Require Processes of the Tag')

        item_schema = self.Schema()

        # checks required fields
        data, errors = item_schema.load(kwargs)
        if errors:
            raise Exception("Validation error.")

        # create new tag
        tag = Tag(**kwargs)

        # query related processes
        processes = Process.query.filter(Process.id.in_(procs)).all()
        # set tag to process
        for process in processes:
            process.tags.append(tag)

        # add and write
        db.session.add_all(processes)
        db.session.add(tag)
        db.session.commit()

        # get schema to return
        result = item_schema.dump(tag).data

        return result  # created

    def get_by_process(self, process_id, *args, **kwargs):
        """ Get all tags from specified process

        keyword arguments:
        process_id -- process id (required)
        count -- tags per page, use zero for WIIM_COUNT_LIMIT (default 0)
        filters -- filters for sqlalchemy (default None)
        """
        query = Tag.query.filter(Tag.processes.any(Process.id == process_id))

        return self.get_query(query, *args, **kwargs)


class RecordService(BaseService):
    """ Record methods with Base Service """

    def __init__(self, *args, **kwargs):
        super(RecordService, self).__init__(*args, **kwargs)

        self.order_by = Record.time_opc  # orverride order by column

    def create(self, *args, **kwargs):
        """ Create a new entry """
        # checks if tag id exits
        if db.session.query(Tag.id).filter_by(id=kwargs['tag_id']).scalar() is None:
            raise Exception("Have no Tag with id equal " + str(kwargs['tag_id']))

        # continue with default method
        return super(RecordService, self).create(*args, **kwargs)

    def get_by_process(self, process_id, *args, **kwargs):
        """ Get all tags from specified process

        keyword arguments:
        process_id -- related process id (required)
        page -- page number (default 1)
        count -- tags per page, use zero for WIIM_COUNT_LIMIT (default 0)
        filters -- filters for sqlalchemy (default None)
        """

        # get tags by process id
        t = Tag.query.filter(Tag.processes.any(Process.id == process_id)).subquery('t')
        # query records with previous tags
        query = Record.query.filter(Record.tag_id == t.c.id)

        return self.get_query(query, *args, **kwargs)

    def get_by_tags(self, tags, *args, **kwargs):
        """ Get all records from a tags list

        keyword arguments:
        tags -- list with tags id (required)
        page -- page number (default 1)
        count -- tags per page, use zero for WIIM_COUNT_LIMIT (default 0)
        filters -- filters for sqlalchemy (default None)
        """

        # get records with tags id
        query = Record.query.filter(Record.tag_id.in_(tags))

        return self.get_query(query, *args, **kwargs)


# Initialize services
site_service = BaseService(Site, SiteSchema)
zone_service = BaseService(Zone, ZoneSchema)
process_service = BaseService(Process, ProcessSchema)
server_service = BaseService(Server, ServerSchema)
tag_service = TagService(Tag, TagSchema)
record_service = RecordService(Record, RecordSchema)
