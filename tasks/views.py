from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
import openpyxl

from .models import Task, TaskColumn, TaskQuestion, TaskAssignment, TaskResponse, TaskHistory, TaskTemplate


@login_required
def task_list(request):
    """Vazifalar ro'yxati"""
    tasks = Task.objects.select_related('created_by', 'target_region', 'target_district').all()

    # Filterlar
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    task_type = request.GET.get('type')
    search = request.GET.get('search')

    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if task_type:
        tasks = tasks.filter(type=task_type)
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    # Pagination
    paginator = Paginator(tasks, 20)
    page = request.GET.get('page')
    tasks = paginator.get_page(page)

    context = {
        'tasks': tasks,
        'status_choices': Task.Status.choices,
        'priority_choices': Task.Priority.choices,
        'type_choices': Task.Type.choices,
        'current_filters': {
            'status': status,
            'priority': priority,
            'type': task_type,
            'search': search,
        }
    }
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_detail(request, pk):
    """Vazifa tafsilotlari"""
    task = get_object_or_404(Task.objects.select_related('created_by'), pk=pk)

    columns = task.columns.all().order_by('order')
    questions = task.questions.all().order_by('order')

    assignments = task.assignments.select_related('leader', 'leader__mahalla', 'leader__district').all()

    # Pagination for assignments
    paginator = Paginator(assignments, 20)
    page = request.GET.get('page')
    assignments = paginator.get_page(page)

    # Statistics
    stats = {
        'total': task.total_assigned,
        'pending': task.assignments.filter(status=TaskAssignment.Status.PENDING).count(),
        'viewed': task.assignments.filter(status=TaskAssignment.Status.VIEWED).count(),
        'in_progress': task.assignments.filter(status=TaskAssignment.Status.IN_PROGRESS).count(),
        'submitted': task.assignments.filter(status=TaskAssignment.Status.SUBMITTED).count(),
        'approved': task.assignments.filter(status=TaskAssignment.Status.APPROVED).count(),
        'rejected': task.assignments.filter(status=TaskAssignment.Status.REJECTED).count(),
    }

    context = {
        'task': task,
        'columns': columns,
        'questions': questions,
        'assignments': assignments,
        'stats': stats,
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_create(request):
    """Yangi vazifa yaratish"""
    from accounts.models import Region, District

    if request.method == 'POST':
        # Asosiy ma'lumotlar
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        instructions = request.POST.get('instructions', '')
        task_type = request.POST.get('type', 'table')
        priority = request.POST.get('priority', 'medium')
        deadline = request.POST.get('deadline')

        # Targeting
        target_all = request.POST.get('target_all') == 'on'
        target_region_id = request.POST.get('target_region')
        target_district_id = request.POST.get('target_district')

        # Settings
        requires_approval = request.POST.get('requires_approval') == 'on'
        allow_multiple_rows = request.POST.get('allow_multiple_rows') == 'on'

        # Vazifa yaratish
        task = Task.objects.create(
            title=title,
            description=description,
            instructions=instructions,
            type=task_type,
            priority=priority,
            deadline=deadline,
            target_all=target_all,
            target_region_id=target_region_id if target_region_id else None,
            target_district_id=target_district_id if target_district_id else None,
            requires_approval=requires_approval,
            allow_multiple_rows=allow_multiple_rows,
            created_by=request.user
        )

        # Ustunlar (TABLE type)
        if task_type == 'table':
            column_titles = request.POST.getlist('column_title[]')
            column_types = request.POST.getlist('column_type[]')

            for i, (title, dtype) in enumerate(zip(column_titles, column_types)):
                if title.strip():
                    TaskColumn.objects.create(
                        task=task,
                        title=title.strip(),
                        data_type=dtype,
                        order=i + 1
                    )

        # Savollar (SURVEY type)
        elif task_type == 'survey':
            question_texts = request.POST.getlist('question_text[]')
            question_types = request.POST.getlist('question_type[]')

            for i, (text, qtype) in enumerate(zip(question_texts, question_types)):
                if text.strip():
                    TaskQuestion.objects.create(
                        task=task,
                        text=text.strip(),
                        answer_type=qtype,
                        order=i + 1
                    )

        # Tarix
        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.CREATED,
            actor=request.user,
            description="Vazifa yaratildi"
        )

        messages.success(request, "Vazifa muvaffaqiyatli yaratildi!")
        return redirect('tasks:task_detail', pk=task.pk)

    context = {
        'regions': Region.objects.filter(is_active=True),
        'type_choices': Task.Type.choices,
        'priority_choices': Task.Priority.choices,
        'column_type_choices': TaskColumn.DataType.choices,
        'question_type_choices': TaskQuestion.AnswerType.choices,
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_edit(request, pk):
    """Vazifani tahrirlash"""
    from accounts.models import Region, District

    task = get_object_or_404(Task, pk=pk)

    if task.status != Task.Status.DRAFT:
        messages.error(request, "Faqat qoralama vazifani tahrirlash mumkin!")
        return redirect('tasks:task_detail', pk=pk)

    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description', '')
        task.instructions = request.POST.get('instructions', '')
        task.priority = request.POST.get('priority', 'medium')
        task.deadline = request.POST.get('deadline')
        task.target_all = request.POST.get('target_all') == 'on'
        task.target_region_id = request.POST.get('target_region') or None
        task.target_district_id = request.POST.get('target_district') or None
        task.requires_approval = request.POST.get('requires_approval') == 'on'
        task.allow_multiple_rows = request.POST.get('allow_multiple_rows') == 'on'
        task.save()

        # Ustunlarni yangilash (TABLE type)
        if task.type == 'table':
            task.columns.all().delete()
            column_titles = request.POST.getlist('column_title[]')
            column_types = request.POST.getlist('column_type[]')

            for i, (title, dtype) in enumerate(zip(column_titles, column_types)):
                if title.strip():
                    TaskColumn.objects.create(
                        task=task,
                        title=title.strip(),
                        data_type=dtype,
                        order=i + 1
                    )

        # Savollarni yangilash (SURVEY type)
        elif task.type == 'survey':
            task.questions.all().delete()
            question_texts = request.POST.getlist('question_text[]')
            question_types = request.POST.getlist('question_type[]')

            for i, (text, qtype) in enumerate(zip(question_texts, question_types)):
                if text.strip():
                    TaskQuestion.objects.create(
                        task=task,
                        text=text.strip(),
                        answer_type=qtype,
                        order=i + 1
                    )

        messages.success(request, "Vazifa yangilandi!")
        return redirect('tasks:task_detail', pk=task.pk)

    context = {
        'task': task,
        'columns': task.columns.order_by('order'),
        'questions': task.questions.order_by('order'),
        'regions': Region.objects.filter(is_active=True),
        'districts': District.objects.filter(region=task.target_region) if task.target_region else [],
        'type_choices': Task.Type.choices,
        'priority_choices': Task.Priority.choices,
        'column_type_choices': TaskColumn.DataType.choices,
        'question_type_choices': TaskQuestion.AnswerType.choices,
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_delete(request, pk):
    """Vazifani o'chirish"""
    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST':
        task.delete()
        messages.success(request, "Vazifa o'chirildi!")
        return redirect('tasks:task_list')

    return render(request, 'tasks/task_delete.html', {'task': task})


@login_required
def task_publish(request, pk):
    """Vazifani e'lon qilish"""
    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST':
        success, message = task.publish(request.user)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('tasks:task_detail', pk=pk)

    # Preview
    target_leaders = task.get_target_leaders()[:20]
    target_leaders_count = task.get_target_leaders().count()

    context = {
        'task': task,
        'target_leaders': target_leaders,
        'target_leaders_count': target_leaders_count,
    }
    return render(request, 'tasks/task_publish.html', context)


@login_required
def task_results(request, pk):
    """Vazifa natijalari"""
    task = get_object_or_404(Task, pk=pk)

    # Faqat yuborilgan va tasdiqlangan assignmentlar
    assignments = task.assignments.filter(
        status__in=[
            TaskAssignment.Status.SUBMITTED,
            TaskAssignment.Status.APPROVED,
            TaskAssignment.Status.REJECTED
        ]
    ).select_related(
        'leader',
        'leader__mahalla',
        'leader__district'
    ).prefetch_related('responses', 'responses__column', 'responses__question')

    columns = list(task.columns.order_by('order'))
    questions = list(task.questions.order_by('order'))

    results = []
    for assignment in assignments:
        row = {
            'assignment': assignment,
            'leader': assignment.leader,
            'status': assignment.status,
            'submitted_at': assignment.submitted_at,
            'answers': {}
        }

        # Javoblarni to'plash
        for response in assignment.responses.all():
            if response.column:
                # Table type - column order bo'yicha
                key = f"col_{response.column.order}_{response.row_index}"
                row['answers'][key] = response.display_value
            elif response.question:
                # Survey type - question order bo'yicha
                key = f"q_{response.question.order}"
                row['answers'][key] = response.display_value
            else:
                # Report type
                row['answers']['report'] = response.value_text

        results.append(row)

    context = {
        'task': task,
        'columns': columns,
        'questions': questions,
        'results': results,
        'assignments': assignments,
    }
    return render(request, 'tasks/task_results.html', context)


@login_required
def task_export(request, pk):
    """Natijalarni Excel ga eksport"""
    task = get_object_or_404(Task, pk=pk)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Natijalar"

    # Sarlavha
    headers = ['№', 'Yetakchi', 'Mahalla', 'Tuman', 'Telefon']

    if task.type == Task.Type.TABLE:
        for column in task.columns.order_by('order'):
            headers.append(column.title)
    elif task.type == Task.Type.SURVEY:
        for question in task.questions.order_by('order'):
            headers.append(question.text[:50])

    headers.extend(['Holat', 'Yuborilgan vaqt'])

    # Sarlavha yozish
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")

    # Ma'lumotlar
    assignments = task.assignments.select_related(
        'leader', 'leader__mahalla', 'leader__district'
    ).prefetch_related('responses')

    for row_num, assignment in enumerate(assignments, 2):
        ws.cell(row=row_num, column=1, value=row_num - 1)
        ws.cell(row=row_num, column=2, value=assignment.leader.get_full_name())
        ws.cell(row=row_num, column=3, value=str(assignment.leader.mahalla) if assignment.leader.mahalla else '')
        ws.cell(row=row_num, column=4, value=str(assignment.leader.district) if assignment.leader.district else '')
        ws.cell(row=row_num, column=5, value=assignment.leader.phone or '')

        col_num = 6
        if task.type == Task.Type.TABLE:
            for column in task.columns.order_by('order'):
                response = assignment.responses.filter(column=column).first()
                value = response.display_value if response else ''
                ws.cell(row=row_num, column=col_num, value=value)
                col_num += 1
        elif task.type == Task.Type.SURVEY:
            for question in task.questions.order_by('order'):
                response = assignment.responses.filter(question=question).first()
                value = response.display_value if response else ''
                ws.cell(row=row_num, column=col_num, value=value)
                col_num += 1

        ws.cell(row=row_num, column=col_num, value=assignment.get_status_display())
        ws.cell(row=row_num, column=col_num + 1,
                value=assignment.submitted_at.strftime('%d.%m.%Y %H:%M') if assignment.submitted_at else '')

    # Ustun kengligi
    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{task.title}_natijalar.xlsx"'
    wb.save(response)
    return response