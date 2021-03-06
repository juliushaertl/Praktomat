import zipfile
import tempfile

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404
from django.http import HttpResponseRedirect, HttpResponse
from django.template.context import RequestContext
from django.core.urlresolvers import reverse
from django.views.decorators.cache import cache_control
from django.template import Context, loader
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _
from django.contrib.sites.models import RequestSite


from datetime import datetime

from tasks.models import Task
from attestation.models import Attestation
from solutions.models import Solution, SolutionFile, get_solutions_zip
from solutions.forms import SolutionFormSet
from accounts.views import access_denied
from accounts.models import User
from configuration import get_settings
from checker.models import CheckerResult
from checker.models import check
from django.db import transaction

@login_required
@cache_control(must_revalidate=True, no_cache=True, no_store=True, max_age=0) #reload the page from the server even if the user used the back button
def solution_list(request, task_id, user_id=None):
        if (user_id and not request.user.is_trainer and not request.user.is_superuser):
		return access_denied(request)

	task = get_object_or_404(Task,pk=task_id)
	author = get_object_or_404(User,pk=user_id) if user_id else request.user
	solutions = task.solution_set.filter(author = author).order_by('-id')
	final_solution = task.final_solution(author)

        if task.publication_date >= datetime.now() and not request.user.is_trainer:
		raise Http404
	
	if request.method == "POST":
                if task.expired() and not request.user.is_trainer:
                        return access_denied(request)

		solution = Solution(task = task, author=author)
		formset = SolutionFormSet(request.POST, request.FILES, instance=solution)
		if formset.is_valid():
			solution.save()
			formset.save()
                        run_all_checker = bool(User.objects.filter(id=user_id, tutorial__tutors__pk=request.user.id) or request.user.is_trainer)
			solution.check(run_all_checker)
			
			if solution.accepted:  
				# Send submission confirmation email
				t = loader.get_template('solutions/submission_confirmation_email.html')
				c = {
					'protocol': request.is_secure() and "https" or "http",
					'domain': RequestSite(request).domain, 
					'site_name': settings.SITE_NAME,
					'solution': solution,
				}
				if solution.author.email:
					send_mail(_("%s submission confirmation") % settings.SITE_NAME, t.render(Context(c)), None, [solution.author.email])
		
			if solution.accepted or get_settings().accept_all_solutions:
				solution.final = True
				solution.save()
			
			return HttpResponseRedirect(reverse('solution_detail', args=[solution.id]))
	else:
		formset = SolutionFormSet()
	
	attestations = Attestation.objects.filter(solution__task=task, author__tutored_tutorials=request.user.tutorial)
	attestationsPublished = attestations[0].published if attestations else False

	return render_to_response("solutions/solution_list.html",
                {"formset": formset, "task":task, "solutions": solutions, "final_solution":final_solution, "attestationsPublished":attestationsPublished, "author":author, "invisible_attestor":get_settings().invisible_attestor},
		context_instance=RequestContext(request))
@login_required
def test_upload(request, task_id):
        if not request.user.is_trainer and not request.user.is_tutor and not request.user.is_superuser:
		return access_denied(request)

	task = get_object_or_404(Task,pk=task_id)

	if request.method == "POST":
		solution = Solution(task = task, author=request.user, testupload = True)
		formset = SolutionFormSet(request.POST, request.FILES, instance=solution)
		if formset.is_valid():
			solution.save()
			formset.save()
			solution.check(run_secret = True)

			return HttpResponseRedirect(reverse('solution_detail_full', args=[solution.id]))
	else:
		formset = SolutionFormSet()
	
	return render_to_response("solutions/solution_test_upload.html",
                {"formset": formset, "task":task},
		context_instance=RequestContext(request))

@login_required
def solution_detail(request,solution_id,full):
	solution = get_object_or_404(Solution, pk=solution_id)	
	if not (solution.author == request.user or request.user.is_trainer or request.user.is_superuser or (solution.author.tutorial and solution.author.tutorial.tutors.filter(id=request.user.id))):
		return access_denied(request)

        if full and not (request.user.is_trainer or request.user.is_tutor or request.user.is_superuser):
		return access_denied(request)

        accept_all_solutions = get_settings().accept_all_solutions

	if (request.method == "POST"):
                if solution.final or solution.testupload or solution.task.expired():
                    return access_denied(request)
                if not (solution.accepted or accept_all_solutions):
                    return access_denied(request)
		solution.copy()
		return HttpResponseRedirect(reverse('solution_list', args=[solution.task.id]))
	else:
		attestations = Attestation.objects.filter(solution__task=solution.task, author__tutored_tutorials=request.user.tutorial)
		attestationsPublished = attestations[0].published if attestations else False

                return render_to_response(
                    "solutions/solution_detail.html",
                    {
                        "solution": solution,
                        "attestationsPublished": attestationsPublished,
                        "accept_all_solutions": accept_all_solutions,
                        "full":full
                    },
                    context_instance=RequestContext(request))

@login_required
def solution_download(request,solution_id,full):
	solution = get_object_or_404(Solution, pk=solution_id)	
        if (not (solution.author == request.user or request.user.is_tutor or request.user.is_trainer)):
		return access_denied(request)
	zip_file = get_solutions_zip([solution], full and (request.user.is_tutor or request.user.is_trainer))
	response = HttpResponse(zip_file.read(), content_type="application/zip")
	response['Content-Disposition'] = 'attachment; filename=Solution.zip'
	return response

@login_required
def solution_download_for_task(request, task_id,full):
	if not (request.user.is_tutor or request.user.is_trainer):
		return access_denied(request)

	task = get_object_or_404(Task, pk=task_id)
	solutions = task.solution_set.filter(final=True)
        if not request.user.is_trainer:
		solutions = solutions.filter(author__tutorial__id__in=request.user.tutored_tutorials.values_list('id', flat=True))
	zip_file = get_solutions_zip(solutions,full)
	response = HttpResponse(zip_file.read(), content_type="application/zip")
	response['Content-Disposition'] = 'attachment; filename=Solutions.zip'
	return response


@login_required
def checker_result_list(request,task_id):
	task = get_object_or_404(Task, pk=task_id)	
        if not request.user.is_trainer and not request.user.is_superuser:
		return access_denied(request)
	else:
		users_with_checkerresults = [(user,dict(checkerresults),final_solution)              \
		for user           in User.objects.filter(groups__name='User').order_by('mat_number')          \
		for final_solution in Solution.objects.filter(author=user,final=True,task=task).values() \
		for checkerresults in [[ (result.checker, result) for result in CheckerResult.objects.all().filter(solution=final_solution['id'])]] ]

		checkers_seen = set([])
		for _, results,_  in users_with_checkerresults:
		    checkers_seen |= set(results.keys())
		checkers_seen = sorted(checkers_seen, key=lambda checker: checker.order)

		for i,(user,results,final_solution) in enumerate(users_with_checkerresults):
			users_with_checkerresults[i] = (user,
			                                [results[checker] if checker in results else None for (checker) in checkers_seen],
			                                final_solution)

		return render_to_response("solutions/checker_result_list.html", {"users_with_checkerresults": users_with_checkerresults,  'checkers_seen':checkers_seen, "task":task},context_instance=RequestContext(request))

@staff_member_required
def solution_run_checker(request,solution_id):
	solution = Solution.objects.get(pk=solution_id)
	check(solution,True)
	return HttpResponseRedirect(reverse('solution_detail_full', args=[solution_id]))
