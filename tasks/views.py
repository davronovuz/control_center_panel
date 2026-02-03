from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
import openpyxl
from openpyxl.styles import Font, PatternFill

from .models import Task, TaskColumn, TaskQuestion, TaskAssignment, TaskHistory, TaskResponse


# ==============================================================================
# YORDAMCHI FUNKSIYA (MUAMMONI HAL QILUVCHI)
# ==============================================================================
def get_list_secure(request, key):
    """
    HTML formadan kelgan ma'lumotlarni 'name[]' va 'name' formatlarida tekshirib,
    har qanday holatda ham to'liq ro'yxatni qaytaradi.
    Bu funksiya dinamik qatorlar (ustunlar, savollar) yo'qolib qolishini oldini oladi.
    """
    # 1-urinish: 'name[]' formatida (masalan: column_title[])
    values = request.POST.getlist(f"{key}[]")

    # 2-urinish: Agar bo'sh bo'lsa, 'name' formatida tekshiramiz (masalan: column_title)
    if not values:
        values = request.POST.getlist(key)

    return values


# ==============================================================================
# VIEW FUNKSIYALAR
# ==============================================================================

@login_required
def task_list(request):
    """Vazifalar ro'yxati"""
    # Optimallashtirish: N+1 muammosini oldini olish uchun select_related
    tasks = Task.objects.select_related('created_by', 'target_region', 'target_district').all().order_by('-created_at')

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
    """Vazifa tafsilotlari va statistikasi"""
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
    """Yangi vazifa yaratish (Konstruktor)"""
    from accounts.models import Region, District

    if request.method == 'POST':
        # --- 1. Asosiy ma'lumotlar ---
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

        # --- 2. Vazifani yaratish ---
        task = Task.objects.create(
            title=title,
            description=description,
            instructions=instructions,
            type=task_type,
            priority=priority,
            deadline=deadline if deadline else None,
            target_all=target_all,
            target_region_id=target_region_id if target_region_id else None,
            target_district_id=target_district_id if target_district_id else None,
            requires_approval=requires_approval,
            allow_multiple_rows=allow_multiple_rows,
            created_by=request.user,
            status=Task.Status.DRAFT  # Avval qoralama
        )

        # --- 3. Ustunlarni saqlash (TABLE) ---
        if task_type == 'table':
            # MUHIM: Xavfsiz funksiya orqali olish
            column_titles = get_list_secure(request, 'column_title')
            column_types = get_list_secure(request, 'column_type')

            for i, (col_title, col_type) in enumerate(zip(column_titles, column_types)):
                if col_title.strip():
                    TaskColumn.objects.create(
                        task=task,
                        title=col_title.strip(),
                        data_type=col_type,
                        order=i + 1
                    )

        # --- 4. Savollarni saqlash (SURVEY) ---
        elif task_type == 'survey':
            question_texts = get_list_secure(request, 'question_text')
            question_types = get_list_secure(request, 'question_type')

            for i, (q_text, q_type) in enumerate(zip(question_texts, question_types)):
                if q_text.strip():
                    TaskQuestion.objects.create(
                        task=task,
                        text=q_text.strip(),
                        answer_type=q_type,
                        order=i + 1
                    )

        # Tarix
        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.CREATED,
            actor=request.user,
            description="Vazifa konstruktori orqali yaratildi"
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
        messages.error(request, "Faqat qoralama (Draft) holatidagi vazifani tahrirlash mumkin!")
        return redirect('tasks:task_detail', pk=pk)

    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description', '')
        task.instructions = request.POST.get('instructions', '')
        task.priority = request.POST.get('priority', 'medium')
        task.deadline = request.POST.get('deadline')

        # Checkboxlar
        task.target_all = request.POST.get('target_all') == 'on'
        task.requires_approval = request.POST.get('requires_approval') == 'on'
        task.allow_multiple_rows = request.POST.get('allow_multiple_rows') == 'on'

        # Selectlar
        r_id = request.POST.get('target_region')
        d_id = request.POST.get('target_district')
        task.target_region_id = r_id if r_id else None
        task.target_district_id = d_id if d_id else None

        task.save()

        # --- Ustunlarni yangilash ---
        if task.type == 'table':
            # Eski ustunlarni o'chirib, yangilarini yozamiz
            task.columns.all().delete()

            # Yana o'sha xavfsiz funksiya
            titles = get_list_secure(request, 'column_title')
            types = get_list_secure(request, 'column_type')

            for i, (t, dt) in enumerate(zip(titles, types)):
                if t.strip():
                    TaskColumn.objects.create(task=task, title=t.strip(), data_type=dt, order=i + 1)

        # --- Savollarni yangilash ---
        elif task.type == 'survey':
            task.questions.all().delete()

            q_texts = get_list_secure(request, 'question_text')
            q_types = get_list_secure(request, 'question_type')

            for i, (qt, qtp) in enumerate(zip(q_texts, q_types)):
                if qt.strip():
                    TaskQuestion.objects.create(task=task, text=qt.strip(), answer_type=qtp, order=i + 1)

        messages.success(request, "Vazifa muvaffaqiyatli yangilandi!")
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
        # Agar modelda maxsus publish metodi bo'lsa, uni ishlatamiz
        if hasattr(task, 'publish'):
            success, message = task.publish(request.user)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        else:
            # Oddiy holatda statusni o'zgartiramiz
            task.status = Task.Status.PUBLISHED
            task.save()
            messages.success(request, "Vazifa e'lon qilindi")

        return redirect('tasks:task_detail', pk=pk)

    # Preview uchun ma'lumotlar
    target_leaders = []
    if hasattr(task, 'get_target_leaders'):
        target_leaders = task.get_target_leaders()[:20]
        target_leaders_count = task.get_target_leaders().count()
    else:
        target_leaders_count = 0

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

    # Faqat yuborilgan (submitted/approved/rejected) assignmentlar
    assignments = task.assignments.filter(
        status__in=['submitted', 'approved', 'rejected']
    ).select_related('leader', 'leader__mahalla', 'leader__district').prefetch_related('responses')

    columns = list(task.columns.order_by('order'))
    questions = list(task.questions.order_by('order'))

    results = []
    for assignment in assignments:
        # Har bir assignment uchun javoblarni yig'ish (tezkor lookup uchun dict)
        answers = {}

        for response in assignment.responses.all():
            if response.column:
                # Column ID bo'yicha saqlash
                answers[str(response.column.pk)] = response.display_value
            elif response.question:
                answers[str(response.question.pk)] = response.display_value
            else:
                answers['report'] = response.value_text

        results.append({
            'assignment': assignment,
            'leader': assignment.leader,
            'status': assignment.status,
            'submitted_at': assignment.submitted_at,
            'answers': answers,
        })

    context = {
        'task': task,
        'columns': columns,
        'questions': questions,
        'results': results,
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

    # Sarlavha yozish va formatlash
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")

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

    # Ustun kengligini avtomatik moslash
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter  # Get the column name
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = min(adjusted_width, 50)  # Juda keng bo'lib ketmasligi uchun limit

    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    # Fayl nomidagi kirill yoki maxsus belgilarni to'g'irlash uchun
    filename = f"task_results_{task.pk}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response