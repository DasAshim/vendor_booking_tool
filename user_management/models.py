import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractBaseUser


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError('The email must be set')
        user = self.model(email=email, **extra_fields)
        user.save()
        return user

    def create_superuser(self, email, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        # extra_fields.setdefault('is_active', True)
        return self.create_user(email, **extra_fields)

# Create your models here
class User(AbstractBaseUser):
    """
    Create and save a User Details.
    """
    username = None
    is_staff = None
    date_joined = None
    is_superuser = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=15)
    last_name = models.CharField(max_length=15, null=True)
    organisation_name = models.CharField(max_length=15, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    country_code = models.CharField(max_length=4, blank=True, null=True)
    status = models.BooleanField(default=True, db_column='is_active')
    is_deleted = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    is_application = models.BooleanField(default=False)
    announcement_read_flag = models.IntegerField(default=1)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True, blank=True)
    modified_on = models.DateTimeField(null=True)
    modified_by = models.PositiveIntegerField(null=True, blank=True)
    auth0_id = models.CharField(null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def is_active(self):
        return self.status

    class Meta:
        db_table = "user"
        ordering = ['first_name']
        verbose_name = "User"
        verbose_name_plural = "Users"


TOKEN_TYPES = (
    ("APP_TOKEN", "APP_TOKEN"),
    ("LOGIN_TOKEN", "LOGIN_TOKEN"),

)


class TokenModule(models.Model):
    user_id = models.OneToOneField(User, on_delete=models.DO_NOTHING, null=True,
                                   related_name="token_user_id", db_column="user_id")
    expiry_days = models.PositiveIntegerField()
    expiry_time = models.DateTimeField(null=True)
    type = models.CharField(max_length=255, choices=TOKEN_TYPES, default="APP_TOKEN", db_column="TOKEN_TYPE")
    primary_token = models.CharField(max_length=120, null=True, blank=True)
    secondary_token = models.CharField(max_length=120, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)
    modified_on = models.DateTimeField(null=True, blank=True)
    modified_by = models.PositiveIntegerField(null=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-created_on']
        db_table = 'TOKEN_MANAGEMENT'
