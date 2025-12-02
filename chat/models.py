from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings
from django.utils import timezone


class CustomUser(AbstractUser):
    # Override the M2M fields from PermissionsMixin to avoid reverse-accessor
    # name clashes with the legacy `auth.User` model in the database.
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='customuser_set',
        related_query_name='customuser',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_user_set',
        related_query_name='customuser',
    )

    # Username is already unique by default, but we make it explicit
    username = models.CharField(
        max_length=150,
        unique=True,
        error_messages={
            'unique': "This username is already taken. Choose another one."
        }
    )

    # enforce unique email at the model level
    email = models.EmailField(unique=True)

    # Optional: add profile pic later
    # profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return self.username


class PrivateMessage(models.Model):
    """A simple model for 1-vs-1 private messages between users.

    Messages are immutable records storing sender, recipient, optional image and
    the message text. Use a deterministic group name in the consumer so both
    participants join the same channel group.
    """
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_private_messages',
        on_delete=models.CASCADE,
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_private_messages',
        on_delete=models.CASCADE,
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='private_images/', blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def to_dict(self):
        return {
            'id': self.id,
            'sender': self.sender.username,
            'recipient': self.recipient.username,
            'content': self.content,
            'image_url': self.image.url if self.image else None,
            'timestamp': self.timestamp.isoformat(),
            'read': self.read,
        }