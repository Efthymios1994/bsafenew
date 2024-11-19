from rest_framework import serializers
from .models import Customer, Technician, Appointment





#create your serializers here
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'address','email', 'phone']

class TechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technician
        fields = ['id', 'name', 'email', 'phone']


class AppointmentSerializer(serializers.ModelSerializer):
    technicians = serializers.PrimaryKeyRelatedField(queryset=Technician.objects.all(), many=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_name', 'customer', 'technicians', 'date',
            'start_time', 'end_time', 'service_type', 'additional_details', 'record_date'
        ]
        read_only_fields = ['record_date']

    def create(self, validated_data):
        # Extract technicians data from validated_data
        technicians_data = validated_data.pop('technicians', None)

        # Create the appointment instance
        appointment = Appointment.objects.create(**validated_data)

        # Assign technicians to the appointment if technicians_data is provided
        if technicians_data:
            appointment.technicians.set(technicians_data)

        return appointment

class TechnicianAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technician
        fields = ['id', 'name', 'email', 'phone','isSelected']

