from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from accounts.models import User, Region, District, Mahalla, Announcement
from tasks.models import Task, TaskAssignment


@login_required
def home(request):
    """Admin dashboard"""
    if request.user.is_leader:
        return redirect('dashboard:leader_home')

    # Statistika
    total_leaders = User.objects.filter(role=User.Role.LEADER, status=User.Status.ACTIVE).count()
    total_tasks = Task.objects.count()
    active_tasks = Task.objects.filter(status=Task.Status.ACTIVE).count()
    completed_tasks = Task.objects.filter(status=Task.Status.COMPLETED).count()

    # Oxirgi 7 kun
    week_ago = timezone.now() - timedelta(days=7)
    new_tasks_week = Task.objects.filter(created_at__gte=week_ago).count()
    completed_week = TaskAssignment.objects.filter(
        submitted_at__gte=week_ago,
        status__in=[TaskAssignment.Status.SUBMITTED, TaskAssignment.Status.APPROVED]
    ).count()

    # Muddati o'tgan
    overdue_count = Task.objects.filter(
        status=Task.Status.ACTIVE,
        deadline__lt=timezone.now()
    ).count()

    # Faol vazifalar
    active_tasks_list = Task.objects.filter(
        status=Task.Status.ACTIVE
    ).order_by('deadline')[:5]

    # Oxirgi tayinlashlar
    recent_assignments = TaskAssignment.objects.select_related(
        'task', 'leader'
    ).order_by('-updated_at')[:10]

    context = {
        'total_leaders': total_leaders,
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
        'new_tasks_week': new_tasks_week,
        'completed_week': completed_week,
        'overdue_count': overdue_count,
        'active_tasks_list': active_tasks_list,
        'recent_assignments': recent_assignments,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def statistics(request):
    """Statistika sahifasi"""
    if request.user.is_leader:
        return redirect('dashboard:leader_home')

    # Vazifalar holati bo'yicha
    tasks_by_status = Task.objects.values('status').annotate(count=Count('id'))

    # Vazifalar muhimligi bo'yicha
    tasks_by_priority = Task.objects.values('priority').annotate(count=Count('id'))

    # Vazifalar turi bo'yicha
    tasks_by_type = Task.objects.values('type').annotate(count=Count('id'))

    # Top yetakchilar
    top_leaders = User.objects.filter(
        role=User.Role.LEADER,
        status=User.Status.ACTIVE
    ).annotate(
        completed_count=Count(
            'task_assignments',
            filter=Q(task_assignments__status__in=['submitted', 'approved'])
        )
    ).order_by('-completed_count')[:10]

    # Mahallalar bo'yicha
    mahalla_stats = Mahalla.objects.annotate(
        leaders_count=Count('users', filter=Q(users__role='leader')),
        tasks_count=Count('users__task_assignments')
    ).order_by('-tasks_count')[:10]

    # Oylik trend
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (timezone.now().replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)

        tasks = Task.objects.filter(created_at__gte=month_start, created_at__lt=month_end).count()
        completed = TaskAssignment.objects.filter(
            submitted_at__gte=month_start,
            submitted_at__lt=month_end,
            status__in=['submitted', 'approved']
        ).count()

        monthly_data.append({
            'month': month_start.strftime('%B'),
            'tasks': tasks,
            'completed': completed
        })

    context = {
        'tasks_by_status': tasks_by_status,
        'tasks_by_priority': tasks_by_priority,
        'tasks_by_type': tasks_by_type,
        'top_leaders': top_leaders,
        'mahalla_stats': mahalla_stats,
        'monthly_data': monthly_data,
    }
    return render(request, 'dashboard/statistics.html', context)


# ========== YETAKCHI PANEL ==========

@login_required
def leader_home(request):
    """Yetakchi dashboard"""
    if not request.user.is_leader:
        return redirect('dashboard:home')

    user = request.user

    # Vazifalar
    assignments = user.task_assignments.select_related('task')

    new_tasks = assignments.filter(status=TaskAssignment.Status.PENDING)
    in_progress = assignments.filter(status=TaskAssignment.Status.IN_PROGRESS)
    completed = assignments.filter(status__in=[TaskAssignment.Status.SUBMITTED, TaskAssignment.Status.APPROVED])

    # Muddati yaqin
    urgent_tasks = assignments.filter(
        status__in=[TaskAssignment.Status.PENDING, TaskAssignment.Status.VIEWED, TaskAssignment.Status.IN_PROGRESS],
        task__deadline__lte=timezone.now() + timedelta(days=3)
    ).order_by('task__deadline')[:5]

    # E'lonlar
    announcements = Announcement.objects.filter(
        status=Announcement.Status.ACTIVE
    ).filter(
        Q(target_all=True) |
        Q(target_region=user.region) |
        Q(target_district=user.district)
    ).order_by('-created_at')[:3]

    # O'qilmagan bildirishnomalar
    unread_notifications = user.notifications.filter(is_read=False).count()

    context = {
        'new_tasks_count': new_tasks.count(),
        'in_progress_count': in_progress.count(),
        'completed_count': completed.count(),
        'urgent_tasks': urgent_tasks,
        'announcements': announcements,
        'unread_notifications': unread_notifications,
    }
    return render(request, 'dashboard/leader_home.html', context)


@login_required
def leader_tasks(request):
    """Yetakchi vazifalari"""
    if not request.user.is_leader:
        return redirect('dashboard:home')

    assignments = request.user.task_assignments.select_related('task')

    # Filter
    status = request.GET.get('status')
    if status:
        assignments = assignments.filter(status=status)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(assignments.order_by('-created_at'), 10)
    page = request.GET.get('page')
    assignments = paginator.get_page(page)

    context = {
        'assignments': assignments,
        'status_choices': TaskAssignment.Status.choices,
        'current_status': status,
    }
    return render(request, 'dashboard/leader_tasks.html', context)


@login_required
def leader_task_detail(request, pk):
    """Yetakchi - vazifa tafsilotlari va to'ldirish"""
    if not request.user.is_leader:
        return redirect('dashboard:home')

    assignment = TaskAssignment.objects.select_related('task').get(
        pk=pk,
        leader=request.user
    )

    task = assignment.task

    # Ko'rildi deb belgilash
    assignment.mark_viewed()

    # Boshlash
    if assignment.status in [TaskAssignment.Status.PENDING, TaskAssignment.Status.VIEWED]:
        assignment.start()

    columns = task.columns.order_by('order')
    questions = task.questions.order_by('order')

    # Mavjud javoblar
    responses = {}
    for response in assignment.responses.all():
        if response.column:
            key = f"col_{response.column.pk}_{response.row_index}"
        elif response.question:
            key = f"q_{response.question.pk}"
        else:
            continue
        responses[key] = response

    context = {
        'assignment': assignment,
        'task': task,
        'columns': columns,
        'questions': questions,
        'responses': responses,
    }
    return render(request, 'dashboard/leader_task_detail.html', context)


@login_required
def leader_task_submit(request, pk):
    """Vazifani yuborish"""
    if not request.user.is_leader:
        return redirect('dashboard:home')

    assignment = TaskAssignment.objects.get(pk=pk, leader=request.user)

    if request.method == 'POST':
        assignment.submit()
        from django.contrib import messages
        messages.success(request, "Vazifa muvaffaqiyatli yuborildi!")
        return redirect('dashboard:leader_tasks')

    return redirect('dashboard:leader_task_detail', pk=pk)