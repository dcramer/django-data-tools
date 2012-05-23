django-data-tools
=================

A set of utilities and improvements for managing data (fixtures specifically) in Django.

Install
-------

::

    INSTALLED_APPS = (
        # ...
        'datatools',
    )

Commands
--------

dumpdata
~~~~~~~~

An improved version of the ``manage.py dumpdata`` command:

* Adds a --limit option to specify the maximum number of objects per model to fetch.
* Adds a --sort option to specify ascending or descending order for serialization.
* Automatically follows the dependency graph for ForeignKeys and ManyToManyFields.

::

    # Retrieve the latest 10000 thread objects with all their required dependencies
    python manage.py dumpdata forums.thread --limit=10000 --sort=desc

Utilities
---------

RangeQuerySetWrapper
~~~~~~~~~~~~~~~~~~~~

Efficient iteration over a large collection of database objects, using a standard range
pattern on the primary key.

::

    from datatools.query import RangeQuerySetWrapper

    qs = RangeQuerySetWrapper(Model.objects.all(), limit=100000)
    for obj in qs:
        print "Got %r!" % obj
