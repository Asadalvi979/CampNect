import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from ..models import Note, Connection, CommunityMember
from ..forms import NoteUploadForm
from .utils import validate_uploaded_file


@login_required
def notes_view(request):
    if request.method == 'POST':
        if request.POST.get('action') == 'delete_note':
            note_id = request.POST.get('note_id')
            note = get_object_or_404(Note, id=note_id, uploaded_by=request.user)
            if note.file and os.path.isfile(note.file.path):
                os.remove(note.file.path)
            note.delete()
            messages.success(request, 'Note deleted successfully.')
            return redirect('notes')

        form = NoteUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES.get('file')
            file_error = validate_uploaded_file(uploaded_file, allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'zip', 'rar'], max_size_mb=50)
            if file_error:
                messages.error(request, file_error)
                return redirect('notes')
            note = form.save(commit=False)
            note.uploaded_by = request.user
            note.save()
            messages.success(request, 'Notes uploaded successfully.')
            return redirect('notes')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('notes')

    all_notes_list = Note.objects.all().order_by('-upload_date').select_related('uploaded_by')
    my_notes = Note.objects.filter(uploaded_by=request.user).order_by('-upload_date').select_related('uploaded_by')

    page = request.GET.get('page', 1)
    paginator = Paginator(all_notes_list, 20)
    all_notes = paginator.get_page(page)

    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    context = {
        'all_notes': all_notes,
        'my_notes': my_notes,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'notes.html', context)
