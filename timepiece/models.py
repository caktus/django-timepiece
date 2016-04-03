from django.db import models
from django.contrib.auth.models import User

import boto
from project_toolbox_main import settings

class MongoAttachment(models.Model):
    file_id = models.CharField(max_length=24) # str of object id
    filename = models.CharField(max_length=128)
    upload_time = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User)
    description = models.TextField(blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

class AwsAttachment(models.Model):
    bucket = models.CharField(max_length=64, default='aaceng-firmbase')
    file_id = models.CharField(max_length=24)
    uuid = models.TextField() # AWS S3 uuid
    filename = models.CharField(max_length=128)
    upload_time = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User)
    description = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def get_download_url(self):
        conn = boto.connect_s3(settings.AWS_UPLOAD_CLIENT_KEY,
            settings.AWS_UPLOAD_CLIENT_SECRET_KEY)
        bucket = conn.get_bucket(self.bucket)
        s3_file_path = bucket.get_key(self.uuid)
        url = s3_file_path.generate_url(expires_in=15) # expiry time is in seconds
        return url
