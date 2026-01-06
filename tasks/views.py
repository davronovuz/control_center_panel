from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse
from django.utils import timezone
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from .models import Task, Question, TaskAssignment, Answer
from accounts.models import Region, District, Mahalla


@login_required
def task_list(request):
    """Vazifalar ro'yxati"""

    tasks = Task.objects.select_related(
        'created_by', 'target_region', 'target_district'
    ).order_by('-created_at')

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
        tasks = tasks.filter(task_type=task_type)
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    # Pagination
    paginator = Paginator(tasks, 15)
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
def task_create(request):
    """Yangi vazifa yaratish"""

    if request.method == 'POST':
        try:
            # Vazifa yaratish
            task = Task.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description', ''),
                task_type=request.POST.get('task_type', Task.Type.SURVEY),
                priority=request.POST.get('priority', Task.Priority.MEDIUM),
                deadline=request.POST.get('deadline'),
                created_by=request.user,
            )

            # Manzil targeting
            region_id = request.POST.get('target_region')
            district_id = request.POST.get('target_district')

            if region_id:
                task.target_region_id = region_id
            if district_id:
                task.target_district_id = district_id

            task.save()

            # Savollarni qo'shish
            questions = request.POST.getlist('question_text[]')
            question_types = request.POST.getlist('question_type[]')

            for i, (text, q_type) in enumerate(zip(questions, question_types), 1):
                if text.strip():
                    Question.objects.create(
                        task=task,
                        order=i,
                        text=text.strip(),
                        question_type=q_type,
                    )

            messages.success(request, f"Vazifa '{task.title}' yaratildi!")
            return redirect('tasks:task_detail', pk=task.pk)

        except Exception as e:
            messages.error(request, f"Xatolik: {str(e)}")

    regions = Region.objects.filter(is_active=True)

    context = {
        'regions': regions,
        'type_choices': Task.Type.choices,
        'priority_choices': Task.Priority.choices,
        'question_type_choices': Question.Type.choices,
    }

    return render(request, 'tasks/task_form.html', context)


@login_required
def task_detail(request, pk):
    """Vazifa tafsilotlari"""

    task = get_object_or_404(Task, pk=pk)

    # Savollar
    questions = task.questions.order_by('order')

    # Tayinlashlar
    assignments = task.assignments.select_related('leader').order_by('-sent_at')

    # Statistika
    stats = {
        'total': assignments.count(),
        'pending': assignments.filter(status=TaskAssignment.Status.PENDING).count(),
        'seen': assignments.filter(status=TaskAssignment.Status.SEEN).count(),
        'in_progress': assignments.filter(status=TaskAssignment.Status.IN_PROGRESS).count(),
        'completed': assignments.filter(status=TaskAssignment.Status.COMPLETED).count(),
    }

    # Pagination for assignments
    paginator = Paginator(assignments, 20)
    page = request.GET.get('page')
    assignments = paginator.get_page(page)

    context = {
        'task': task,
        'questions': questions,
        'assignments': assignments,
        'stats': stats,
    }

    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_edit(request, pk):
    """Vazifani tahrirlash"""

    task = get_object_or_404(Task, pk=pk)

    # Faqat qoralama vazifalarni tahrirlash mumkin
    if task.status != Task.Status.DRAFT:
        messages.warning(request, "Faqat qoralama vazifalarni tahrirlash mumkin!")
        return redirect('tasks:task_detail', pk=pk)

    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description', '')
        task.task_type = request.POST.get('task_type')
        task.priority = request.POST.get('priority')
        task.deadline = request.POST.get('deadline')

        # Manzil
        region_id = request.POST.get('target_region')
        district_id = request.POST.get('target_district')

        task.target_region_id = region_id if region_id else None
        task.target_district_id = district_id if district_id else None

        task.save()

        # Savollarni yangilash — avval eskisini o'chirish
        task.questions.all().delete()

        questions = request.POST.getlist('question_text[]')
        question_types = request.POST.getlist('question_type[]')

        for i, (text, q_type) in enumerate(zip(questions, question_types), 1):
            if text.strip():
                Question.objects.create(
                    task=task,
                    order=i,
                    text=text.strip(),
                    question_type=q_type,
                )

        messages.success(request, "Vazifa yangilandi!")
        return redirect('tasks:task_detail', pk=pk)

    regions = Region.objects.filter(is_active=True)
    questions = task.questions.order_by('order')

    context = {
        'task': task,
        'questions': questions,
        'regions': regions,
        'type_choices': Task.Type.choices,
        'priority_choices': Task.Priority.choices,
        'question_type_choices': Question.Type.choices,
    }

    return render(request, 'tasks/task_form.html', context)


@login_required
def task_delete(request, pk):
    """Vazifani o'chirish"""

    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST':
        title = task.title
        task.delete()
        messages.success(request, f"Vazifa '{title}' o'chirildi!")
        return redirect('tasks:task_list')

    context = {
        'task': task,
    }

    return render(request, 'tasks/task_delete.html', context)


@login_required
def task_publish(request, pk):
    """Vazifani e'lon qilish"""

    task = get_object_or_404(Task, pk=pk)

    if task.status != Task.Status.DRAFT:
        messages.warning(request, "Bu vazifa allaqachon e'lon qilingan!")
        return redirect('tasks:task_detail', pk=pk)

    if task.questions.count() == 0:
        messages.error(request, "Vazifada kamida 1 ta savol bo'lishi kerak!")
        return redirect('tasks:task_detail', pk=pk)

    if request.method == 'POST':
        if task.publish():
            messages.success(request, f"Vazifa e'lon qilindi! {task.stats_total_assigned} ta yetakchiga yuborildi.")
        else:
            messages.error(request, "Vazifani e'lon qilishda xatolik!")

        return redirect('tasks:task_detail', pk=pk)

    # E'lon qilishdan oldin ma'lumot ko'rsatish
    target_leaders = task.get_target_leaders()

    context = {
        'task': task,
        'target_leaders_count': target_leaders.count(),
        'target_leaders': target_leaders[:20],  # Birinchi 20 tasi
    }

    return render(request, 'tasks/task_publish.html', context)


@login_required
def task_results(request, pk):
    """Vazifa natijalari"""

    task = get_object_or_404(Task, pk=pk)

    # Barcha javoblar
    assignments = task.assignments.filter(
        status=TaskAssignment.Status.COMPLETED
    ).select_related('leader').prefetch_related('answers__question')

    questions = task.questions.order_by('order')

    # Jadval uchun ma'lumot
    results = []
    for assignment in assignments:
        row = {
            'leader': assignment.leader,
            'completed_at': assignment.completed_at,
            'answers': {}
        }

        for answer in assignment.answers.all():
            row['answers'][answer.question.order] = answer.display_value

        results.append(row)

    context = {
        'task': task,
        'questions': questions,
        'results': results,
    }

    return render(request, 'tasks/task_results.html', context)


@login_required
def task_export(request, pk):
    """Natijalarni Excel ga export qilish"""

    task = get_object_or_404(Task, pk=pk)

    # Excel yaratish
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Natijalar"

    # Stillar
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Sarlavha
    questions = task.questions.order_by('order')

    headers = ['№', 'Yetakchi', 'Mahalla', 'Telefon']
    headers += [q.text for q in questions]
    headers += ['Bajarilgan vaqt']

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Ma'lumotlar
    assignments = task.assignments.filter(
        status=TaskAssignment.Status.COMPLETED
    ).select_related('leader', 'leader__mahalla').prefetch_related('answers__question')

    for row_num, assignment in enumerate(assignments, 2):
        # Asosiy ma'lumotlar
        ws.cell(row=row_num, column=1, value=row_num - 1).border = thin_border
        ws.cell(row=row_num, column=2, value=assignment.leader.get_full_name()).border = thin_border
        ws.cell(row=row_num, column=3, value=str(assignment.leader.mahalla or '-')).border = thin_border
        ws.cell(row=row_num, column=4, value=assignment.leader.phone or '-').border = thin_border

        # Javoblar
        answers_dict = {a.question.order: a.display_value for a in assignment.answers.all()}

        for i, question in enumerate(questions):
            col = 5 + i
            value = answers_dict.get(question.order, '-')
            ws.cell(row=row_num, column=col, value=value).border = thin_border

        # Vaqt
        completed = assignment.completed_at.strftime('%d.%m.%Y %H:%M') if assignment.completed_at else '-'
        ws.cell(row=row_num, column=len(headers), value=completed).border = thin_border

    # Ustun kengligini sozlash
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{task.title}_natijalar.xlsx"'

    wb.save(response)
    return response