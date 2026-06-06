import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.


class Property(models.Model):
    TYPE = [
        ('HOUSE', 'House'),
        ('VILLA', 'Villa'),
        ('APARTMENT', 'Apartment'),
        ('COMMERCIAL', 'Commercial'),
    ]

    STATUS = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    bedroom = models.IntegerField(null=True, blank=True)
    bathroom = models.IntegerField(null=True, blank=True)
    area = models.CharField(max_length=255, null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    cover_image = models.ImageField(upload_to='property_gallery/',blank=True)
    latitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    type = models.CharField(max_length=255, choices=TYPE, default="HOUSE")
    status = models.CharField(max_length=255, choices=STATUS, default='ACTIVE')
    verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class Amenity(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='amenities')
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name



class Gallery(models.Model):
    TYPE = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    ]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='galleries')
    type = models.CharField(max_length=255, choices=TYPE, default="IMAGE")
    file = models.FileField(upload_to='property_gallery/')

    def __str__(self):
        return f"{self.property.name} - {self.type}"
    
    

class Review(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.property.name} - {self.user.username}"

    

