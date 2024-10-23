from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login,authenticate,logout
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from .forms import *
from datetime import datetime, timedelta
import calendar
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, F
from django.utils.dateparse import parse_date
import csv
from django.http import HttpResponse
from collections import defaultdict
from decimal import Decimal

from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.utils.encoding import force_str,force_bytes
from .utils import email_verification_token


from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode

from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator as email_verification_token

from .utils import email_verification_token
from django.contrib.auth.models import User
from .tokens import email_verification_token
from django.urls import reverse
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db.models import Q  
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


def get_shift_details(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    data = {
        'start_time': shift.start_time.strftime('%H:%M'), 
        'end_time': shift.end_time.strftime('%H:%M'),     
        'shift_type': shift.shift_type,                    
    }
    return JsonResponse(data)

@login_required
def dashboard(request):
    if request.user.is_staff:  
        projects = Project.objects.all()
        shifts = Shift.objects.all()

        # Get the search query for availability
        query = request.GET.get('q')
        if query:
            # Filter employees based on the search query (availability field)
            employees = Employee.objects.filter(availability__icontains=query)
            print(f"Manager is searching employees by availability: {query}")
        else:
            employees = Employee.objects.all()

        return render(request, 'Escheduler/dashboard.html', {
            'projects': projects,
            'shifts': shifts,
            'employees': employees,
            'is_manager': True
        })

    else:  # Employee view
        # Get or create the employee record
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            employee = Employee.objects.create(user=request.user)

        # Handle form submission for availability
        if request.method == 'POST':
            form = AvailabilityForm(request.POST, instance=employee)
            if form.is_valid():
                form.save()
                return redirect('dashboard')  
        else:
            form = AvailabilityForm(instance=employee)  

        # Fetch the employee's shifts
        shifts = Shift.objects.filter(employees=employee)

        # Create a mapping of shift ID to time entry for easy access
        time_entries = TimeEntry.objects.filter(employee=employee)
        shift_time_entries = {entry.shift.id: entry for entry in time_entries}

        # Add time entry information to shifts for check-in/out logic
        for shift in shifts:
            shift.time_entry = shift_time_entries.get(shift.id)  
        today = timezone.now().date()

        return render(request, 'Escheduler/dashboard.html', {
            'shifts': shifts,
            'employee': employee,
            'form': form,  
            'is_manager': False,
            'today': today 
        })


@login_required
def submit_shift_report(request):
    if request.method == 'POST':
        shift_id = request.POST['shift_id']
        report_document = request.FILES.get('report_document')

        shift = get_object_or_404(Shift, id=shift_id)

        if report_document:
            shift.report_document = report_document
            shift.save()
            messages.success(request, "Report submitted successfully.")
        else:
            messages.error(request, "Please upload a report.")

        return redirect('dashboard')  

@login_required
def employee_analytics(request):
    # Get date range from request (optional)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    employees = Employee.objects.all()
    analytics_data = []

    for employee in employees:
        # Filter time entries within the specified date range
        time_entries = TimeEntry.objects.filter(employee=employee)

        if start_date:
            time_entries = time_entries.filter(check_in__date__gte=parse_date(start_date))
        if end_date:
            time_entries = time_entries.filter(check_in__date__lte=parse_date(end_date))

        total_hours_worked = sum([entry.duration().total_seconds() for entry in time_entries if entry.duration()], 0) / 3600
        total_overtime_hours = sum([entry.calculate_overtime() for entry in time_entries])

        
        total_payment = sum([entry.calculate_payment() for entry in time_entries], Decimal(0))

        analytics_data.append({
            'employee': employee,
            'total_hours_worked': total_hours_worked,
            'total_overtime_hours': total_overtime_hours,
            'total_payment': float(total_payment),  
        })

    return render(request, 'Escheduler/employee_analytics.html', {
        'analytics_data': analytics_data,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def export_analytics_csv(request):
    # Get all employee analytics data
    employees = Employee.objects.all()

    # Create the HttpResponse object with the CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employee_analytics.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee', 'Total Hours Worked', 'Overtime Hours', 'Total Payment'])

    for employee in employees:
        time_entries = TimeEntry.objects.filter(employee=employee)
        total_hours_worked = sum([entry.duration().total_seconds() for entry in time_entries if entry.duration()], 0) / 3600
        total_overtime_hours = sum([entry.calculate_overtime() for entry in time_entries])
        total_payment = sum([entry.calculate_payment() for entry in time_entries])

        writer.writerow([employee.user.username, total_hours_worked, total_overtime_hours, total_payment])

    return response


@login_required
def create_project(request):
    if request.method == 'POST':
        name = request.POST.get('project_name')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

     
        if name and description and start_date and end_date:
            if end_date < start_date:
                return render(request, 'Escheduler/create_project.html', {'error': 'End date must be after start date.'})
            
            try:
                project = Project.objects.create(
                    name=name,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    created_by=request.user
                )
                return redirect('project_list')
            except ValidationError as e:
                return render(request, 'Escheduler/create_project.html', {'error': e.message})

        return render(request, 'Escheduler/create_project.html', {'error': 'All fields are required.'})

    return render(request, 'Escheduler/create_project.html')

@login_required
def project_list(request):
    projects = Project.objects.filter(created_by=request.user)
    return render(request, 'Escheduler/project_list.html', {'projects': projects})

from collections import defaultdict

from collections import defaultdict
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    shifts = Shift.objects.filter(project=project).order_by('date', 'start_time')
    employees = Employee.objects.all()

    # Get the date range from the query parameters
    date_range = request.GET.get('date_range', '7')  # Default to last 7 days

    # Calculate the start date based on the selected range
    if date_range == 'all':
        start_date = project.start_date
    else:
        days = int(date_range)
        start_date = timezone.now().date() - timedelta(days=days)

    # Get all time entries for the project within the date range
    attendance_entries = TimeEntry.objects.filter(
        shift__project=project,
        shift__date__gte=start_date
    ).select_related('shift', 'employee', 'employee__user').order_by('-shift__date', 'shift__start_time')

    # Collect time entries for each employee and shift
    time_entries = {}
    for shift in shifts:
        shift_entries = {}
        for employee in shift.employees.all():
            entries = TimeEntry.objects.filter(employee=employee, shift=shift).order_by('-check_in')
            if entries.exists():
                latest_entry = entries.first()
                shift_entries[employee.id] = {
                    'check_in': latest_entry.check_in,
                    'check_out': latest_entry.check_out
                }
            else:
                shift_entries[employee.id] = None
        time_entries[shift.id] = shift_entries

    if request.method == 'POST':
        # Create a new shift
        if 'create_shift' in request.POST:
            shift_type = request.POST['shift_type']
            start_time = request.POST['start_time']
            end_time = request.POST['end_time']

            try:
                shift_start_time = datetime.strptime(start_time, "%H:%M").time()
                shift_end_time = datetime.strptime(end_time, "%H:%M").time()
            except ValueError:
                messages.error(request, "Invalid date or time format. Please use HH:MM for time.")
                return redirect('project_detail', project_id=project.id)

            # Create a new shift for the project
            Shift.objects.create(
                project=project,
                date=timezone.now().date(),
                start_time=shift_start_time,
                end_time=shift_end_time,
                shift_type=shift_type
            )
            messages.success(request, "Shift created successfully.")
            return redirect('project_detail', project_id=project.id)

        # Assign multiple employees to a shift
        elif 'assign_employees' in request.POST:
            shift_id = request.POST['shift_id']
            employee_ids = request.POST.getlist('employees')  
            shift = get_object_or_404(Shift, id=shift_id)

            conflicts = []
            for employee_id in employee_ids:
                employee = get_object_or_404(Employee, id=employee_id)

                # Check for conflicts before assigning
                if check_conflicts(employee, shift.date, shift.start_time, shift.end_time):
                    conflicts.append(employee.user.username)
                else:
                    shift.employees.add(employee)  
                    send_shift_email(employee.user.email, shift, 'assigned')  

            if conflicts:
                messages.error(request, f"Cannot assign: {', '.join(conflicts)} due to conflicts.")
            else:
                messages.success(request, "Employees assigned to the shift successfully.")

            return redirect('project_detail', project_id=project.id)

        # Remove an employee from a shift
        elif 'remove_employee' in request.POST:
            shift_id = request.POST['shift_id']
            employee_id = request.POST['employee_id']
            shift = get_object_or_404(Shift, id=shift_id)
            employee = get_object_or_404(Employee, id=employee_id)

            # Remove the employee from the shift
            shift.employees.remove(employee)

            # Send email notification
            send_shift_email(employee.user.email, shift, 'removed')

            messages.success(request, f"{employee.user.username} has been removed from the shift.")
            return redirect('project_detail', project_id=project.id)

        # Edit an existing shift
        elif 'edit_shift' in request.POST:
            shift_id = request.POST['shift_id']
            shift = get_object_or_404(Shift, id=shift_id)

            shift_type = request.POST['shift_type']
            start_time = request.POST['start_time']
            end_time = request.POST['end_time']

            try:
                shift_start_time = datetime.strptime(start_time, "%H:%M").time()
                shift_end_time = datetime.strptime(end_time, "%H:%M").time()
            except ValueError:
                messages.error(request, "Invalid date or time format. Please use HH:MM for time.")
                return redirect('project_detail', project_id=project.id)

            # Update the shift details
            shift.shift_type = shift_type
            shift.start_time = shift_start_time
            shift.end_time = shift_end_time
            shift.save()

            messages.success(request, "Shift updated successfully.")
            return redirect('project_detail', project_id=project.id)

        # Delete a shift
        elif 'delete_shift' in request.POST:
            shift_id = request.POST['shift_id']
            shift = get_object_or_404(Shift, id=shift_id)
            shift.delete()

            messages.success(request, "Shift deleted successfully.")
            return redirect('project_detail', project_id=project.id)

    # Get a list of employees with no conflicts for each shift
    available_employees = []
    for employee in employees:
        if not any(
            check_conflicts(employee, shift.date, shift.start_time, shift.end_time)
            for shift in shifts
        ):
            available_employees.append(employee)

    # Pass the filtered and collected data to the template
    return render(request, 'Escheduler/project_detail.html', {
        'project': project,
        'shifts': shifts,
        'employees': available_employees,  
        'time_entries': time_entries,
        'attendance_entries': attendance_entries,
        'date_range': date_range,
    })


def check_conflicts(employee, shift_date, start_time, end_time):
    """
    Check if there are overlapping shifts for the employee across all projects during the specified date and time.
    """
    overlapping_shifts = Shift.objects.filter(
        employees=employee,
        date=shift_date,  
        start_time__lt=end_time,  
        end_time__gt=start_time   
    )
    return overlapping_shifts.exists()

def create_notification(user, message):
    """
    Create a notification for the user.
    """
    Notification.objects.create(user=user, message=message)



def check_conflicts(employee, shift_date, start_time, end_time):
    """
    Check if there are overlapping shifts for the employee on the same date and during the specified time.
    """
    overlapping_shifts = Shift.objects.filter(
        employees=employee,
        date=shift_date,  
        start_time__lt=end_time,
        end_time__gt=start_time
    )
    return overlapping_shifts.exists()


def create_notification(user, message):
    """
    Create a notification for the user.
    """
    Notification.objects.create(user=user, message=message)


def send_shift_email(email, shift, action):
    subject = f"You have been {action} to a shift"
    message = f"""
        Dear Employee,

        You have been {action} the following shift:
        
        Project: {shift.project.name}
        Date: {shift.date}
        Start Time: {shift.start_time}
        End Time: {shift.end_time}

        Regards,
        Your Team
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,  
        [email],
    )



@login_required
def update_availability(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        employee = Employee(user=request.user)

    if request.method == 'POST':
        form = AvailabilityForm(request.POST, instance=employee)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.availability_days = ','.join(form.cleaned_data['availability_days'])
            employee.save()
            messages.success(request, "Your availability has been updated.")
            return redirect('dashboard')  
    else:
        form = AvailabilityForm(instance=employee)

    return render(request, 'Escheduler/update_availability.html', {'form': form})



@login_required
def check_in(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    employee = get_object_or_404(Employee, user=request.user)

    if shift.employees.filter(id=employee.id).exists():
        time_entry, created = TimeEntry.objects.get_or_create(
            employee=employee,
            shift=shift,
            defaults={'check_in': timezone.now()}
        )
        if not created:
            messages.error(request, "You have already checked in for this shift.")
        else:
            messages.success(request, "Checked in successfully.")
    else:
        messages.error(request, "You are not assigned to this shift.")

    return redirect('dashboard')

@login_required
def check_out(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    employee = get_object_or_404(Employee, user=request.user)

    # Get the time entry for the employee's shift
    time_entry = get_object_or_404(TimeEntry, employee=employee, shift=shift, check_out__isnull=True)
    time_entry.check_out = timezone.now()

    # Calculate the total time worked in hours
    time_worked = (time_entry.check_out - time_entry.check_in).total_seconds() / 3600  

    # Ensure that Employee model has 'hourly_rate' field, and use Decimal for precise calculations
    hourly_rate = Decimal(employee.hourly_rate)
    payment = Decimal(time_worked) * hourly_rate

    # Store the payment in the time entry
    time_entry.payment = payment
    time_entry.save()

    messages.success(request, f"Checked out successfully. Total payment for this shift: ${payment:.2f}")

    return redirect('dashboard')  


@login_required
def timesheet(request):
    employee = get_object_or_404(Employee, user=request.user)
    time_entries = TimeEntry.objects.filter(employee=employee)

    total_payment = 0
    for entry in time_entries:
        total_payment += entry.calculate_payment()  

    return render(request, 'Escheduler/timesheet.html', {
        'time_entries': time_entries,
        'total_payment': total_payment
    })




@login_required
def project_schedule(request, project_id):
    project = Project.objects.get(id=project_id)
    schedules = Schedule.objects.filter(project=project)
    shifts = Shift.objects.filter(project=project)
    return render(request, 'Escheduler/project_schedule.html', {'project': project, 'schedules': schedules, 'shifts': shifts})



@login_required
def create_shift(request):
    if request.method == 'POST':
        start_time = request.POST['start_time']
        end_time = request.POST['end_time']
        employee = Employee.objects.get(user=request.user)
        project_id = request.GET.get('project_id')
        project = Project.objects.get(id=project_id)
        
        Shift.objects.create(
            employee=employee,
            project=project,  
            start_time=start_time,
            end_time=end_time
        )
        return redirect('project_detail', project_id=project.id)  
    return render(request, 'Escheduler/create_shift.html')



@login_required
def assign_shift(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    employees = Employee.objects.all()  

    if request.method == 'POST':
        employee_ids = request.POST.getlist('employee')  
        start_time = request.POST['start_time']
        end_time = request.POST['end_time']
        shift_day = request.POST['shift_day']

        try:
            shift_start_time = datetime.strptime(start_time, "%H:%M").time()
            shift_end_time = datetime.strptime(end_time, "%H:%M").time()
        except ValueError:
            messages.error(request, "Invalid time format. Please use HH:MM.")
            return redirect('project_detail', project_id=project.id)

        # Create the shift for the project
        shift = Shift.objects.create(
            project=project,
            start_time=shift_start_time,
            end_time=shift_end_time,
            shift_type=request.POST['shift_type']
        )

        for employee_id in employee_ids:
            employee = Employee.objects.get(id=employee_id)
            if employee.is_available_for_shift(shift_start_time, shift_end_time, shift_day):
                shift.employees.add(employee)
            else:
                messages.warning(
                    request, 
                    f"{employee.user.username} is unavailable during the selected shift."
                )

        return redirect('project_detail', project_id=project.id)

    return render(request, 'Escheduler/assign_shift.html', {
        'project': project,
        'employees': employees
    })




@login_required
def manage_shift_swaps(request):
    if request.user.is_staff:  # Only managers can access this view
        swap_requests = ShiftSwapRequest.objects.filter(status='pending')  # Get pending requests

        if request.method == 'POST':
            request_id = request.POST.get('request_id')
            action = request.POST.get('action')
            swap_request = get_object_or_404(ShiftSwapRequest, id=request_id)

            if action == 'approve':
                swap_request.status = 'approved'
                swap_request.response_date = timezone.now()
                swap_request.manager_response = request.POST.get('response')
                swap_request.save()

                # Notify the employee via email
                send_manager_decision_email(swap_request, approved=True)

                messages.success(request, "Shift swap approved successfully.")
            elif action == 'deny':
                swap_request.status = 'denied'
                swap_request.response_date = timezone.now()
                swap_request.manager_response = request.POST.get('response')
                swap_request.save()

                # Notify the employee via email
                send_manager_decision_email(swap_request, approved=False)

                messages.error(request, "Shift swap denied.")

            return redirect('manage_shift_swaps')

        return render(request, 'Escheduler/manage_shift_swaps.html', {
            'swap_requests': swap_requests  # Pass the swap requests to the template
        })
    else:
        return redirect('dashboard')
    


@login_required
def request_shift_swap(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)

    if request.method == 'POST':
        form = ShiftSwapRequestForm(request.POST)
        if form.is_valid():
            swap_request = form.save(commit=False)
            swap_request.original_shift = shift
            swap_request.employee = Employee.objects.get(user=request.user)
            swap_request.status = 'pending'
            swap_request.save()

            # Email notifications (same as before)
            employee = swap_request.employee
            managers = User.objects.filter(is_staff=True)

            # Email notification to the employee
            send_email_notification(
                subject="Your Shift Swap Request Has Been Submitted",
                recipient_email=employee.user.email,
                template_name='Escheduler/email/shift_swap_employee.html',
                context={
                    'employee': employee,
                    'swap_request': swap_request
                }
            )

            # Email notification to the manager(s)
            for manager in managers:
                send_email_notification(
                    subject="New Shift Swap Request Submitted",
                    recipient_email=manager.email,
                    template_name='Escheduler/email/shift_swap_manager.html',
                    context={
                        'employee': employee,
                        'swap_request': swap_request,
                        'manager': manager
                    }
                )

            messages.success(request, "Your swap request has been submitted and the manager has been notified!")
            return redirect('dashboard')
    else:
        form = ShiftSwapRequestForm()

    return render(request, 'Escheduler/request_shift_swap.html', {
        'form': form,
        'shift': shift
    })



def send_manager_decision_email(swap_request, approved):
    subject = f"Shift Swap Request { 'Approved' if approved else 'Denied' }"
    from_email = settings.EMAIL_HOST_USER
    to_email = swap_request.employee.user.email
    
    # Render HTML content
    html_content = render_to_string('Escheduler/email/manager_shift_swap_decision.html', {
        'employee': swap_request.employee.user.username,
        'shift': swap_request.original_shift,
        'decision': 'approved' if approved else 'denied',
        'response_date': swap_request.response_date,
        'manager_response': swap_request.manager_response or "No additional comments.",
    })
    
    # Create the email
    email = EmailMultiAlternatives(
        subject=subject,
        body="Your shift swap request has been processed. Please view this email in an HTML-supported email client.",
        from_email=from_email,
        to=[to_email]
    )
    
    # Attach the HTML version
    email.attach_alternative(html_content, "text/html")
    
    # Send the email
    email.send()



@login_required
def report_shift(request):
    if request.method == 'POST':
        shift_id = request.POST.get('shift_id')
        report_details = request.POST.get('report_details')
        shift = get_object_or_404(Shift, id=shift_id)
        
        # Assuming there's a field in Shift model to store reports
        shift.report_details = report_details
        shift.has_reported = True
        shift.save()

        messages.success(request, "Shift reported successfully.")
        return redirect('dashboard')
    return redirect('dashboard')  #

@login_required
def request_time_off(request):
    if request.method == 'POST':
        reason = request.POST.get('reason')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        employee = Employee.objects.get(user=request.user)

        # Create and save the time off request
        time_off_request = TimeOffRequest(
            employee=employee,
            reason=reason,
            start_date=start_date,
            end_date=end_date,
            status='pending'
        )
        time_off_request.save()

        # Notify the employee via email
        send_email_notification(
            subject="Your Time Off Request Has Been Submitted",
            recipient_email=employee.user.email,
            template_name='Escheduler/email/time_off_request_employee.html',
            context={
                'employee': employee,
                'time_off_request': time_off_request
            }
        )

        # Notify the manager(s) via email (using user.is_staff to identify managers)
        managers = User.objects.filter(is_staff=True)
        for manager in managers:
            send_email_notification(
                subject="New Time Off Request Submitted",
                recipient_email=manager.email,
                template_name='Escheduler/email/time_off_request_manager.html',
                context={
                    'employee': employee,
                    'time_off_request': time_off_request,
                    'manager': manager
                }
            )

        messages.success(request, "Time off request submitted successfully.")
        return redirect('dashboard')
    
    return redirect('dashboard')


def send_email_notification(subject, recipient_email, template_name, context):
    # Render the HTML template with context
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)  # Fallback to plain text if HTML fails

    # Send the email
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
        html_message=html_message
    )

@login_required
def manage_time_off_requests(request):
    if request.user.is_staff:
        if request.method == 'POST':
            request_id = request.POST.get('request_id')
            action = request.POST.get('action')
            manager_response = request.POST.get('manager_response')

            try:
                time_off_request = TimeOffRequest.objects.get(id=request_id)
                time_off_request.response_date = timezone.now()
                time_off_request.manager_response = manager_response

                if action == 'approve':
                    time_off_request.status = 'approved'
                    email_subject = 'Time Off Request Approved'
                    email_message = f"Your request for time off from {time_off_request.start_date} to {time_off_request.end_date} has been approved."
                elif action == 'deny':
                    time_off_request.status = 'denied'
                    email_subject = 'Time Off Request Denied'
                    email_message = f"Your request for time off from {time_off_request.start_date} to {time_off_request.end_date} has been denied."

                # Save the manager's decision
                time_off_request.save()

                # Notify the employee
                send_mail(
                    email_subject,
                    f"{email_message} Manager's response: {manager_response}",
                    settings.DEFAULT_FROM_EMAIL,
                    [time_off_request.employee.user.email],
                )

                messages.success(request, f"Time off request {action}ed successfully.")
            except TimeOffRequest.DoesNotExist:
                messages.error(request, "Time off request not found.")
        
        # Display requests and project shift information
        requests = TimeOffRequest.objects.all()

        # Embed shift info in each request
        for req in requests:
            employee = req.employee
            req.project_shifts = get_employee_project_shifts(employee)  # Attach shift info directly to the request object

        return render(request, 'Escheduler/manage_time_off.html', {'requests': requests})
    
    else:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('dashboard')
    
def get_employee_project_shifts(employee):
    # Assuming an Employee can have multiple shifts assigned
    shifts = Shift.objects.filter(employees=employee)  # Use 'employees' for ManyToManyField

    project_shift_info = []
    for shift in shifts:
        project_shift_info.append({
            'project_name': shift.project.name if shift.project else "No Project",  # Check if project exists
            'shift_time': f"{shift.start_time} - {shift.end_time}",  # Assuming Shift has start_time and end_time fields
        })
    
    return project_shift_info





def send_verification_email(user, request):
    current_site = get_current_site(request)
    subject = 'Verify your email address'
    
    # Reverse the URL for activation
    activation_link = reverse('activate_account', kwargs={
        'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': email_verification_token.make_token(user)
    })
    
    full_activation_url = f'http://{current_site.domain}{activation_link}'
    
    message = render_to_string('Escheduler/email_verification.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': email_verification_token.make_token(user),
        'activation_link': full_activation_url,  
    })
    
    send_mail(
        subject, 
        message, 
        'add your company email',  
        [user.email], 
        fail_silently=False
    )

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(user, request)
            messages.success(request, 'Registration successful! Please check your email to verify your account.')
            return redirect('login')  
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'Escheduler/Sign_up.html', {'form': form})

def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'Your account has been activated successfully!')
        return redirect('dashboard')
    else:
        messages.error(request, 'The activation link is invalid or has expired.')
        return redirect('login')






User = get_user_model()

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Get the entered username or email and password
            login_input = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Check if the input is an email or username
            try:
                # If it's an email, fetch the associated user
                user = User.objects.get(email=login_input)
                username = user.username  
            except User.DoesNotExist:
                username = login_input  

            # Authenticate the user by username and password
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('dashboard')  
            else:
                messages.error(request, 'Invalid email/username or password.')
        else:
            messages.error(request, 'Invalid email/username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'Escheduler/Sign_in.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login')  