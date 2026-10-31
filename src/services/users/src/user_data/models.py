from django.db import models
from authentication.models import User

class UserProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profile_picture = models.FileField(upload_to='profile_pictures/', default='profile_pictures/default.jpg')
    online_status = models.BooleanField(default=False)
