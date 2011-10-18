"""
datatools.management.commands.dumpdata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.db import router, DEFAULT_DB_ALIAS
from django.db.models import ForeignKey

import itertools
from optparse import make_option
from collections import defaultdict

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--format', default='json', dest='format',
            help='Specifies the output serialization format for fixtures.'),
        make_option('--indent', default=None, dest='indent', type='int',
            help='Specifies the indent level to use when pretty-printing output'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a specific database to load '
                'fixtures into. Defaults to the "default" database.'),
        make_option('-e', '--exclude', dest='exclude',action='append', default=[],
            help='App to exclude (use multiple --exclude to exclude multiple apps).'),
        make_option('-n', '--natural', action='store_true', dest='use_natural_keys', default=False,
            help='Use natural keys if they are available.'),
        make_option('-l', '--limit', dest='limit', type='int', default=None,
            help='Limit the number of objects per app.'),
        make_option('-s', '--sort', dest='sort', default='asc',
            help='Change the sort order (useful with limit). Defaults to asc'),
    )
    help = 'Output the contents of the database as a fixture of the given format.'
    args = '[appname appname.ModelName ...]'

    def handle(self, *app_labels, **options):
        """
        Serializes objects from the database.

        Works much like Django's ``manage.py dumpdata``, except that it allows you to
        limit and sort the apps that you're pulling in, as well as automatically follow
        the dependency graph to pull in related objects.
        """
        # TODO: excluded_apps doesnt correctly handle foo.bar if you're not using app_labels
        from django.db.models import get_app, get_apps, get_model, get_models

        format = options.get('format', 'json')
        indent = options.get('indent', None)
        limit = options.get('limit', None)
        sort = options.get('sort', 'asc')
        using = options.get('database', None)
        exclude = options.get('exclude', [])
        show_traceback = options.get('traceback', True)
        use_natural_keys = options.get('use_natural_keys', False)

        excluded_apps = set(get_app(app_label) for app_label in exclude)

        if len(app_labels) == 0:
            model_list = set(m for m in (get_models(a) for a in get_apps() if a not in excluded_apps))
        else:
            model_list = set()
            app_labels = list(app_labels)
            while app_labels:
                label = app_labels.pop(0)

                if label in excluded_apps:
                    continue

                try:
                    app_label, model_label = label.split('.')
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)

                    if app_label in excluded_apps:
                        continue

                    model = get_model(app_label, model_label)
                    if model is None:
                        raise CommandError("Unknown model: %s.%s" % (app_label, model_label))

                    model_list.add(model)

                except ValueError:
                    # This is just an app - no model qualifier
                    app_label = label
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
                    model_list.update(get_models(app))

        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        if format not in serializers.get_public_serializer_formats():
            raise CommandError("Unknown serialization format: %s" % format)

        try:
            serializers.get_serializer(format)
        except KeyError:
            raise CommandError("Unknown serialization format: %s" % format)

        # Now collate the objects to be serialized.
        objects = []
        for model in model_list:
            if not model._meta.proxy and router.allow_syncdb(using, model):
                qs = model._default_manager
                if using:
                    qs = qs.using(using)
                qs = qs.all()

                if sort == 'desc':
                    qs = qs.order_by('-pk')
                elif sort == 'asc':
                    qs = qs.order_by('pk')
                if limit:
                    qs = qs[:limit]

                results = list(qs)
                if results:
                    objs_to_check = [results[:]]
                    while objs_to_check:
                        i_objs = objs_to_check.pop(0)
                        i_model = i_objs[0].__class__

                        # Handle O2M dependencies
                        for field in (f for f in i_model._meta.fields if isinstance(f, ForeignKey)):
                            qs = field.rel.to._default_manager
                            if using:
                                qs = qs.using(using)
                            i_res = [o for o
                                     in qs.filter(pk__in=[getattr(r, field.column) for r in i_objs])
                                     if o not in results]
                            if i_res:
                                objs_to_check.append(i_res)
                                results.extend(i_res)

                        # Handle M2M dependencies
                        # TODO: this could be a lot more efficient on the SQL query
                        for field in i_model._meta.many_to_many:
                            i_res = [o for o
                                     in itertools.chain(*[getattr(r, field.name).all() for r in i_objs])
                                     if o not in results]
                            if i_res:
                                objs_to_check.append(i_res)
                                results.extend(i_res)

                for obj in results:
                    if obj not in objects:
                        objects.append(obj)

        objects = sort_dependencies(objects)

        try:
            return serializers.serialize(format, objects, indent=indent,
                        use_natural_keys=use_natural_keys)
        except Exception, e:
            if show_traceback:
                raise
            raise CommandError("Unable to serialize database: %s" % e)

def sort_dependencies(objects):
    """
    Sort a list of instances by their model dependancy graph.

    This is very similar to Django's sort_dependencies method except
    for two big differences:

    1. We graph dependencies unrelated to natural_key.
    2. We take a list of objects, and return a sorted list of objects.
    """
    from django.db.models import get_model
    # Process the list of models, and get the list of dependencies
    model_dependencies = []
    models = set()
    model_list = set()
    objs_by_model = defaultdict(list)
    for o in objects:
        model = o.__class__
        objs_by_model[model].append(o)
        model_list.add(model)

    for model in model_list:
        models.add(model)
        # Add any explicitly defined dependencies
        if hasattr(model, 'natural_key'):
            deps = getattr(model.natural_key, 'dependencies', [])
            if deps:
                deps = [get_model(*d.split('.')) for d in deps]
        else:
            deps = []

        # Now add a dependency for any FK or M2M relation with
        # a model that defines a natural key
        for field in itertools.chain(model._meta.fields, model._meta.many_to_many):
            if hasattr(field.rel, 'to') and field.rel.to != model:
                deps.append(field.rel.to)
        model_dependencies.append((model, deps))

    model_dependencies.reverse()
    # Now sort the models to ensure that dependencies are met. This
    # is done by repeatedly iterating over the input list of models.
    # If all the dependencies of a given model are in the final list,
    # that model is promoted to the end of the final list. This process
    # continues until the input list is empty, or we do a full iteration
    # over the input models without promoting a model to the final list.
    # If we do a full iteration without a promotion, that means there are
    # circular dependencies in the list.
    model_list = []
    while model_dependencies:
        skipped = []
        changed = False
        while model_dependencies:
            model, deps = model_dependencies.pop()

            # If all of the models in the dependency list are either already
            # on the final model list, or not on the original serialization list,
            # then we've found another model with all it's dependencies satisfied.
            found = True
            for candidate in ((d not in models or d in model_list) for d in deps):
                if not candidate:
                    found = False
            if found:
                model_list.append(model)
                changed = True
            else:
                skipped.append((model, deps))
        if not changed:
            raise CommandError("Can't resolve dependencies for %s in serialized app list." %
                ', '.join('%s.%s' % (model._meta.app_label, model._meta.object_name)
                for model, deps in sorted(skipped, key=lambda obj: obj[0].__name__))
            )
        model_dependencies = skipped

    sorted_results = []
    for model in model_list:
        sorted_results.extend(objs_by_model[model])

    return sorted_results
