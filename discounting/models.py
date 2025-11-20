from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.fields import DateField
from discounting.choices import ROLES


# Create your models here.
class Role:
    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=100, choices=ROLES, default='admin')
    description = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

class User(AbstractUser):
    username = models.CharField(max_length=15, blank=True)
    email =  models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15)
    created_on = DateField(auto_created=True,null=False)
    is_active = models.BooleanField(default=True)
    role = models.ForeignKey(Role,on_delete=models.SET_NULL,null=False)


    USERNAME_FIELD = 'email'
    def __str__(self):
        return self.email
class Contracts:
    buyer_id = models.ForeignKey(User, on_delete=models.SET_NULL(), null=False)
    supplier_id = models.ForeignKey(User, on_delete=models.SET_NULL(), null=False)
    amount = models.DecimalField(decimal_places=2)
    date_from = models.DateField(null=False)
    date_to = models.DateField(null=False)
    def __str__(self):
        return self.buyer_id.name
class Invoice:
    pass
class Payments:
     pass