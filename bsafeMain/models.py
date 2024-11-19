from django.db import models
from django.core.exceptions import ValidationError
from datetime import time, datetime, date

# Create your models here.
def validate_business_hours(value):
    """Ensure the time is within 9 AM to 5 PM."""
    if not (datetime.strptime("09:00", "%H:%M").time() <= value <= datetime.strptime("17:00", "%H:%M").time()):
        raise ValidationError("Time must be within business hours (9 AM to 5 PM).")

def validate_time_slot(value):
    """Ensure the time is at 30-minute increments."""
    if value.minute % 30 != 0 or value.second != 0 or value.microsecond != 0:
        raise ValidationError("Time must be in 30-minute increments.")

class Customer(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name



class Technician(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)


    def is_available(self, date, start_time, end_time):
        """Check if the technician is available for the given date and time slot."""
        appointments = self.appointments.filter(date=date)
        for appointment in appointments:
            if not (appointment.end_time <= start_time or appointment.start_time >= end_time):
                return False
        return True


class Appointment(models.Model):
    appointment_name = models.CharField(max_length=255)
    customer = models.ForeignKey(
        'Customer', on_delete=models.CASCADE, related_name='appointments'
    )
    technicians = models.ManyToManyField(
        'Technician', related_name='appointments'
    )  # Updated to ManyToManyField to allow multiple technicians
    date = models.DateField()
    start_time = models.TimeField(
        validators=[validate_business_hours, validate_time_slot]
    )
    end_time = models.TimeField(
        validators=[validate_business_hours, validate_time_slot]
    )

    SERVICE_CHOICES = [
        ('installation', 'Installation'),
        ('service', 'Service')
    ]
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    additional_details = models.TextField(blank=True, null=True)
    record_date = models.DateField(auto_now_add=True)

    def clean(self):
        """Custom validation for the Appointment model."""
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        # Ensure the duration is in 30-minute increments
        duration = (
                datetime.combine(date.min, self.end_time) - datetime.combine(date.min, self.start_time)
        ).total_seconds()
        if duration % 1800 != 0:
            raise ValidationError("Appointment duration must be in 30-minute increments.")

    def __str__(self):
        return f"{self.appointment_name} for {self.customer} with technicians on {self.date} from {self.start_time} to {self.end_time}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F('end_time')),
                name='start_time_before_end_time'
            ),
            models.UniqueConstraint(
                fields=['date', 'start_time', 'end_time'],
                name='unique_appointment_time'
            ),
        ]




