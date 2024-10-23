from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import User, Project, Employee, Shift, TimeEntry

class EmployeeAnalyticsTestCase(TestCase):
    def setUp(self):
        # Create a user for the project manager
        self.manager_user = User.objects.create_user(username='manager', password='password123')
        self.client.login(username='manager', password='password123')

        # Create a project with all required fields
        self.project = Project.objects.create(
            name='Test Project',
            description='This is a test project description.',
            start_date='2024-01-01',
            end_date='2024-12-31',
            created_by=self.manager_user
        )

        # Create employees
        self.employee1 = Employee.objects.create(
            user=self.create_user('user1', 'password'),  
            hourly_rate=15.00
        )
        self.employee2 = Employee.objects.create(
            user=self.create_user('user2', 'password'),
            hourly_rate=20.00
        )

        # Create a shift for the project
        self.shift1 = Shift.objects.create(
            project=self.project,
            start_time='09:00:00',
            end_time='17:00:00',
            date='2024-01-02'
        )

        # Add time entries for employees with timezone-aware datetime
        TimeEntry.objects.create(
            employee=self.employee1,
            shift=self.shift1,
            check_in=timezone.make_aware(timezone.datetime(2024, 1, 2, 9, 0, 0)),
            check_out=timezone.make_aware(timezone.datetime(2024, 1, 2, 17, 0, 0))  # Ensure check_out is set
        )
        TimeEntry.objects.create(
            employee=self.employee2,
            shift=self.shift1,
            check_in=timezone.make_aware(timezone.datetime(2024, 1, 2, 9, 30, 0)),
            check_out=timezone.make_aware(timezone.datetime(2024, 1, 2, 17, 0, 0))  # Ensure check_out is set
        )

    def create_user(self, username, password):
        """Helper method to create a user."""
        user = User.objects.create_user(username=username, password=password)
        return user

    def test_employee_created(self):
        """Test that the employee is created successfully."""
        self.assertIsNotNone(self.employee1)
        self.assertIsNotNone(self.employee2)

    def test_time_entries_created(self):
        """Test that time entries are created for employees."""
        self.assertEqual(TimeEntry.objects.count(), 2)

    def test_employee_analytics_view(self):
        """Test the employee analytics view."""
        response = self.client.get(reverse('employee_analytics'))  # Adjust the URL name as necessary
        self.assertEqual(response.status_code, 200)  # Check that the response is OK

    def test_calculate_payment(self):
        """Test the calculate_payment method of TimeEntry."""
        time_entry = TimeEntry.objects.get(employee=self.employee1)
        payment = time_entry.calculate_payment()
        self.assertGreaterEqual(payment, 0)  # Ensure the payment is not negative

