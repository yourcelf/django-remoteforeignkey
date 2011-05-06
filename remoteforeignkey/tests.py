from django.test import TestCase
from django.db import models, IntegrityError

from remoteforeignkey.models import RemoteForeignKey

class Flag(models.Model):
    reason = models.CharField(max_length=255)

class Post(models.Model):
    body = models.TextField()
    flags = RemoteForeignKey(Flag)

class Comment(models.Model):
    body = models.TextField()
    flags = RemoteForeignKey(Flag)

class TestRemoteForeignKey(TestCase):
    def test_rfk(self):
        post = Post.objects.create(body="Life is good")
        self.assertEquals(list(post.flags.all()), [])

        comment = Comment.objects.create(body="This is fun")
        self.assertEquals(list(comment.flags.all()), [])

        flag = Flag.objects.create(reason="My...")
        self.assertEquals(flag.post, None)
        self.assertEquals(flag.comment, None)

        post.flags.add(flag)
        self.assertEquals(list(post.flags.all()), [flag])
        self.assertEquals(list(comment.flags.all()), [])

        # refresh from db, to get the result of adding the flag to the m2m.
        flag = Flag.objects.all()[0]
        self.assertEquals(flag.comment, None)
        self.assertEquals(flag.post, post)
        # test cache.
        self.assertEquals(flag.post, post)

        post2 = Post.objects.create(body="I'm feeling fat and sassy")

        # Change the post the flag is pointing to.
        flag.post = post2
        flag.save()
        self.assertEquals(list(post2.flags.all()), [flag])
        self.assertEquals(list(post.flags.all()), [])

        # Ensure uniqueness.
        self.assertRaises(IntegrityError, lambda: post.flags.add(flag))

        # An expected, though not necessarily wanted side effect: uniqueness
        # doesn't hold across separate models.
        comment.flags.add(flag)
        self.assertEquals(list(comment.flags.all()), list(post2.flags.all()))
