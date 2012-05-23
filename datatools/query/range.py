"""
datatools.query.range
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from datatools.utils import attach_foreignkey

__all__ = ('RangeQuerySetWrapper', 'InvalidQuerySetError')


class InvalidQuerySetError(ValueError):
    pass


class RangeQuerySetWrapper(object):
    """
    Iterates through a queryset by chunking results by ``step`` and using GREATER THAN
    and LESS THAN queries on the primary key.

    Very efficient, but ORDER BY statements will not work.
    """

    def __init__(self, queryset, step=1000, limit=None, min_id=None, max_id=None, sorted=True,
                 select_related=[], callbacks=[]):
        # Support for slicing
        if queryset.query.low_mark == 0 and not\
          (queryset.query.order_by or queryset.query.extra_order_by):
            if limit is None:
                limit = queryset.query.high_mark
            queryset.query.clear_limits()
        else:
            raise InvalidQuerySetError

        self.limit = limit
        if limit:
            self.step = min(limit, abs(step))
            self.desc = step < 0
        else:
            self.step = abs(step)
            self.desc = step < 0
        self.queryset = queryset
        self.min_id, self.max_id = min_id, max_id
        # if max_id isnt set we sort by default for optimization
        self.sorted = sorted or not max_id
        self.select_related = select_related
        self.callbacks = callbacks

    def __iter__(self):
        max_id = self.max_id
        if self.min_id is not None:
            at = self.min_id
        elif not self.sorted:
            at = 0
        else:
            at = None

        num = 0
        limit = self.limit or max_id

        queryset = self.queryset

        # Adjust the sort order if we're stepping through reverse
        if self.sorted:
            if self.desc:
                queryset = queryset.order_by('-id')
            else:
                queryset = queryset.order_by('id')

        if self.max_id:
            queryset = queryset.filter(id__lte=max_id)

        has_results = True
        while ((max_id and at <= max_id) or has_results) and (not self.limit or num < self.limit):
            start = num

            if at is None:
                results = queryset
            elif self.desc:
                results = queryset.filter(id__lte=at)
            elif not self.desc:
                results = queryset.filter(id__gte=at)

            results = results[:self.step].iterator()

            # We treat select_related as a special clause if it's passed, and do a hash-join
            # at the application level for each chunk of results
            if self.select_related:
                results = list(results)
                for fkey in self.select_related:
                    # TODO: We only handle one level of nesting
                    if '__' in fkey:
                        fkey, related = fkey.split('__')
                    else:
                        related = []
                    attach_foreignkey(results, getattr(self.queryset.model, fkey, related))

            # Callbacks operate on a buffered chunk
            if self.callbacks:
                results = list(results)
                for callback in self.callbacks:
                    callback(results)

            for result in results:
                yield result
                num += 1
                at = result.id
                if (max_id and result.id >= max_id) or (limit and num >= limit):
                    break

            if at is None:
                break

            has_results = num > start
            if self.desc:
                at -= 1
            else:
                at += 1
