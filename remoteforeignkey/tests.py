from django.test import TestCase
from django.db import models, IntegrityError

from remoteforeignkey.models import RemoteForeignKey

class Post(models.Model):
    body = models.TextField()
    flags = RemoteForeignKey('Flag')
    comments = RemoteForeignKey('Comment')

class Comment(models.Model):
    body = models.TextField()
    flags = RemoteForeignKey('Flag')

class Flag(models.Model):
    note = models.CharField(max_length=255)

class TestRemoteForeignKey(TestCase):
    def test_schema(self):
        pass

    def test_rfk(self):
        post = Post.objects.create(body="Life is good")
        c1 = Comment.objects.create(body="First")
        c2 = Comment.objects.create(body="Second")
        post.comments.add(c1)
        post.comments.add(c2)
        self.assertEquals(set(post.comments.all()), set([c1, c2]))

        post2 = Post.objects.create(body="This is fun")
        self.assertRaises(IntegrityError, lambda: post2.comments.add(c1))

        flag = Flag.objects.create(note="flag1")
        flag.post = post
        flag.save()

        # Unwanted, but expected feature: flag can apply to different types
        # without error.
        flag.comment = c1
        flag.save()


