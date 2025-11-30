from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


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