from django.db import models, transaction
from forkit import utils, signals

def _commit_direct(instance, memo, **kwargs):
    """Recursively set all direct related object references to the
    instance object. Each downstream related object is saved before
    being set.
    """
    # get and clear to prevent infinite recursion
    relations = instance._commits.direct.items()
    instance._commits.direct = {}

    for accessor, value in relations:
        _memoize_commit(value, memo=memo, **kwargs)
        # save the object to get a primary key
        setattr(instance, accessor, value)

def _commit_related(instance, memo, **kwargs):
    relations = instance._commits.related.items()
    instance._commits.related = {}

    for accessor, value in relations:       
        # execute the commit cycle for these related objects,
        if type(value) is list:
            map(lambda rel: _memoize_commit(rel, memo=memo, **kwargs), value)
        elif isinstance(value, models.Model):
            _memoize_commit(value, memo=memo, **kwargs)

        setattr(instance, accessor, value)

def _memoize_commit(instance, **kwargs):
    if not hasattr(instance, '_commits'):
        return instance

    reference = instance._commits.reference

    root = False
    memo = kwargs.pop('memo', None)   

    # for every call, keep track of the reference and the instance being
    # acted on. this is used for recursive calls to related objects. this
    # ensures relationships that follow back up the tree are caught and are
    # merely referenced rather than traversed again.
    if memo is None:
        root = True
        memo = utils.Memo()
    elif memo.has(reference):       
        return memo.get(reference)

    memo.add(reference, instance)

    # pre-signal
    signals.pre_commit.send(sender=reference.__class__, reference=reference,
        instance=instance, root=root, **kwargs)

    # commit all dependencies first, save it, then traverse dependents
    _commit_direct(instance, memo=memo, **kwargs)
    instance.save()
    _commit_related(instance, memo=memo, **kwargs)   

    # post-signal
    signals.post_commit.send(sender=reference.__class__, reference=reference,
        instance=instance, root=root, **kwargs)

    return instance

@transaction.commit_on_success
def commit_model_object(instance, **kwargs):
    "Recursively commits direct and related objects."
    return _memoize_commit(instance, **kwargs)
