from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from forkit.models import ForkableModel

class Tag(ForkableModel):
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return u'{0}'.format(self.name)
    
class Author(ForkableModel):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __unicode__(self):
        return u'{0} {1} ({2})'.format(self.first_name, self.last_name, self.pk)


class Blog(ForkableModel):
    name = models.CharField(max_length=50)
    author = models.OneToOneField(Author)

    def __unicode__(self):
        return u'{0}'.format(self.name)

class Comment(ForkableModel):
    text = models.CharField(max_length=150)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')


class Post(ForkableModel):
    title = models.CharField(max_length=50)
    # intentionally left off the related_name attr
    blog = models.ForeignKey(Blog)
    authors = models.ManyToManyField(Author, related_name='posts')
    
    comments = generic.GenericRelation(Comment)
    # intentionally left off the related_name attr
    tags = models.ManyToManyField(Tag)

    def __unicode__(self):
        return u'{0} ({1})'.format(self.title, self.pk)
    
class A(ForkableModel):
    title = models.CharField(max_length=50)
    d = models.ForeignKey('D', null=True)

    def __unicode__(self):
        return u'{0}'.format(self.title)


class B(ForkableModel):
    title = models.CharField(max_length=50)

    def __unicode__(self):
        return u'{0}'.format(self.title)


class C(ForkableModel):
    title = models.CharField(max_length=50)
    a = models.ForeignKey(A, null=True)
    b = models.ForeignKey(B, null=True)

    def __unicode__(self):
        return u'{0}'.format(self.title)


class D(ForkableModel):
    title = models.CharField(max_length=50)

    def __unicode__(self):
        return u'{0}'.format(self.title)

