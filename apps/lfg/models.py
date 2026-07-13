from django.db import models
from django.conf import settings

class LFGPost(models.Model):
    STATUS_CHOICES = [
        ('open','Open'),
        ('closed','Closed'),
    ]
    author = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='lfg_posts')
    game = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    description = models.TextField(blank=True)
    contact = models.CharField(max_length=100)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.game} - {self.author}"

class LFGResponse(models.Model):
    post = models.ForeignKey(LFGPost,on_delete=models.CASCADE,related_name='responses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('post','user')

    def __str__(self):
        return f'{self.user} - {self.post}'