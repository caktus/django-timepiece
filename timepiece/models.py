from django.db import models
from django.contrib.auth.models import User

class MongoAttachment(models.Model):
    file_id = models.CharField(max_length=24) # str of object id
    filename = models.CharField(max_length=128)
    upload_time = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User)
    description = models.TextField(blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
