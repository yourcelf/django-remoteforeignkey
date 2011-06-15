from django.db import models
from django.db.models.fields.related import SingleRelatedObjectDescriptor, curry, ManyToManyRel, Field, _, string_concat, create_many_related_manager, router, ReverseManyRelatedObjectsDescriptor, RECURSIVE_RELATIONSHIP_CONSTANT, add_lazy_relation

class OneToManyRel(ManyToManyRel):
    """
    We do a OneToManyRel just like a ManyToManyRel, but set "multiple" to False
    so we don't use the "_set" semantics for it.
    """
    def __init__(self, *args, **kwargs):
        super(OneToManyRel, self).__init__(*args, **kwargs)
        self.multiple = False

class RemoteForeignObjectsDescriptor(object):
    """
    This class is roughly a mix of SingleRelatedObjectDescriptor for __get__,
    and ManyRelatedObjectDescriptor for __set__; in both case using the m2m
    related manager for the instance.

    'get' should return a single instance; 'set' should take a single instance,
    but under the hood it uses the m2m.
    """
    def __init__(self, related):
        self.related = related
        self.cache_name = related.get_cache_name()

    def get_rel_manager(self, instance):
        rel_model = self.related.model
        superclass = rel_model._default_manager.__class__
        RelatedManager = create_many_related_manager(superclass, self.related.field.rel)
        return RelatedManager(
            model=rel_model,
            core_filters={'%s__pk' % self.related.field.name: instance._get_pk_val()},
            instance=instance,
            symmetrical=False,
            source_field_name=self.related.field.m2m_reverse_field_name(),
            target_field_name=self.related.field.m2m_field_name(),
            reverse=True
        )

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        try:
            return getattr(instance, self.cache_name)
        except AttributeError:
            pass

        try:
            rel_obj = self.get_rel_manager(instance).all()[0]
        except IndexError:
            rel_obj = None
        setattr(instance, self.cache_name, rel_obj)
        return rel_obj

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Manager must be accessed via instance")

        if not self.related.field.rel.through._meta.auto_created:
            opts = self.related.field.rel.through._meta
            raise AttributeError("Cannot set values on a ManyToManyField which specifies an intermediary model. Use %s.%s's Manager instead." % (opts.app_label, opts.object_name))

        manager = self.get_rel_manager(instance)
        manager.clear()
        manager.add(value)

class RemoteForeignKey(models.ManyToManyField):
    description = _("One-to-many relationship")
    def __init__(self, to, **kwargs):
        # copied from parent only to change rel type to OneToManyRel
        try:
            assert not to._meta.abstract, "%s cannot define a relation with abstract class %s" % (self.__class__.__name__, to._meta.object_name)
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, basestring), "%s(%r) is invalid. First parameter to ManyToManyField must be either a model, a model name, or the string %r" % (self.__class__.__name__, to, RECURSIVE_RELATIONSHIP_CONSTANT)

        kwargs['verbose_name'] = kwargs.get('verbose_name', None)
        kwargs['rel'] = OneToManyRel(to,
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            symmetrical=kwargs.pop('symmetrical', to==RECURSIVE_RELATIONSHIP_CONSTANT),
            through=kwargs.pop('through', None))

        self.db_table = kwargs.pop('db_table', None)
        if kwargs['rel'].through is not None:
            assert self.db_table is None, "Cannot specify a db_table if an intermediary model is used."

        Field.__init__(self, **kwargs)

        msg = _('Hold down "Control", or "Command" on a Mac, to select more than one.')
        self.help_text = string_concat(self.help_text, ' ', msg)

    def contribute_to_class(self, cls, name):
        # Copied to parent, only to change create_many_to_many... to
        # create_one_to_many....

        # To support multiple relations to self, it's useful to have a non-None
        # related name on symmetrical relations for internal reasons. The
        # concept doesn't make a lot of sense externally ("you want me to
        # specify *what* on my non-reversible relation?!"), so we set it up
        # automatically. The funky name reduces the chance of an accidental
        # clash.
        if self.rel.symmetrical and (self.rel.to == "self" or self.rel.to == cls._meta.object_name):
            self.rel.related_name = "%s_rel_+" % name

        super(models.ManyToManyField, self).contribute_to_class(cls, name)

        # The intermediate m2m model is not auto created if:
        #  1) There is a manually specified intermediate, or
        #  2) The class owning the m2m field is abstract.
        if not self.rel.through and not cls._meta.abstract:
            self.rel.through = create_one_to_many_intermediary_model(self, cls)

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, ReverseManyRelatedObjectsDescriptor(self))

        # Set up the accessor for the m2m table name for the relation
        self.m2m_db_table = curry(self._get_m2m_db_table, cls._meta)

        # Populate some necessary rel arguments so that cross-app relations
        # work correctly.
        if isinstance(self.rel.through, basestring):
            def resolve_through_model(field, model, cls):
                field.rel.through = model
            add_lazy_relation(cls, self, self.rel.through, resolve_through_model)

        if isinstance(self.rel.to, basestring):
            target = self.rel.to
        else:
            target = self.rel.to._meta.db_table
        cls._meta.duplicate_targets[self.column] = (target, "m2m")

    def contribute_to_related_class(self, cls, related):
        #  Copied from parent, only to change the foreign object descriptor
        #  class.

        # Internal M2Ms (i.e., those with a related name ending with '+')
        # don't get a related descriptor.
        if not self.rel.is_hidden():
            setattr(cls, related.get_accessor_name(), RemoteForeignObjectsDescriptor(related))

        # Set up the accessors for the column names on the m2m table
        self.m2m_column_name = curry(self._get_m2m_attr, related, 'column')
        self.m2m_reverse_name = curry(self._get_m2m_reverse_attr, related, 'column')

        self.m2m_field_name = curry(self._get_m2m_attr, related, 'name')
        self.m2m_reverse_field_name = curry(self._get_m2m_reverse_attr, related, 'name')

        get_m2m_rel = curry(self._get_m2m_attr, related, 'rel')
        self.m2m_target_field_name = lambda: get_m2m_rel().field_name
        get_m2m_reverse_rel = curry(self._get_m2m_reverse_attr, related, 'rel')
        self.m2m_reverse_target_field_name = lambda: get_m2m_reverse_rel().field_name

def create_one_to_many_intermediary_model(field, klass):
    """
    Identical to the 'create_many_to_many_intermediary_model' implementation
    from django.db.models.fields.related, but with a 'unique' constraint added
    to the receiving relation.
    """
    from django.db import models
    managed = True
    if isinstance(field.rel.to, basestring) and field.rel.to != RECURSIVE_RELATIONSHIP_CONSTANT:
        to_model = field.rel.to
        to = to_model.split('.')[-1]
        def set_managed(field, model, cls):
            field.rel.through._meta.managed = model._meta.managed or cls._meta.managed
        add_lazy_relation(klass, field, to_model, set_managed)
    elif isinstance(field.rel.to, basestring):
        to = klass._meta.object_name
        to_model = klass
        managed = klass._meta.managed
    else:
        to = field.rel.to._meta.object_name
        to_model = field.rel.to
        managed = klass._meta.managed or to_model._meta.managed
    name = '%s_%s' % (klass._meta.object_name, field.name)

    if field.rel.to == RECURSIVE_RELATIONSHIP_CONSTANT or to == klass._meta.object_name:
        from_ = 'from_%s' % to.lower()
        to = 'to_%s' % to.lower()
    else:
        from_ = klass._meta.object_name.lower()
        to = to.lower()
    meta = type('Meta', (object,), {
        'db_table': field._get_m2m_db_table(klass._meta),
        'managed': managed,
        'auto_created': klass,
        'app_label': klass._meta.app_label,
        'unique_together': (from_, to),
        'verbose_name': '%(from)s-%(to)s relationship' % {'from': from_, 'to': to},
        'verbose_name_plural': '%(from)s-%(to)s relationships' % {'from': from_, 'to': to},
    })
    # Construct and return the new class.
    return type(name, (models.Model,), {
        'Meta': meta,
        '__module__': klass.__module__,
        from_: models.ForeignKey(klass, related_name='%s+' % name),
        to: models.ForeignKey(to_model, related_name='%s+' % name, unique=True)
    })

