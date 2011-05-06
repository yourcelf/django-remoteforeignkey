django-remoteforeignkey
=======================

Django offers a built in many-to-one solution -- ``ForeignKey``.  But it
doesn't offer a comparable one-to-many, where you put the relation on the
"many" side.  ``RemoteForeignKey`` does this.

It's useful for cases where you want a one-to-many relationship, but don't want
to or can't modify the receiving model.  You can think of it as a nicer
alternative to generic relations when you are writing reusable apps.

As an example, suppose you have a simple blog site with Comments and Flags,
which call for moderator attention to a particular piece comment.  The
relationship between the comment and Flag is a "one-to-many" relationship: one
"Comment" could have many Flags, but each Flag has only one Comment.  To
structure this using a ``ForeignKey`` type, you'd have to write your models
like this::

    class Comment(models.Model):
        body = models.TextField()

    class Flag(models.Model):
        reason = models.CharField(max_length=255)
        comment = models.ForeignKey(Comment)

But since flagging of content is such a common pattern, we might want to
encapsulate that as a reusable app that could be used for any arbitrary site
content (say, a Post).  Each time we add a new type of content, we'd have to
modify the definition of Flag to add a new ForeignKey.  What we really want
is a "reversed" ForeignKey, where we put the definition on the "many" side
instead of on the "one" side.  That's what ``RemoteForeignKey`` does::

    from remoteforeignkey.models import RemoteForeignKey

    class Post(models.Model):
        body = models.TextField()
        flags = RemoteForeignKey(Flag)

How do we do make this work?  Under the hood, we use a many-to-many relation,
with a unique constraint on the receiving model.  And we add some syntactic
sugar so that the relation acts as a "-to-one" on the receiving side::

    >>> flag1 = Flag.objects.create(reason="It's terrible!")
    >>> flag2 = Flag.objects.create(reason="It's great!")
    >>> post = Post.objects.create(body="Good times")
    >>> post.flags.add(flag1)
    >>> flag1.post
    post
    >>> flag2.post
    None
    >>> flag2.post = post
    >>> post.flags.all()
    [<Flag: "It's terrible!">, <Flag: "It's great!">]

This is obviously less efficient than a regular ForeignKey, but it buys us
semantic clarity and reusability, and is a fair bit better than previous
generic relation implementations, so in many circumstances it's worth it.

Installation
------------

Install with pip::

    pip install -e git+http://github.com/yourcelf/django-remoteforeignkey.git#egg=remoteforeignkey

Testing
-------

Tests included.  Test in a django project with::

    python manage.py test remoteforeignkey
