from django.shortcuts import render
from rest_framework import viewsets
from .models import Customer, Technician, Appointment
from .serializers import CustomerSerializer, TechnicianSerializer, AppointmentSerializer
from rest_framework.permissions import IsAuthenticated
from bsafe.permissions import IsSuperUser
from rest_framework import status
from datetime import datetime
from collections import defaultdict

# Create your views here.
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

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

        if not date_str or not start_time_str or not end_time_str:
            return Response(
                {"error": "Please provide date, start_time, and end_time."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
            end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
        except ValueError:
            return Response(
                {"error": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM:SS for time."},
                status=status.HTTP_400_BAD_REQUEST
            )

        available_technicians = [
            technician for technician in Technician.objects.all()
            if technician.is_available(date, start_time, end_time)
        ]

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
                Q(customer__name__icontains=search) |
                Q(customer__address__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(customer__phone__icontains=search) |
                Q(appointment_name__icontains=search)
            )

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

