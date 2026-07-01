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
        ('AVAILABLE', 'Available'),
        ('BOOKED', 'Booked'),
        ('CLOSED', 'Closed'),
        
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
    type = models.CharField(max_length=255, choices=TYPE, default="HOUSE")
    status = models.CharField(max_length=255, choices=STATUS, default='ACTIVE')
    verified = models.BooleanField(default=True)
    hosted_by = models.CharField(max_length=255, null=True, blank=True)
    whatsapp = models.CharField(max_length=15, null=True, blank=True)
    sea_view = models.BooleanField(default=False)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_daily = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    discount = models.IntegerField(default=0)

    @property
    def price(self):
        return self.price_daily or self.price_monthly or 0.0

    @price.setter
    def price(self, value):
        self.price_daily = value

    def __str__(self):
        return self.name


class Weekend(models.Model):
    WEEKEND = [
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='weekend_dates')
    weekend = models.JSONField(blank=True, default=list, choices=WEEKEND)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.property.name + " - " + str(self.weekend)



class Vacetions(models.Model):
    MONTHS = [
        ('JAN', 'January'),
        ('FEB', 'February'),
        ('MAR', 'March'),
        ('APR', 'April'),
        ('MAY', 'May'),
        ('JUN', 'June'),
        ('JUL', 'July'),
        ('AUG', 'August'),
        ('SEP', 'September'),
        ('OCT', 'October'),
        ('NOV', 'November'),
        ('DEC', 'December'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='vacations')
    month = models.JSONField(blank=True, default=list, choices=MONTHS)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.property.name + " - " + str(self.month)



class OtherCharges(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='other_charges')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.property.name + " - " + self.name + " : " + str(self.price)



class AddOnsPrice(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='add_ons_prices')
    service = models.CharField(max_length=255)
    price = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.property.name + " - " + self.service + " : " + str(self.price)


class Amenity(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='amenities')
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Activity(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='activities')
    name = models.CharField(max_length=255)
    details = models.TextField(null=True, blank=True)

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

    

class Favourites(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Favourite for {self.property.name} by {self.user.username}"
    
    class Meta:
        unique_together = ('user', 'property')
        verbose_name_plural = "Favourites"



class Reports(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255)
    description = models.TextField()
    response = models.TextField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolve_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report for {self.property.name} by {self.user.username}"

    class Meta:
        verbose_name_plural = "Reports"

    