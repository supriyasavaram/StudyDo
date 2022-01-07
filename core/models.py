from django.db import models
from django.db.models.deletion import CASCADE
from django.http import HttpResponseRedirect
from django.shortcuts import render
#from gdstorage.storage import GoogleDriveStorage
from storages.backends.gcloud import GoogleCloudStorage
from django.forms import ModelForm
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator, RegexValidator
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
#from .forms import ModelFormWithFileField

storage = GoogleCloudStorage()

# Create your models here.
class Temp(models.Model):
    title = models.CharField(max_length = 100)
    thought = models.CharField(max_length = 400)
    


    def __str__(self):
        return self.title + ": " + self.thought


class Calendar(models.Model):
    user = models.CharField(max_length = 100)
    calendarId = models.CharField(max_length = 100)

    def __str__(self):
        return self.calendarId


class Course(models.Model):
    alphabetic = RegexValidator(r'^[a-zA-Z]+$', 'Only alphabetic characters are allowed.')

    dept = models.CharField(max_length=4, validators=[MinLengthValidator(2), alphabetic])
    num = models.IntegerField(validators=[MinValueValidator(1000), MaxValueValidator(9999)])
    
    class Meta:
        unique_together = (("dept", "num"),)    

    def __str__(self):
        return "" + self.dept + " " + str(self.num)
    
    def slug(self):
        return '-'.join((slugify(self.dept), slugify(self.num)))


class Profile(models.Model):
    user = models.CharField(max_length = 100)
    refresh_token = models.CharField(max_length = 200)
    courses = models.ManyToManyField(Course)
    user = models.OneToOneField(User, on_delete=CASCADE)

# class User(models.Model):
#     user = models.CharField(max_length = 100)
#     refresh_token = models.CharField(max_length = 200)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


# Source: https://www.youtube.com/watch?v=Zx09vcYq1oc
class Upload(models.Model):
    title = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING)
    upload_file = models.FileField(upload_to='files/')
    user = models.CharField(max_length = 100)

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        self.upload_file.delete()
        super().delete(*args, **kwargs)
