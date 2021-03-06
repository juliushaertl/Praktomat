# -*- coding: utf-8 -*-

import tempfile
import zipfile

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404
from django.http import HttpResponseRedirect, HttpResponse
from django.template.context import RequestContext
from datetime import datetime
from django import forms
from django.core import urlresolvers
from django.contrib import messages
import django.utils.timezone

from tasks.models import Task
from solutions.forms import ModelSolutionFormSet
from solutions.models import Solution, SolutionFile
from accounts.models import User
from accounts.views import access_denied
from attestation.models import Attestation, Script
from configuration import get_settings

@login_required
def taskList(request):
	now = django.utils.timezone.now()
	tasks = Task.objects.filter(publication_date__lte = now).order_by('submission_date')
	try:
		tutors = request.user.tutorial.tutors.all()
	except:
		tutors = None
	trainers = User.objects.filter(groups__name="Trainer")

	attestations = []
	expired_Tasks = Task.objects.filter(submission_date__lt = now).order_by('publication_date','submission_date')
	for task in expired_Tasks:
		attestation_qs =  Attestation.objects.filter(solution__task = task, published=True, solution__author=request.user)
		attestations.append((task, attestation_qs.first()))

	script = Script.objects.get_or_create(id=1)[0].script

	def tasksWithSolutions(tasks):
		return map(lambda t: (t, t.final_solution(request.user)), tasks)

	return render_to_response(
                'tasks/task_list.html',
                {
                        'tasks':tasksWithSolutions(tasks),
                        'expired_tasks': tasksWithSolutions(expired_Tasks),
                        'attestations':attestations,
                        'show_final_grade': get_settings().final_grades_published,
                        'tutors':tutors,
                        'trainers':trainers,
                        'script':script
                },
                context_instance=RequestContext(request))

@login_required
def taskDetail(request,task_id):
	task = get_object_or_404(Task,pk=task_id)

        if task.publication_date >= datetime.now() and not request.user.is_trainer:
		raise Http404

	my_solutions = Task.objects.get(pk=task_id).solution_set.filter(author = request.user)
        return render_to_response(
                'tasks/task_detail.html',
                {
                        'task': task,
                        'solutions': my_solutions,
                },
                context_instance=RequestContext(request))

class ImportForm(forms.Form):
	file = forms.FileField()

@staff_member_required
def import_tasks(request):
	""" View in the admin """
	if request.method == 'POST': 
		form = ImportForm(request.POST, request.FILES)
		if form.is_valid(): 
			try:
				Task.import_Tasks(form.files['file'], request.user)
                                messages.success(request, "The import was successfull.")
				return HttpResponseRedirect(urlresolvers.reverse('admin:tasks_task_changelist'))
			except Exception, e:
				from django.forms.util import ErrorList
                                msg = "An Error occured. The import file was propably malformed.: %s" % str(e)
				form._errors["file"] = ErrorList([msg]) 			
	else:
		form = ImportForm()
	return render_to_response('admin/tasks/task/import.html', {'form': form, 'title':"Import Task"  }, RequestContext(request))

@staff_member_required
def download_final_solutions(request, task_id):
	""" download all final solutions of a task from the admin interface """
	zip_file = tempfile.SpooledTemporaryFile()
	zip = zipfile.ZipFile(zip_file,'w')
	for solution_file in SolutionFile.objects.filter(solution__task=task_id):
		if solution_file.solution.final:
			zip.write(solution_file.file.path, solution_file.file.name)
	zip.close()
	zip_file.seek(0)
	response = HttpResponse(zip_file.read(), content_type="application/zip")
	response['Content-Disposition'] = 'attachment; filename=FinalSolutions.zip'
	return response
	

@staff_member_required
def model_solution(request, task_id):
	""" View in the admin """
	task = get_object_or_404(Task,pk=task_id)
	
	if request.method == "POST":	
		solution = Solution(task = task, author=request.user)
		formset = ModelSolutionFormSet(request.POST, request.FILES, instance=solution)
		if formset.is_valid():
			try:
				solution.save(); 
				# no deleting the old solution:
				# delete will cascade on db level deleting checker results and checker 
				# as this isn't easily prevented just keep the old solution around until the task is deleted
				formset.save()		
				solution.check(request.session)
				task.model_solution = solution;
				task.save()
			except:
				solution.delete()	# delete files 
				raise				# dont commit db changes
	else:
		formset = ModelSolutionFormSet()
	context = {"formset": formset, "task": task, 'title': "Model Solution", 'is_popup': True, }
	return render_to_response("admin/tasks/task/model_solution.html", context, context_instance=RequestContext(request))

