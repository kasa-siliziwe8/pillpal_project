from django.db import models

class Clinic(models.Model):
    name = models.CharField(max_length=200)
    province = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name
