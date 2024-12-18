from django.shortcuts import render
from rest_framework import viewsets
from .models import Customer, Technician, Appointment
from .serializers import CustomerSerializer, TechnicianSerializer, AppointmentSerializer
from rest_framework.permissions import IsAuthenticated
from bsafe.permissions import IsSuperUser
from rest_framework import status
from datetime import datetime,time,timedelta
from collections import defaultdict
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework.response import Response

# Create your views here.
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [SearchFilter]  # Add SearchFilter
    search_fields = ['name', 'email', 'address', 'phone']  # Define searchable fields

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        query = request.query_params.get('q', None)
        customer_id = request.query_params.get('customer_id', None)

        customers = Customer.objects.all()

        if query:
            customers = customers.filter(
                Q(name__icontains=query) |
                Q(email__icontains=query) |
                Q(address__icontains=query) |
                Q(phone__icontains=query)
            )

        if customer_id:
            customers = customers.filter(id=customer_id)

        serializer = self.get_serializer(customers, many=True)
        return Response(serializer.data)


class TechnicianViewSet(viewsets.ModelViewSet):
    """
    A viewset that provides the standard actions for Technician model
    """
    queryset = Technician.objects.all()
    serializer_class = TechnicianSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        query = request.query_params.get('q', None)

        technicians = Technician.objects.all()

        if query:
            technicians = technicians.filter(
                Q(name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )

        serializer = self.get_serializer(technicians, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='available')
    def available(self, request):
        date_str = request.query_params.get('date')
        start_time_str = request.query_params.get('start_time')
        end_time_str = request.query_params.get('end_time')
    
        # Check for missing parameters
        if not date_str or not start_time_str or not end_time_str:
            return Response(
                {"error": "Please provide date, start_time, and end_time."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        try:
            # Debugging: Log the incoming parameters
            print(f"Received date: {date_str}, start_time: {start_time_str}, end_time: {end_time_str}")
            
            # Parse date and time
            date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str.strip(), "%H:%M:%S").time()
            end_time = datetime.strptime(end_time_str.strip(), "%H:%M:%S").time()
        except ValueError as e:
            # Log error for debugging
            print(f"Parsing error: {e}")
            return Response(
                {"error": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM:SS for time."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # Logic to find available technicians
        available_technicians = [
            technician for technician in Technician.objects.all()
            if technician.is_available(date, start_time, end_time)
        ]
    
        # Serialize the response
        serializer = self.get_serializer(available_technicians, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='details')
    def technician_details(self, request, pk=None):
        try:
            technician = self.get_queryset().get(pk=pk)
        except Technician.DoesNotExist:
            return Response(
                {"detail": "Technician not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(technician)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='by-id')
    def technician_by_id(self, request, pk=None):
        """
        Custom action to return technician data by their ID.
        """
        try:
            # Fetch technician by primary key (ID)
            technician = self.get_queryset().get(pk=pk)
        except Technician.DoesNotExist:
            return Response(
                {"detail": "Technician not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(technician)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='by-ids')
    def get_by_ids(self, request):
        """
        Custom action to return data for a list of technician IDs.
        """
        technician_ids = request.data.get('technician_ids', None)

        if not technician_ids or not isinstance(technician_ids, list):
            return Response(
                {"detail": "Please provide a list of technician IDs as 'technician_ids' in the request body."},
                status=status.HTTP_400_BAD_REQUEST
            )

        technicians = self.queryset.filter(id__in=technician_ids)

        if not technicians.exists():
            return Response(
                {"detail": "No technicians found for the provided IDs."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(technicians, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='available-excluding-appointment')
    def available_excluding_appointment(self, request):
        """
        Return technicians available for the given date and time range,
        excluding conflicts with all appointments except the one specified by appointment_id.
        """
        date_str = request.query_params.get('date')
        start_time_str = request.query_params.get('start_time')
        end_time_str = request.query_params.get('end_time')
        appointment_id = request.query_params.get('appointment_id')
    
        # Validate required parameters
        if not date_str or not start_time_str or not end_time_str or not appointment_id:
            return Response(
                {"error": "Please provide 'date', 'start_time', 'end_time', and 'appointment_id'."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # Parse and validate date and time
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
            end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
        except ValueError:
            return Response(
                {"error": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM:SS for time."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # Validate appointment_id
        try:
            appointment_id = int(appointment_id)
        except ValueError:
            return Response(
                {"error": "Invalid 'appointment_id'. It must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # Fetch appointments excluding the specified appointment ID
        conflicting_appointments = Appointment.objects.filter(
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(id=appointment_id)
    
        # Get technicians who are busy during the specified time range
        busy_technician_ids = conflicting_appointments.values_list('technicians__id', flat=True).distinct()
    
        # Get technicians who are not in the busy technician list
        available_technicians = Technician.objects.exclude(id__in=busy_technician_ids)
    
        # Serialize and return the available technicians
        serializer = self.get_serializer(available_technicians, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]

    def get_queryset(self):
        """
        Optionally restricts the returned appointments based on query parameters.
        """
        queryset = super().get_queryset()
        technician_id = self.request.query_params.get('technician_id')
        date = self.request.query_params.get('date')
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')
        search = self.request.query_params.get('search')

        if technician_id:
            queryset = queryset.filter(technicians__id=technician_id)
        if date:
            queryset = queryset.filter(date=date)
        if start_time and end_time:
            queryset = queryset.filter(start_time__gte=start_time, end_time__lte=end_time)
        if search:
            queryset = queryset.filter(
                Q(appointment_name__icontains=search) |
                Q(date__icontains=search) |  # Matches the `date` field
                Q(technicians__name__icontains=search)  # Matches technician names
            ).distinct()  # Avoid duplicate results due to ManyToMany relationship

        return queryset

    @action(detail=False, methods=['get'], url_path='filtered')
    def filtered_appointments(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-date')
    def appointments_by_date(self, request):
        date = request.query_params.get('date')

        if not date:
            return Response(
                {"detail": "Please provide a 'date' query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            appointments = self.queryset.filter(date=date)
            print(self.queryset.filter(date=date))
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Please use 'YYYY-MM-DD'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='appointments-by-technician')
    def appointments_by_technician(self, request):
        date = request.query_params.get('date')

        if not date:
            return Response(
                {"detail": "Please provide a 'date' query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            appointments = self.queryset.filter(date=date)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Please use 'YYYY-MM-DD'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        grouped_appointments = defaultdict(list)
        for appointment in appointments:
            for technician in appointment.technicians.all():
                grouped_appointments[technician.id].append(appointment)

        technicians = Technician.objects.all()

        response_data = []
        for technician in technicians:
            response_data.append({
                "technician_id": technician.id,
                "technician_name": technician.name,
                "appointments": AppointmentSerializer(grouped_appointments.get(technician.id, []), many=True).data
            })

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='by-id')
    def appointment_by_id(self, request):
        """
        Custom action to return appointment data by its ID.
        """
        appointment_id = request.query_params.get('id')

        if not appointment_id:
            return Response(
                {"detail": "Please provide an 'id' query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch the appointment by ID
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"detail": f"Appointment with ID {appointment_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize and return the appointment data
        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='delete-appointment')
    def delete_appointment(self, request):
        """
        Custom action to delete an appointment by its ID.
        """
        appointment_id = request.query_params.get('id')

        if not appointment_id:
            return Response(
                {"detail": "Please provide an 'id' query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch the appointment by ID
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response(
                {"detail": f"Appointment with ID {appointment_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete the appointment
        appointment.delete()

        return Response(
            {"detail": f"Appointment with ID {appointment_id} has been deleted."},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='availability-by-day')
    def availability_by_day(self, request):
        """
        Custom action to get available and unavailable slots for given technicians on a specific date.
        """
        date_str = request.query_params.get('date')
        technician_ids = request.query_params.get('technician_ids')  # Accept comma-separated list

        if not date_str or not technician_ids:
            return Response(
                {"error": "Please provide both 'date' and 'technician_ids' as query parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse technician IDs from the comma-separated string
        try:
            technician_ids = [int(id.strip()) for id in technician_ids.strip('[]').split(',')]
        except ValueError:
            return Response(
                {"error": "Invalid format for 'technician_ids'. Use a comma-separated list of integers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initialize 30-minute slots from 9:00 AM to 5:00 PM
        start_time = time(9, 0)
        end_time = time(17, 0)
        all_slots = []
        current_time = start_time
        while current_time < end_time:
            next_time = (datetime.combine(date, current_time) + timedelta(minutes=30)).time()
            all_slots.append((current_time.strftime('%H:%M:%S'), next_time.strftime('%H:%M:%S')))
            current_time = next_time

        # Find unavailable slots based on appointments
        unavailable_slots = set()
        for technician_id in technician_ids:
            appointments = Appointment.objects.filter(
                technicians__id=technician_id,
                date=date
            )
            for appointment in appointments:
                unavailable_slots.add((appointment.start_time.strftime('%H:%M:%S'),
                                       appointment.end_time.strftime('%H:%M:%S')))

        # Determine available slots
        available_slots = [slot for slot in all_slots if slot not in unavailable_slots]

        # Response
        return Response(
            {
                "date": date_str,
                "technician_ids": technician_ids,
                "available_slots": available_slots,
                "unavailable_slots": list(unavailable_slots)
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='by-customer')
    def appointments_by_customer(self, request):
        """
        Custom action to return all appointments for a specific customer,
        with optional search functionality.
        """
        customer_id = request.query_params.get('customer_id', None)
        search = request.query_params.get('search', None)  # New search parameter

        if not customer_id:
            return Response(
                {"detail": "Please provide a 'customer_id' query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            appointments = self.queryset.filter(customer__id=customer_id)

            if search:
                # Apply search filters
                appointments = appointments.filter(
                    Q(appointment_name__icontains=search) |
                    Q(date__icontains=search) |
                    Q(technicians__name__icontains=search)
                ).distinct()

        except ValueError:
            return Response(
                {"detail": "Invalid customer ID."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='availability-by-day-exclude')
    def availability_by_day_exclude(self, request):
        """
        Custom action to get available and unavailable slots for given technicians on a specific date,
        excluding a specific appointment ID from consideration.
        """
        date_str = request.query_params.get('date')
        technician_ids = request.query_params.get('technician_ids')  # Accept comma-separated list
        appointment_id = request.query_params.get('appointment_id')  # Exclude this appointment ID

        if not date_str or not technician_ids:
            return Response(
                {"error": "Please provide 'date', 'technician_ids', and optionally 'appointment_id' as query parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse technician IDs from the comma-separated string
        try:
            technician_ids = [int(id.strip()) for id in technician_ids.strip('[]').split(',')]
        except ValueError:
            return Response(
                {"error": "Invalid format for 'technician_ids'. Use a comma-separated list of integers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initialize 30-minute slots from 9:00 AM to 5:00 PM
        start_time = time(9, 0)
        end_time = time(17, 0)
        all_slots = []
        current_time = start_time
        while current_time < end_time:
            next_time = (datetime.combine(date, current_time) + timedelta(minutes=30)).time()
            all_slots.append((current_time.strftime('%H:%M:%S'), next_time.strftime('%H:%M:%S')))
            current_time = next_time

        # Find unavailable slots based on appointments, excluding the given appointment ID
        unavailable_slots = set()
        for technician_id in technician_ids:
            appointments = Appointment.objects.filter(
                technicians__id=technician_id,
                date=date
            )
            if appointment_id:
                try:
                    appointments = appointments.exclude(id=int(appointment_id))
                except ValueError:
                    return Response(
                        {"error": "Invalid format for 'appointment_id'. It should be an integer."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            for appointment in appointments:
                unavailable_slots.add((appointment.start_time.strftime('%H:%M:%S'),
                                       appointment.end_time.strftime('%H:%M:%S')))

        # Determine available slots
        available_slots = [slot for slot in all_slots if slot not in unavailable_slots]

        # Response
        return Response(
            {
                "date": date_str,
                "technician_ids": technician_ids,
                "available_slots": available_slots,
                "unavailable_slots": list(unavailable_slots)
            },
            status=status.HTTP_200_OK
        )

