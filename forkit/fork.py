from copy import deepcopy
from django.db import models
from django.contrib.contenttypes.generic import GenericRelation
from forkit import utils, signals
from forkit.commit import commit_model_object

def _fork_one2one(instance, value, field, direct, accessor, deep, **kwargs):
    "Due to the unique constraint, only deep forks can be performed."
    if deep:
        fork = _memoize_fork(value, deep=deep, **kwargs)
        
        if not direct:
            fork = utils.DeferredCommit(fork)
            
        instance._commits.defer(accessor, fork, direct=direct)

def _fork_foreignkey(instance, value, field, direct, accessor, deep, **kwargs):
    # don't perform deep copy if strict and direct m2m    
    if deep and not (kwargs['strict'] and direct):
        if direct:
            fork = _memoize_fork(value, deep=deep, **kwargs)
        else:
            fork = [_memoize_fork(rel, deep=deep, **kwargs) for rel in value]           
            fork = utils.DeferredCommit(fork)
    else:
        memo = kwargs.pop('memo', None)
        
        if memo and memo.has(value):
            fork = memo.get(value)
        else:
            fork = value

    instance._commits.defer(accessor, fork, direct=direct)

def _fork_many2many(instance, value, field, direct, accessor, deep, **kwargs):
    if deep:
        fork = [_memoize_fork(rel, deep=deep, **kwargs) for rel in value]
        if not direct:
            fork = utils.DeferredCommit(fork)
    else:
        #todo Make optional?
        if not direct and kwargs['strict']:
            return
        
        fork = value

    instance._commits.defer(accessor, fork)
    
def _fork_generic_relation(instance, value, field, direct, accessor, deep, **kwargs):
    if kwargs['strict'] and not direct:
        return   

    if deep:
        fork = [_memoize_fork(rel, deep=deep, **kwargs) for rel in value]
        if not direct:
            fork = utils.DeferredCommit(fork)
    else:       
        #todo Make optional?
        if direct:
            fork = [_memoize_fork(rel, deep=deep, **kwargs) for rel in value]
            if not direct:       
                fork = utils.DeferredCommit(fork)
        else:
            fork = value

    instance._commits.defer(accessor, fork)

def _fork_field(reference, instance, accessor, conserve, **kwargs):
    """Creates a copy of the reference value for the defined ``accessor``
    (field). For deep forks, each related object is related objects must
    be created first prior to being recursed.
    """
    value, field, direct, m2m = utils._get_field_value(reference, accessor)

    if value is None:
        return

    # recursive calls cannot be saved until everything has been traversed..
    kwargs['commit'] = False
    
    if accessor in conserve:
        setattr(instance, accessor, value)
        return
    
    if isinstance(field, models.OneToOneField):
        return _fork_one2one(instance, value, field, direct,
            accessor, **kwargs)

    if isinstance(field, models.ForeignKey):       
        return _fork_foreignkey(instance, value, field, direct,
            accessor, **kwargs)

    if isinstance(field, models.ManyToManyField):    
        # exclude customized intermediate models
        if not field.rel.through._meta.auto_created:
            return
        
        if kwargs['strict']: 
            kwargs['deep'] = False
        
        return _fork_many2many(instance, value, field, direct,
            accessor, **kwargs)
        
    if isinstance(field, GenericRelation):   
        return _fork_generic_relation(instance, value, field, direct,
            accessor, **kwargs)

    # non-relational field, perform a deepcopy to ensure no mutable nonsense
    setattr(instance, accessor, deepcopy(value))

def _memoize_fork(reference, **kwargs):
    "Resets the specified instance relative to ``reference``"
    # popped so it does not get included in the config for the signal
    memo = kwargs.pop('memo', None)
    
    root = False

    # for every call, keep track of the reference and the instance being
    # acted on. this is used for recursive calls to related objects. this
    # ensures relationships that follow back up the tree are caught and are
    # merely referenced rather than traversed again.
    if memo is None:
        root = True
        memo = utils.Memo()
    elif memo.has(reference):
        return memo.get(reference)
    
    # initialize and memoize new instance
    instance = reference.__class__()
    instance._commits = utils.Commits(reference)    
    memo.add(reference, instance)

    # default configuration
    config = {
        'fields': None,
        'exclude': ['pk'],
        'deep': True,
        'commit': True,
        'strict': True,
        'conserve': []
    }

    # pop off and set any config params for signals
    for key in config.iterkeys():
        if kwargs.has_key(key):
            config[key] = kwargs.pop(key)
            
    kwargs['strict'] = config['strict']
    
    # pre-signal
    signals.pre_fork.send(sender=reference.__class__, reference=reference,
        instance=instance, config=config, root=root, **kwargs)
    
    # always exclude pk to create copies of related objects
    if 'exclude' in config:
        config['exclude'].append('pk')

    fields = config['fields']
    exclude = config['exclude']
    deep = config['deep']
    commit = config['commit']
    conserve = config['conserve']

    # no fields are defined, so get the default ones for shallow or deep
    if not fields:
        fields = utils._default_model_fields(reference, exclude=exclude, deep=deep, conserve=conserve, **kwargs)

    # add arguments for downstream use
    kwargs.update({'deep': deep})

    # iterate over each field and fork it!. nested calls will not commit,
    # until the recursion has finished
    for accessor in fields:
        _fork_field(reference, instance, accessor, conserve=conserve, memo=memo, **kwargs)

    # post-signal
    signals.post_fork.send(sender=reference.__class__, reference=reference,
        instance=instance, root=root, **kwargs)

    # as of now, this will only every be from a top-level call
    if commit:
        commit_model_object(instance, **kwargs)

    return instance

def fork_model_object(reference, **kwargs):
    """Creates a fork of the reference object. If an object is supplied, it
    effectively gets reset relative to the reference object.
    """
        
    return _memoize_fork(reference, **kwargs)