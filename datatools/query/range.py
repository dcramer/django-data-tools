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
    """

    def __init__(self, queryset, step=1000, limit=None, min_id=None, max_id=None, sorted=True,
                 select_related=[], callbacks=[], order_by='pk'):
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
        self.min_value, self.max_value = min_id, max_id
        # if max_id isnt set we sort by default for optimization
        self.sorted = sorted or not max_id
        self.select_related = select_related
        self.callbacks = callbacks
        self.order_by = order_by

    def __iter__(self):
        max_value = self.max_value
        if self.min_value is not None:
            cur_value = self.min_value
        elif not self.sorted:
            cur_value = 0
        else:
            cur_value = None

        num = 0
        limit = self.limit

        queryset = self.queryset
        if max_value:
            queryset = queryset.filter(**{'%s__lte' % self.order_by: max_value})
            # Adjust the sort order if we're stepping through reverse
        if self.sorted:
            if self.desc:
                queryset = queryset.order_by('-%s' % self.order_by)
            else:
                queryset = queryset.order_by(self.order_by)

        # we implement basic cursor pagination for columns that are not unique
        last_value = None
        offset = 0
        has_results = True
        while ((max_value and cur_value <= max_value) or has_results) and (not self.limit or num < self.limit):
            start = num

            if cur_value is None:
                results = queryset
            elif self.desc:
                results = queryset.filter(**{'%s__lte' % self.order_by: cur_value})
            elif not self.desc:
                results = queryset.filter(**{'%s__gte' % self.order_by: cur_value})

            results = results[offset:offset + self.step].iterator()

            # hash maps to pull in select_related columns
            if self.select_related:
                # we have to pull them all into memory to do the select_related
                results = list(results)
                for fkey in self.select_related:
                    if '__' in fkey:
                        fkey, related = fkey.split('__')
                    else:
                        related = []
                    attach_foreignkey(results, getattr(self.queryset.model, fkey, related))

            if self.callbacks:
                results = list(results)
                for callback in self.callbacks:
                    callback(results)

            for result in results:
                yield result

                num += 1
                cur_value = getattr(result, self.order_by)
                if cur_value == last_value:
                    offset += 1
                else:
                    # offset needs to be based at 1 so we dont return a row
                    # that was already selected
                    last_value = cur_value
                    offset = 1

                if (max_value and cur_value >= max_value) or (limit and num >= limit):
                    break

            if cur_value is None:
                break

            has_results = num > start
