"""
datatools.utils
~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from collections import defaultdict
from django.db.models.fields.related import SingleRelatedObjectDescriptor


def distinct(l):
    """
    Given an iterable will return a list of all distinct values.
    """
    return list(set(l))


def queryset_to_dict(qs, key='pk', singular=True):
    """
    Given a queryset will transform it into a dictionary based on ``key``.
    """
    if singular:
        result = {}
        for u in qs:
            result.setdefault(getattr(u, key), u)
    else:
        result = defaultdict(list)
        for u in qs:
            result[getattr(u, key)].append(u)
    return result


def attach_foreignkey(objects, field, related=[], database=None):
    """
    Shortcut method which handles a pythonic LEFT OUTER JOIN.

    ``attach_foreignkey(posts, Post.thread)``

    Works with both ForeignKey and OneToOne (reverse) lookups.
    """

    if not objects:
        return

    if database is None:
        database = list(objects)[0]._state.db

    is_foreignkey = isinstance(field, SingleRelatedObjectDescriptor)

    if not is_foreignkey:
        field = field.field
        accessor = '_%s_cache' % field.name
        model = field.rel.to
        lookup = 'pk'
        column = field.column
        key = lookup
    else:
        accessor = field.cache_name
        field = field.related.field
        model = field.model
        lookup = field.name
        column = 'pk'
        key = field.column

    objects = [o for o in objects if (related or getattr(o, accessor, False) is False)]

    if not objects:
        return

    # Ensure values are unique, do not contain already present values, and are not missing
    # values specified in select_related
    values = distinct(filter(None, (getattr(o, column) for o in objects)))
    if values:
        qs = model.objects.filter(**{'%s__in' % lookup: values})
        if database:
            qs = qs.using(database)
        if related:
            qs = qs.select_related(*related)

        queryset = queryset_to_dict(qs, key=key)
    else:
        queryset = {}

    for o in objects:
        setattr(o, accessor, queryset.get(getattr(o, column)))
