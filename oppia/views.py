# oppia/views.py
import csv
import datetime
import json
import os
import oppia
import tablib
import logging

from dateutil.relativedelta import relativedelta

from django import forms
from django.conf import settings
from django.contrib.auth import (authenticate, logout, views)
from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib import messages 

#from django.core.servers.basehttp import FileWrapper
from wsgiref.util import FileWrapper
from django.core.urlresolvers import reverse
from django.db.models import Q, Count, Max, Avg, Min
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render,render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from oppia.forms import UploadCourseStep1Form, UploadCourseStep2Form, ScheduleForm, DateRangeForm, DateRangeIntervalForm,UserRoleForm
from oppia.forms import ActivityScheduleForm, CohortForm
from oppia.models import Course, Tracker, Tag, CourseTag, Schedule, CourseManager, CourseCohort, SchoolCode, BaselineSurvey, Section
from oppia.models import ActivitySchedule, Activity, Cohort, Participant, Points, UserProfile
from oppia.permissions import *
from oppia.quiz.models import Quiz, QuizAttempt, QuizAttemptResponse

from uploader import handle_uploaded_file

def server_view(request):
    return render_to_response('oppia/server.html',  
                              {'settings': settings}, 
                              content_type="application/json", 
                              context_instance=RequestContext(request))

def about_view(request):
    return render_to_response('oppia/about.html',  
                              {'settings': settings}, 
                              context_instance=RequestContext(request))
    
def home_view(request):
    activity = []
    if request.user.is_authenticated():
        # create profile if none exists (historical for very old users)
        try:
            up = request.user.userprofile
        except UserProfile.DoesNotExist:
            up = UserProfile()
            up.user= request.user
            up.save()
        
        # if user is student redirect to their scorecard
        if up.is_student_only():
            return HttpResponseRedirect(reverse('profile_user_activity', args=[request.user.id]))
        
        # is user is teacher redirect to teacher home
        if up.is_teacher_only():
            return HttpResponseRedirect(reverse('oppia_teacher_home'))
        
        start_date = timezone.now() - datetime.timedelta(days=31)
        end_date = timezone.now()
        interval = 'days'
        if request.method == 'POST':
            form = DateRangeIntervalForm(request.POST)
            if form.is_valid():
                start_date = form.cleaned_data.get("start_date")  
                start_date = datetime.datetime.strptime(start_date,"%Y-%m-%d")
                end_date = form.cleaned_data.get("end_date")
                end_date = datetime.datetime.strptime(end_date,"%Y-%m-%d")   
                interval =  form.cleaned_data.get("interval")          
        else:
            data = {}
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['interval'] = interval
            form = DateRangeIntervalForm(initial=data)
        
        if interval == 'days':
            no_days = (end_date-start_date).days + 1
            trackers = Tracker.objects.filter(course__isnull=False, 
                                              course__is_draft=False, 
                                              user__is_staff=False, 
                                              course__is_archived=False,
                                              tracker_date__gte=start_date,
                                              tracker_date__lte=end_date).extra({'activity_date':"date(tracker_date)"}).values('activity_date').annotate(count=Count('id'))
            for i in range(0,no_days,+1):
                temp = start_date + datetime.timedelta(days=i)
                count = next((dct['count'] for dct in trackers if dct['activity_date'] == temp.date()), 0)
                activity.append([temp.strftime("%d %b %Y"),count])
        else:
            delta = relativedelta(months=+1)
            
            no_months = 0
            tmp_date = start_date
            while tmp_date <= end_date:
                print tmp_date
                tmp_date += delta
                no_months += 1
                
            for i in range(0,no_months,+1):
                temp = start_date + relativedelta(months=+i)
                month = temp.strftime("%m")
                year = temp.strftime("%Y")
                count = Tracker.objects.filter(course__isnull=False,
                                               course__is_draft=False,
                                               user__is_staff=False,
                                               course__is_archived=False,
                                               tracker_date__month=month,
                                               tracker_date__year=year).count()
                activity.append([temp.strftime("%b %Y"),count])
    else:
        form = None
    leaderboard = Points.get_leaderboard(10)
    return render_to_response('oppia/home.html',
                              {'form': form,
                               'activity_graph_data': activity, 
                               'leaderboard': leaderboard}, 
                              context_instance=RequestContext(request))

def teacher_home_view(request):
    cohorts, response = get_cohorts(request)
    if response is not None:
        return response
    
    start_date = timezone.now() - datetime.timedelta(days=31)
    end_date = timezone.now()
        
    # get student activity
    activity = []
    no_days = (end_date-start_date).days + 1
    students =  User.objects.filter(participant__role=Participant.STUDENT, participant__cohort__in=cohorts).distinct()   
    courses = Course.objects.filter(coursecohort__cohort__in=cohorts).distinct()
    trackers = Tracker.objects.filter(course__in=courses, 
                                       user__in=students,  
                                       tracker_date__gte=start_date,
                                       tracker_date__lte=end_date).extra({'activity_date':"date(tracker_date)"}).values('activity_date').annotate(count=Count('id'))
    for i in range(0,no_days,+1):
        temp = start_date + datetime.timedelta(days=i)
        count = next((dct['count'] for dct in trackers if dct['activity_date'] == temp.date()), 0)
        activity.append([temp.strftime("%d %b %Y"),count])
    
    return render_to_response('oppia/home-teacher.html',
                              {'cohorts': cohorts,
                               'activity_graph_data': activity, }, 
                              context_instance=RequestContext(request))

def courses_list_view(request):
    courses, response = can_view_courses_list(request) 
    if response is not None:
        return response
           
    tag_list = Tag.objects.all().exclude(coursetag=None).order_by('name')
    courses_list = []
    for course in courses:
        obj = {}
        obj['course'] = course
        access_detail, response = can_view_course_detail(request,course.id)
        if access_detail is not None:
            obj['access_detail'] = True
        else:
            obj['access_detail'] = False
        courses_list.append(obj)
        
    return render_to_response('oppia/course/courses-list.html',
                              {'courses_list': courses_list, 
                               'tag_list': tag_list}, 
                              context_instance=RequestContext(request))
def users_list_view(request):
    user_list=[]
    if request.user.is_superuser:
        user_list = UserProfile.objects.select_related('user')  
    else:
        user_list = UserProfile.objects.select_related('user').filter(school_code=request.user.userprofile.school_code)
    if request.method == 'POST':
        form = UserRoleForm(request.POST)
        if form.is_valid():
            role=form.cleaned_data.get("role")  
            if request.user.is_superuser:
                user_list = UserProfile.objects.select_related('user').filter(status=role)  
            else:
                user_list = UserProfile.objects.select_related('user').filter(school_code=request.user.userprofile.school_code,status=role)
        else:
            if request.user.is_superuser:
                user_list = UserProfile.objects.select_related('user')  
            else:
                user_list = UserProfile.objects.select_related('user').filter(school_code=request.user.userprofile.school_code)
    else:
        form = UserRoleForm()
    return render_to_response('oppia/userreport.html',
                              {'user_list': user_list,
                               'form':form,
                              'title':"Select User to view transcript"}, 
                              context_instance=RequestContext(request))
def user_details_view(request,user_id):
    view_user, response = get_user(request, user_id)
    profile=UserProfile.objects.get(user=view_user)
    try:
      version=Tracker.objects.filter(user=view_user,agent__contains='OppiaMobile Android').latest('submitted_date')
    except Tracker.DoesNotExist:
      version= None
    try:
      device=Tracker.objects.filter(user=view_user,agent__contains='Dalvik').latest('submitted_date')
    except Tracker.DoesNotExist:
      device= None
    try:
      school=SchoolCode.objects.filter(school_code=profile.school_code)
    except SchoolCode.DoesNotExist:
      school=None
    if response is not None:
        return response
    
    cohort_courses, other_courses, all_courses = get_user_courses(request, view_user) 
    
    courses = []
    quizzes = []
    for course in all_courses:

        completed=course.get_activities_completed(course,view_user)+course.get_no_quizzes_completed(course,view_user)
        total=course.get_no_activities()+course.get_no_quizzes()
        percentage=(float(completed)/100)*total
        data = {'course': course,
                'no_quizzes_completed': course.get_no_quizzes_completed(course,view_user),
                'pretest_score': course.get_pre_test_score(course,view_user),
                'no_activities_completed': course.get_activities_completed(course,view_user),
                'no_quizzes_completed': course.get_no_quizzes_completed(course,view_user),
                'no_points': course.get_points(course,view_user),
                'no_badges': course.get_badges(course,view_user),
                'percentage_complete':float("{0:.6f}".format(percentage)),}
        courses.append(data)
        course_value = can_view_course(request, course.id)
        act_quizzes = Activity.objects.filter(section__course=course_value,type=Activity.QUIZ).order_by('section__order','order')
        for aq in act_quizzes:
            quiz = Quiz.objects.filter(quizprops__value=aq.digest, quizprops__name="digest")
            attempts = QuizAttempt.objects.filter(quiz=quiz, user=view_user)
            if attempts.count() > 0:
                max_score = 100*float(attempts.aggregate(max=Max('score'))['max']) / float(attempts[0].maxscore)
                min_score = 100*float(attempts.aggregate(min=Min('score'))['min']) / float(attempts[0].maxscore)
                avg_score = 100*float(attempts.aggregate(avg=Avg('score'))['avg']) / float(attempts[0].maxscore)
                first_date = attempts.aggregate(date=Min('attempt_date'))['date']
                recent_date = attempts.aggregate(date=Max('attempt_date'))['date']
                first_score = 100*float(attempts.filter(attempt_date = first_date)[0].score) / float(attempts[0].maxscore)
                latest_score = 100*float(attempts.filter(attempt_date = recent_date)[0].score) / float(attempts[0].maxscore)
            else:
                max_score = None
                min_score = None
                avg_score = None
                first_score = None
                latest_score = None
            
            quiz = {'quiz': aq,
                        'course_value':course_value,
                        'no_attempts': attempts.count(),
                        'max_score': max_score,
                        'min_score': min_score,
                        'first_score': first_score,
                        'latest_score': latest_score,
                        'avg_score': avg_score,
                  }
            quizzes.append(quiz);
   
    return render_to_response('oppia/userdetails.html',
                              {'view_user': view_user,
                              'title':'Student Transcript',
                              'profile':profile,
                              'version':version,
                              'device':device,
                              'courses': courses, 
                              'quizzes':quizzes,
                            }, 
                              context_instance=RequestContext(request))


def final_quiz_scores_view(request):
    quizzes=[]
    if request.user.is_superuser:
      tracker_quiz=Tracker.objects.filter(type="quiz", activity_title__contains='Final').annotate(date=Max('submitted_date')).select_related()
    else:
      tracker_quiz=Tracker.objects.filter(type="quiz", activity_title__contains='Final', user__userprofile__school_code=request.user.userprofile.school_code).annotate(date=Max('submitted_date')).select_related()
   
      
    start_date = datetime.datetime.now() - datetime.timedelta(days=31)
    end_date = datetime.datetime.now()
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data.get("start_date")  
            start_date = datetime.datetime.strptime(start_date,"%Y-%m-%d")
            end_date = form.cleaned_data.get("end_date")
            end_date = datetime.datetime.strptime(end_date,"%Y-%m-%d") 
            if request.user.is_superuser:
                trackers = Tracker.objects.filter(type="quiz", activity_title__contains='Final',tracker_date__gte=start_date, tracker_date__lte=end_date).annotate(date=Max('submitted_date')).select_related()
            else:
                trackers = Tracker.objects.filter(type="quiz", activity_title__contains='Final' , user__userprofile__school_code=request.user.userprofile.school_code,tracker_date__gte=start_date, tracker_date__lte=end_date).annotate(date=Max('submitted_date')).select_related()
        else:
            if request.user.is_superuser:
                trackers = Tracker.objects.filter(type="quiz", activity_title__contains='Final').annotate(date=Max('submitted_date')).select_related()         
            else:
                trackers = Tracker.objects.filter(type="quiz", activity_title__contains='Final', user__userprofile__school_code=request.user.userprofile.school_code).annotate(date=Max('submitted_date')).select_related()      
    else:
        data = {}
        data['start_date'] = start_date
        data['end_date'] = end_date
        form = DateRangeForm(initial=data)
        if request.user.is_superuser:
            trackers = Tracker.objects.filter(type="quiz", activity_title__contains='Final').annotate(date=Max('submitted_date')).select_related()
        else:
            trackers = Tracker.objects.filter(type="quiz", activity_title__contains='Final', user__userprofile__school_code=request.user.userprofile.school_code).annotate(date=Max('submitted_date')).select_related()
    for t in trackers:
      profile=UserProfile.objects.get(user_id=t.user_id)
      quiz_id=json.loads(t.data)
      quiz=QuizAttempt.objects.filter(quiz_id=quiz_id['quiz_id'], user_id=t.user_id).values('quiz_id')

      data={'tracker':t,
              'profile':profile,
              'score':quiz_id['score'],
              'quiz':quiz,
              'attempts':quiz.count(),
            }
      quizzes.append(data)
    return render_to_response('oppia/finalquizscores.html',
                              {'data': quizzes,
                               'form': form,
                               #'users':users,
                              'title':"Final Quiz Scores"}, 
                              context_instance=RequestContext(request))
def filter_final_quiz_scores_view(request):
  quizzes=[]
  if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data.get("start_date")  
            #start_date = datetime.datetime.strptime(start_date,"%Y-%m-%d")
            end_date = form.cleaned_data.get("end_date")
            #end_date = datetime.datetime.strptime(end_date,"%Y-%m-%d") 
            tracker_quiz = Tracker.objects.filter(type="quiz", activity_title__contains='Final',tracker_date__range=[start_date, end_date]).annotate(date=Max('submitted_date')).select_related()
        else:
            tracker_quiz = Tracker.objects.filter(type="quiz", activity_title__contains='Final').annotate(date=Max('submitted_date')).select_related()
      
        for t in tracker_quiz:
          profile=UserProfile.objects.get(user_id=t.user_id)
          quiz_id=json.loads(t.data)
          quiz=QuizAttempt.objects.filter(quiz_id=quiz_id['quiz_id'], user_id=t.user_id).values('quiz_id')

          data={'tracker':t,
            'profile':profile,
            'score':quiz_id['score'],
            'quiz':quiz,
            'attempts':quiz.count(),
            }
          quizzes.append(data)
          return render_to_response('oppia/finalquizscores.html',
                              {'data': quizzes,
                              'form': form,
                              'title':"Final Quiz Scores"}, 
                              context_instance=RequestContext(request))
def quiz_summary_view(request):
    if request.user.is_superuser:
        tracker_quiz=Tracker.objects.raw('select * , count(t.user_id) as no_users from oppia_tracker t where type="quiz" group by t.activity_title, t.course_id,t.section_title')   
    else:
        tracker_quiz=Tracker.objects.raw('select * , count(t.user_id) as no_users from oppia_tracker t, oppia_userprofile up where type="quiz" and up.user_id=t.user_id and up.school_code='+"'"+request.user.userprofile.school_code+"'"+' group by t.activity_title, t.course_id,t.section_title')   
    quizzes=[]
    for t in tracker_quiz:
      quiz_id=json.loads(t.data)
     
      #quiz=QuizAttempt.objects.raw('select id,AVG(score) as score_avg, count(quiz_id) as attempts from quiz_quizattempt where quiz_id='+str(quiz_id['quiz_id'])+' and user_id='+str(t.user_id)+' group by quiz_id')
      try:
        course=Course.objects.get(pk=t.course_id)
      except Course.DoesNotExist:
        course=None
      try:
        quiz=QuizAttempt.objects.filter(quiz_id=quiz_id['quiz_id']).values('quiz_id').annotate(score_avg=Avg('score')).annotate(attempts=Count('quiz_id'))
      except QuizAttempt.DoesNotExist:
        quiz=None

      data={'tracker':t,
            'quiz':list(quiz),
            'course':course,
            }
      quizzes.append(data)
    return render_to_response('oppia/quizsummary.html',
                              {'data': quizzes,
                              'title':"Quiz Summary"}, 
                              context_instance=RequestContext(request))
def learning_center_access_view(request):
    #tracker=Tracker.objects.raw('select t.*, c.title, up.status,up.year_group, u.first_name,u.last_name, u.is_active  from oppia_tracker t, oppia_userprofile up, auth_user u, oppia_course c where (t.type="quiz" or t.type="page") and up.user_id=t.user_id and u.id=t.user_id and t.course_id=c.id')  
    access=[] 
    if request.user.is_superuser:
        trackers=Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'))
    else:
        trackers=Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'), user__userprofile__school_code=request.user.userprofile.school_code)
    start_date = datetime.datetime.now() - datetime.timedelta(days=31)
    end_date = datetime.datetime.now()
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data.get("start_date")  
            start_date = datetime.datetime.strptime(start_date,"%Y-%m-%d")
            end_date = form.cleaned_data.get("end_date")
            end_date = datetime.datetime.strptime(end_date,"%Y-%m-%d") 
            if request.user.is_superuser:
                trackers = Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'),submitted_date__gte=start_date, submitted_date__lte=end_date)
            else:
                trackers = Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'),submitted_date__gte=start_date, submitted_date__lte=end_date,user__userprofile__school_code=request.user.userprofile.school_code)
        else:
            if request.user.is_superuser:
                trackers = Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'))
            else:
                trackers=Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'), user__userprofile__school_code=request.user.userprofile.school_code)
    else:
        data = {}
        data['start_date'] = start_date
        data['end_date'] = end_date
        form = DateRangeForm(initial=data)
        if request.user.is_superuser:
            trackers = Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'))
        else:
            trackers=Tracker.objects.select_related('course','user').filter(Q(type='quiz')|Q(type='page'), user__userprofile__school_code=request.user.userprofile.school_code)
    for t in trackers:
      profile=UserProfile.objects.get(user_id=t.user_id)
      data={'tracker':t,
              'profile':profile,
            }
      access.append(data)
    return render_to_response('oppia/learning-center-access.html',
                              {'data': access,
                              'form':form,
                              'title':"Learning Center Access"}, 
                              context_instance=RequestContext(request))
def learning_summary_view(request):
    courses=Course.objects.all() 
    access=[]
    if request.user.is_superuser:
        acts = Activity.objects.filter(baseline=False).values_list('digest')
        downloads=Tracker.objects.filter(type='download', course_id__isnull=False).count()   
        app_downloads=UserProfile.objects.filter(imei__isnull=False).count()   
        started=Tracker.objects.filter(completed=False,type="page",digest__in=acts).values_list('user_id').distinct().count()
        completed=Tracker.objects.filter(completed=True,type="page",digest__in=acts).values_list('user_id').distinct().count()
        quizzes=Tracker.objects.filter(digest__in=acts, type=Activity.QUIZ).values_list('user_id').distinct().count()
    else:
        acts = Activity.objects.filter(baseline=False).values_list('digest')
        downloads=Tracker.objects.filter(type='download', course_id__isnull=False,user__userprofile__school_code=request.user.userprofile.school_code).count()   
        app_downloads=UserProfile.objects.filter(imei__isnull=False,user__userprofile__school_code=request.user.userprofile.school_code).count()   
        started=Tracker.objects.filter(completed=False,type="page",user__userprofile__school_code=request.user.userprofile.school_code).values_list('user_id').distinct().count()
        completed=Tracker.objects.filter(completed=True,type="page",user__userprofile__school_code=request.user.userprofile.school_code).values_list('user_id').distinct().count()
        quizzes=Tracker.objects.filter(type=Activity.QUIZ, user__userprofile__school_code=request.user.userprofile.school_code).values_list('user_id').distinct().count()
    for c in courses:
        if request.user.is_superuser:
            started_modules=Tracker.objects.filter(course=c,type="page",completed=False).values_list('digest').distinct().count()
            completed_modules=Tracker.objects.filter(course=c,type="page",completed=True).values_list('digest').distinct().count()
            no_quizzes= Tracker.objects.filter(course=c,type="quiz").values_list('digest').distinct().count()
            no_downloads=Tracker.objects.filter(course=c, type='download').count()
            no_media_downloads=Tracker.objects.filter(course=c, type='media').count()
            data={'course':c,
            'started_modules':started_modules,
            'completed_modules':completed_modules,
            'no_quizzes':no_quizzes,
            'no_downloads':no_downloads,
            'no_media_downloads':no_media_downloads,
            }
            access.append(data)
        else:
            started_modules=Tracker.objects.filter(course=c,type="page",completed=False,user__userprofile__school_code=request.user.userprofile.school_code).values_list('digest').distinct().count()
            completed_modules=Tracker.objects.filter(course=c,type="page",completed=True,user__userprofile__school_code=request.user.userprofile.school_code).values_list('digest').distinct().count()
            no_quizzes= Tracker.objects.filter(course=c,type="quiz",user__userprofile__school_code=request.user.userprofile.school_code).values_list('digest').distinct().count()
            no_downloads=Tracker.objects.filter(course=c, type='download',user__userprofile__school_code=request.user.userprofile.school_code).count()
            no_media_downloads=Tracker.objects.filter(course=c, type='media',user__userprofile__school_code=request.user.userprofile.school_code).count()
            data={'course':c,
            'started_modules':started_modules,
            'completed_modules':completed_modules,
            'no_quizzes':no_quizzes,
            'no_downloads':no_downloads,
            'no_media_downloads':no_media_downloads,
            }
            access.append(data)
    return render_to_response('oppia/learning-summary.html',
                              {'data': access,
                                'downloads':downloads,
                                'app_downloads':app_downloads,
                                'started':started,
                                'completed':completed,
                                'quizzes':quizzes,
                              'title':"Learning Summary"}, 
                              context_instance=RequestContext(request))
def learning_summary_by_course_view(request, course_id):
    course=Course.objects.get(pk=course_id) 
    if request.user.is_superuser:
        started_modules=Tracker.objects.raw('select *, count(t.user_id) as users from oppia_tracker t where  t.completed=0 and t.course_id='+course_id+' and (t.type="page") group by t.digest')
        completed_modules=Tracker.objects.raw('select *, count(t.user_id) as users  from oppia_tracker t where  t.completed=1 and t.course_id='+course_id+' and (t.type="page") group by t.digest')
        
    else:
        started_modules=Tracker.objects.raw('select *, count(t.user_id) as users from oppia_tracker t, oppia_userprofile up where  t.completed=0 and t.user_id=up.user_id, and up.school_code='+"'"+request.user.userprofile.school_code+"'"+' and t.course_id='+course_id+' and (t.type="page") group by t.digest')
        completed_modules=Tracker.objects.raw('select *, count(t.user_id) as users  from oppia_tracker t, oppia_userprofile up where  t.completed=1 and t.user_id=up.user_id, and up.school_code='+"'"+request.user.userprofile.school_code+"'"+'and t.course_id='+course_id+' and (t.type="page") group by t.digest')

    return render_to_response('oppia/learning-summary-course.html',
                              {'started_modules': started_modules,
                               'completed_modules': completed_modules,
                                'course':course,}, 
                              context_instance=RequestContext(request))
def report_schools_list_view(request):
    school_list = UserProfile.objects.raw('select u.id,count(u.user_id) as c, s.school_name from oppia_userprofile u,oppia_schoolcode s where not u.school_code="-----" and u.school_code=s.school_code group by u.school_code')

    return render_to_response('oppia/schools_per_user_report.html',
                              {'school_list': school_list,
                              'title':"Users Registered Per School"}, 
                              context_instance=RequestContext(request))
def users_registered_per_school(request, school_code):
    cohort_list=[]
    school_list =  UserProfile.objects.raw("select up.*,u.*, s.school_name from oppia_userprofile up,auth_user u,oppia_schoolcode s where not up.school_code='-----' and up.school_code=s.school_code and up.school_code='"+school_code+"' group by up.user_id")
    courses=Course.objects.all()
    if request.method == 'POST':
        form = UserRoleForm(request.POST)
        if form.is_valid():
            role=form.cleaned_data.get("role")  
            school_list =  UserProfile.objects.raw("select up.*,u.*, s.school_name from oppia_userprofile up,auth_user u,oppia_schoolcode s where not up.school_code='-----' and up.school_code=s.school_code and up.status='"+role+"' and up.school_code='"+school_code+"' group by up.user_id") 
        else:
            school_list =  UserProfile.objects.raw("select up.*,u.*, s.school_name from oppia_userprofile up,auth_user u,oppia_schoolcode s where not up.school_code='-----' and up.school_code=s.school_code and up.school_code='"+school_code+"' group by up.user_id")
    else:
        form = UserRoleForm()
        
       
    return render_to_response('oppia/users_registered_per_school.html',
                              {'school_list': school_list,
                              'form':form,
                              'courses':courses,
                              'title':"Users Registered in "+school_code}, 
                              context_instance=RequestContext(request))
def report_completed_module_view(request):
    module_list = Activity.objects.raw('select a.id, a.title as mtitle,c.title as ctitle,count(t.user_id) as c from oppia_activity a, oppia_tracker t,oppia_course c where t.digest=a.digest and t.completed=1 and c.id=t.course_id group by  a.title')    
    return render_to_response('oppia/completed_modules_report.html',
                              {'module_list': module_list,
                              'title':"Number of Modules completed"}, 
                              context_instance=RequestContext(request))
def report_started_module_view(request):
    module_list = Activity.objects.raw('select a.id, a.title as mtitle,c.title as ctitle,count(t.user_id) as c from oppia_activity a, oppia_tracker t,oppia_course c where t.digest=a.digest and t.completed=0 and c.id=t.course_id group by  a.title')    
    return render_to_response('oppia/completed_modules_report.html',
                              {'module_list': module_list,
                              'title':"Number of Modules started"}, 
                              context_instance=RequestContext(request))
def report_survey_results_view(request):
    if request.user.is_superuser: 
        module_list = BaselineSurvey.objects.all()
      
    else:
        module_list = BaselineSurvey.objects.raw('Select * from oppia_baselinesurvey b, oppia_userprofile up where b.user_id_id=up.user_id and up.school_code='+request.user.userprofile.school_code)
    return render_to_response('oppia/survey-results.html',
                              {'module_list': module_list,
                              'title':"Survey Results"}, 
                              context_instance=RequestContext(request))
def about_view(request):
    return render_to_response('oppia/about.html',
                              {'title':"About"}, 
                              context_instance=RequestContext(request))

def course_download_view(request, course_id):
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise Http404()
    file_to_download = course.getAbsPath();
    wrapper = FileWrapper(file(file_to_download))
    response = HttpResponse(wrapper, content_type='application/zip')
    response['Content-Length'] = os.path.getsize(file_to_download)
    response['Content-Disposition'] = 'attachment; filename="%s"' %(course.filename)
    return response

def tag_courses_view(request, tag_id):
    courses, response = can_view_courses_list(request) 
    if response is not None:
        return response
    courses = courses.filter(coursetag__tag__pk=tag_id)
    courses_list = []
    for course in courses:
        obj = {}
        obj['course'] = course
        access_detail, response = can_view_course_detail(request,course.id)
        if access_detail is not None:
            obj['access_detail'] = True
        else:
            obj['access_detail'] = False
        courses_list.append(obj)
    tag_list = Tag.objects.all().order_by('name')
    return render_to_response('oppia/course/courses-list.html',
                              {'courses_list': courses_list, 
                               'tag_list': tag_list, 
                               'current_tag': id}, 
                              context_instance=RequestContext(request))
        
def upload_step1(request):
    if not request.user.userprofile.get_can_upload():
        return HttpResponse('Unauthorized', status=401)
        
    if request.method == 'POST':
        form = UploadCourseStep1Form(request.POST,request.FILES)
        if form.is_valid(): # All validation rules pass
            extract_path = os.path.join(settings.COURSE_UPLOAD_DIR, 'temp', str(request.user.id))
            course = handle_uploaded_file(request.FILES['course_file'], extract_path, request, request.user)
            if course:
                return HttpResponseRedirect(reverse('oppia_upload2', args=[course.id])) # Redirect after POST
            else:
                os.remove(settings.COURSE_UPLOAD_DIR + request.FILES['course_file'].name)
    else:
        form = UploadCourseStep1Form() # An unbound form

    return render_to_response('oppia/upload.html', 
                              {'form': form,
                               'title':_(u'Upload Course - step 1')},
                              context_instance=RequestContext(request))

def upload_step2(request, course_id):
    if not request.user.userprofile.get_can_upload():
        return HttpResponse('Unauthorized', status=401)
        
    course = Course.objects.get(pk=course_id)
    
    if request.method == 'POST':
        form = UploadCourseStep2Form(request.POST,request.FILES)
        if form.is_valid(): # All validation rules pass
            is_draft = form.cleaned_data.get("is_draft")
            if course:
                #add the tags
                tags = form.cleaned_data.get("tags").strip().split(",")
                is_draft = form.cleaned_data.get("is_draft")
                if len(tags) > 0:
                    course.is_draft = is_draft
                    course.course_tag=form.cleaned_data.get("tags")
                    course.save()
                    for t in tags:
                        try: 
                            tag = Tag.objects.get(name__iexact=t.strip())
                        except Tag.DoesNotExist:
                            tag = Tag()
                            tag.name = t.strip()
                            tag.created_by = request.user
                            tag.save()
                        # add tag to course
                        try:
                            ct = CourseTag.objects.get(course=course,tag=tag)
                        except CourseTag.DoesNotExist:
                            ct = CourseTag()
                            ct.course = course
                            ct.tag = tag
                            ct.save()
                return HttpResponseRedirect('success/') # Redirect after POST
    else:
        form = UploadCourseStep2Form(initial={'tags':course.get_tags(),
                                    'is_draft':course.is_draft,}) # An unbound form

    return render_to_response('oppia/upload.html', 
                              {'form': form,
                               'title':_(u'Upload Course - step 2')},
                              context_instance=RequestContext(request))


def recent_activity(request,course_id):
    #view_user = get_user(request, user_id)
    course, response = can_view_course_detail(request, course_id)
    leaderboard = Points.get_leaderboard(0, course)

    if response is not None:
        return response
    
    start_date = datetime.datetime.now() - datetime.timedelta(days=31)
    end_date = datetime.datetime.now()
    interval = 'days'

    if request.method == 'POST':
        form = DateRangeIntervalForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data.get("start_date")  
            start_date = datetime.datetime.strptime(start_date,"%Y-%m-%d")
            end_date = form.cleaned_data.get("end_date")
            end_date = datetime.datetime.strptime(end_date,"%Y-%m-%d") 
            interval =  form.cleaned_data.get("interval")               
    else:
        data = {}
        data['start_date'] = start_date
        data['end_date'] = end_date
        data['interval'] = interval
        form = DateRangeIntervalForm(initial=data)
    
    dates = []
    if interval == 'days':
        no_days = (end_date-start_date).days + 1
        
        for i in range(0,no_days,+1):
            temp = start_date + datetime.timedelta(days=i)
            day = temp.strftime("%d")
            month = temp.strftime("%m")
            year = temp.strftime("%Y")
            count_objs = Tracker.objects.filter(course=course,tracker_date__day=day,tracker_date__month=month,tracker_date__year=year).values('type').annotate(total=Count('type'))
            count_activity = {'page':0, 'quiz':0, 'media':0, 'resource':0, 'monitor': 0, 'total':0}
            for co in count_objs:
                if co['type'] in count_activity:
                    count_activity[co['type']] = count_activity[co['type']] + co['total']
                    count_activity['total'] = count_activity['total'] + co['total']
                else:
                    count_activity[co['type']] = 0
                    count_activity[co['type']] = count_activity[co['type']] + co['total']
                    count_activity['total'] = count_activity['total'] + co['total']
            
            dates.append([temp.strftime("%d %b %y"),count_activity])
    else:
        delta = relativedelta(months=+1)  
        no_months = 0
        tmp_date = start_date
        while tmp_date <= end_date:
            print tmp_date
            tmp_date += delta
            no_months += 1
            
        for i in range(0,no_months,+1):
            temp = start_date + relativedelta(months=+i)
            month = temp.strftime("%m")
            year = temp.strftime("%Y")
            count_objs = Tracker.objects.filter(course=course,tracker_date__month=month,tracker_date__year=year).values('type').annotate(total=Count('type'))
            count_activity = {'page':0, 'quiz':0, 'media':0, 'resource':0, 'monitor': 0, 'total':0}
            for co in count_objs:
                if co['type'] in count_activity:
                    count_activity[co['type']] = count_activity[co['type']] + co['total']
                    count_activity['total'] = count_activity['total'] + co['total']
                else:
                    count_activity[co['type']] = 0
                    count_activity[co['type']] = count_activity[co['type']] + co['total']
                    count_activity['total'] = count_activity['total'] + co['total']
            
            dates.append([temp.strftime("%b %y"),count_activity])
        
        
    
    return render_to_response('oppia/course/activity.html',
                              {'course': course,
                               'form': form,
                                'data':dates, 
                                'leaderboard':leaderboard,}, 
                              context_instance=RequestContext(request))

def recent_activity_detail(request,course_id):
    course, response = can_view_course_detail(request, course_id)
    
    if response is not None:
        return response
        
    start_date = datetime.datetime.now() - datetime.timedelta(days=31)
    end_date = datetime.datetime.now()
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data.get("start_date")  
            start_date = datetime.datetime.strptime(start_date,"%Y-%m-%d")
            end_date = form.cleaned_data.get("end_date")
            end_date = datetime.datetime.strptime(end_date,"%Y-%m-%d") 
            trackers = Tracker.objects.filter(course=course,tracker_date__gte=start_date, tracker_date__lte=end_date).order_by('-tracker_date')
        else:
            trackers = Tracker.objects.filter(course=course).order_by('-tracker_date')             
    else:
        data = {}
        data['start_date'] = start_date
        data['end_date'] = end_date
        form = DateRangeForm(initial=data)
        trackers = Tracker.objects.filter(course=course).order_by('-tracker_date')
        
    paginator = Paginator(trackers, 25)
    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        tracks = paginator.page(page)
        for t in tracks:  
            t.data_obj = []
            try:
                data_dict = json.loads(t.data)
                for key, value in data_dict.items():
                    t.data_obj.append([key,value])
            except ValueError:
                pass
            t.data_obj.append(['agent',t.agent])
            t.data_obj.append(['ip',t.ip])
    except (EmptyPage, InvalidPage):
        tracks = paginator.page(paginator.num_pages)
    
    return render_to_response('oppia/course/activity-detail.html',
                              {'course': course,
                               'form': form, 
                               'page':tracks,}, 
                              context_instance=RequestContext(request))


def export_tracker_detail(request,course_id):
    course, response = can_view_course_detail(request, course_id)
    
    if response is not None:
        return response
    
    headers = ('Date', 'UserId', 'Type', 'Activity Title', 'Section Title', 'Time Taken', 'IP Address', 'User Agent', 'Language')
    data = []
    data = tablib.Dataset(*data, headers=headers)
    trackers = Tracker.objects.filter(course=course).order_by('-tracker_date')
    for t in trackers:
        try:
            data_dict = json.loads(t.data)
            if 'lang' in data_dict:
                lang = data_dict['lang']
            else:
                lang = ""
            data.append((t.tracker_date.strftime('%Y-%m-%d %H:%M:%S'), t.user.id, t.type, t.get_activity_title(), t.get_section_title(), t.time_taken, t.ip, t.agent, lang))
        except ValueError:
            data.append((t.tracker_date.strftime('%Y-%m-%d %H:%M:%S'), t.user.id, t.type, "", "", t.time_taken, t.ip, t.agent, ""))
            
    response = HttpResponse(data.xls, content_type='application/vnd.ms-excel;charset=utf-8')
    response['Content-Disposition'] = "attachment; filename=export.xls"

    return response
    
def schedule(request,course_id):
    course = check_owner(request,course_id)    
    schedules = Schedule.objects.filter(course=course)
    return render_to_response('oppia/course/schedules.html',{'course': course,'schedules':schedules,}, context_instance=RequestContext(request))
    
def schedule_add(request,course_id):
    course = check_owner(request,course_id)
    ActivityScheduleFormSet = formset_factory(ActivityScheduleForm, extra=0)

    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        formset = ActivityScheduleFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            schedule = Schedule()
            schedule.course = course
            schedule.title = form.cleaned_data.get("title").strip()
            schedule.default = form.cleaned_data.get("default")
            schedule.created_by = request.user
            
            # remvoe any existing default for this schedule
            if schedule.default:
                Schedule.objects.filter(course=course).update(default=False)
                
            schedule.save()
            
            for f in formset:
                act_sched = ActivitySchedule()
                start_date = f.cleaned_data.get("start_date")
                end_date = f.cleaned_data.get("end_date")
                digest = f.cleaned_data.get("digest")
                if start_date is not None:
                    act_sched = ActivitySchedule()
                    act_sched.schedule = schedule
                    act_sched.start_date = start_date
                    act_sched.end_date = end_date
                    act_sched.digest = digest.strip()
                    act_sched.save()
            return HttpResponseRedirect('../saved/')
    else:
        activities = Activity.objects.filter(section__course= course)
        initial = []
        section = None
        start_date = datetime.datetime.now() 
        end_date = datetime.datetime.now() + datetime.timedelta(days=7)
        for a in activities:
            if a.section != section:
                section = a.section
                start_date = start_date + datetime.timedelta(days=7)
                end_date = end_date + datetime.timedelta(days=7)
            data = {}
            data['title'] = a.title
            data['digest'] = a.digest
            data['section'] = a.section.title
            data['start_date'] = start_date
            data['end_date'] = end_date
            initial.append(data)
            form = ScheduleForm()
        formset = ActivityScheduleFormSet(initial=initial)

    return render(request, 'oppia/schedule-form.html', {'form': form, 'formset': formset,'course':course, })

def schedule_edit(request,course_id, schedule_id):
    course = check_owner(request,course_id)
    schedule = Schedule.objects.get(pk=schedule_id)
    ActivityScheduleFormSet = formset_factory(ActivityScheduleForm, extra=0)
    activities = Activity.objects.filter(section__course = course)
    
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        formset = ActivityScheduleFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            schedule.title = form.cleaned_data.get("title").strip()
            schedule.default = form.cleaned_data.get("default")
            schedule.lastupdated_date = datetime.datetime.now()
            
            # remove any existing default for this schedule
            if schedule.default:
                Schedule.objects.filter(course=course).update(default=False)
                
            schedule.save()
            
            # remove all the old schedule Activities
            ActivitySchedule.objects.filter(schedule=schedule).delete()
            
            for f in formset:
                act_sched = ActivitySchedule()
                start_date = f.cleaned_data.get("start_date")
                end_date = f.cleaned_data.get("end_date")
                digest = f.cleaned_data.get("digest")
                if start_date is not None:
                    act_sched = ActivitySchedule()
                    act_sched.schedule = schedule
                    act_sched.start_date = start_date
                    act_sched.end_date = end_date
                    act_sched.digest = digest.strip()
                    act_sched.save()
            return HttpResponseRedirect('../saved/')
    else:
        initial = []
        section = None
        for a in activities:
            if a.section != section:
                section = a.section
            data = {}
            data['title'] = a.title
            data['digest'] = a.digest
            data['section'] = a.section.title
            try:
                act_s = ActivitySchedule.objects.get(schedule=schedule,digest = a.digest)
                start_date = act_s.start_date
                end_date = act_s.end_date
            except ActivitySchedule.DoesNotExist:
                start_date = None
                end_date = None
            data['start_date'] = start_date
            data['end_date'] = end_date
            initial.append(data)
        form = ScheduleForm(initial={'title':schedule.title,
                                    'default':schedule.default})
        formset = ActivityScheduleFormSet(initial=initial)

    return render(request, 'oppia/schedule-form.html', {'form': form, 'formset': formset,'course':course, })

def schedule_saved(request, course_id, schedule_id=None):
    course = check_owner(request,course_id)
    return render_to_response('oppia/schedule-saved.html', 
                              {'course': course},
                              context_instance=RequestContext(request))
 
def cohort_list_view(request):
    if not request.user.is_staff:
        raise Http404  
    cohorts = Cohort.objects.all()
    return render_to_response('oppia/course/cohorts-list.html',
                              {'cohorts':cohorts,}, 
                              context_instance=RequestContext(request))
'''  
def cohort_add(request):
    if not can_add_cohort(request):
        return HttpResponse('Unauthorized', status=401)   
    
    if request.method == 'POST':
        form = CohortForm(request.POST,request.FILES)
        if form.is_valid(): # All validation rules pass
            request.FILES['courses'].open("rb")
            request.FILES['students'].open("rb")
            request.FILES['teachers'].open("rb")
            course_csv = csv.DictReader(request.FILES['courses'].file)
            student_csv = csv.DictReader(request.FILES['students'].file)
            teacher_csv = csv.DictReader(request.FILES['teachers'].file)
            required_fields = ['course_codes','tutors','students','courses']
            cohort = Cohort()
            cohort.start_date = form.cleaned_data.get("start_date")
            cohort.end_date = form.cleaned_data.get("end_date")
            cohort.description = form.cleaned_data.get("description")
            cohort.save()
            
            #students = form.cleaned_data.get("students").strip().split(",")
            #if len(students) > 0:
            for s in student_csv:
                try:
                    if s['students'].strip().startswith("0"):
                        student = User.objects.get(username=s['students'].strip())
                    else:
                        student = User.objects.get(username="0"+s['students'].strip())
                        participant = Participant()
                        participant.cohort = cohort
                        participant.user = student
                        participant.role = Participant.STUDENT
                        participant.save()
                except User.DoesNotExist:
                    pass
                    
            #teachers = form.cleaned_data.get("teachers").strip().split(",")
            #if len(teachers) > 0:
            for t in teacher_csv:
                try:
                    if s['tutors'].strip().startswith("0"):
                        teacher = User.objects.get(username=t['tutors'].strip())
                    else:
                        teacher = User.objects.get(username="0"+t['tutors'].strip())
                        #teacher = User.objects.get(username__contains=t['tutors'].strip())
                        participant = Participant()
                        participant.cohort = cohort
                        participant.user = teacher
                        participant.role = Participant.TEACHER
                        participant.save()
                except User.DoesNotExist:
                    pass
             
            #courses = form.cleaned_data.get("courses").strip().split(",")
            #if len(courses) > 0:
            for c in course_csv:
                try:
                    course = Course.objects.get(shortname=c['course_codes'].strip())
                    CourseCohort(cohort=cohort, course=course).save()
                except Course.DoesNotExist:
                    pass
                           
            return HttpResponseRedirect('../') # Redirect after POST
           
    else:
        form = CohortForm() # An unbound form

    return render(request, 'oppia/cohort-form.html',{'form': form,})  
'''
'''
def cohort_add(request):
    if not can_add_cohort(request):
        return HttpResponse('Unauthorized', status=401)   
    
    if request.method == 'POST':
        form = CohortForm(request.POST)
        if form.is_valid(): # All validation rules pass
            cohort = Cohort()
            cohort.start_date = form.cleaned_data.get("start_date")
            cohort.end_date = form.cleaned_data.get("end_date")
            cohort.description = form.cleaned_data.get("description").strip()
            cohort.save()
            
            students = form.cleaned_data.get("students").strip().split(",")
            if len(students) > 0:
                for s in students:
                    try:
                        student = User.objects.get(username=s.strip())
                        participant = Participant()
                        participant.cohort = cohort
                        participant.user = student
                        participant.role = Participant.STUDENT
                        participant.save()
                    except User.DoesNotExist:
                        pass
                    
            teachers = form.cleaned_data.get("teachers").strip().split(",")
            if len(teachers) > 0:
                for t in teachers:
                    try:
                        teacher = User.objects.get(username=t.strip())
                        participant = Participant()
                        participant.cohort = cohort
                        participant.user = teacher
                        participant.role = Participant.TEACHER
                        participant.save()
                    except User.DoesNotExist:
                        pass
             
            #courses = form.cleaned_data.get("courses").strip().split(",")
            courses=Course.objects.get()
            if len(courses) > 0:
                for c in courses:
                    try:
                        #course = Course.objects.get(shortname=c.strip())
                        CourseCohort(cohort=cohort, course=c).save()
                    except Course.DoesNotExist:
                        pass
                           
            return HttpResponseRedirect('../') # Redirect after POST
        else:
            #If form is not valid, clean the groups data
            form.data['teachers'] = None
            form.data['courses'] = None
            form.data['students'] = None
    else:
        form = CohortForm() # An unbound form

    return render(request, 'oppia/cohort-form.html',{'form': form,})  

'''
def cohort_add(request):
    if not can_add_cohort(request):
        return HttpResponse('Unauthorized', status=401)   
    
    if request.method == 'POST':
        form = CohortForm(request.POST)
        if form.is_valid(): # All validation rules pass
            logging.warning('Watch out!') 
            cohort = Cohort()
            cohort.start_date = form.cleaned_data.get("start_date")
            cohort.end_date = form.cleaned_data.get("end_date")
            cohort.school = form.cleaned_data.get("description")
            cohort.save()
            
            students=User.objects.filter(userprofile__school_code=form.cleaned_data.get("description"), userprofile__status="Student")
            for s in students:
                try:
                    student = User.objects.get(username=s.username)
                    participant = Participant()
                    participant.cohort = cohort
                    participant.user = student
                    participant.role = Participant.STUDENT
                    participant.save()
                except User.DoesNotExist:
                    raise Http404
                    
            teachers=User.objects.filter(userprofile__school_code=form.cleaned_data.get("description"),userprofile__status="Tutor")
            for t in teachers:
                try:
                    teacher = User.objects.get(username=t.username)
                    participant = Participant()
                    participant.cohort = cohort
                    participant.user = teacher
                    participant.role = Participant.TEACHER
                    participant.save()
                except User.DoesNotExist:
                    logging.warning('Watch out!') 
             
            courses=Course.objects.all()
            for c in courses:
                try:
                    course = Course.objects.get(shortname=c.shortname)
                    CourseCohort(cohort=cohort, course=course).save()
                except Course.DoesNotExist:
                     raise Http404
                           
            #return HttpResponseRedirect('../') # Redirect after POST
        else:
            #If form is not valid, clean the groups data
            messages.error(request, "The form is invalid")
            logging.warning('Watch out!') 
    else:
        form = CohortForm() # An unbound form

    return render(request, 'oppia/cohort-form.html',{'form': form,})  


def cohort_view(request,cohort_id):
    cohort, response = can_view_cohort(request,cohort_id)
    
    if response is not None:
        return response
    
    start_date = timezone.now() - datetime.timedelta(days=31)
    end_date = timezone.now()
        
    # get student activity
    student_activity = []
    no_days = (end_date-start_date).days + 1
    students =  User.objects.filter(participant__role=Participant.STUDENT, participant__cohort=cohort)    
    trackers = Tracker.objects.filter(course__coursecohort__cohort=cohort, 
                                       user__is_staff=False,
                                       user__in=students,  
                                       tracker_date__gte=start_date,
                                       tracker_date__lte=end_date).extra({'activity_date':"date(tracker_date)"}).values('activity_date').annotate(count=Count('id'))
    for i in range(0,no_days,+1):
        temp = start_date + datetime.timedelta(days=i)
        count = next((dct['count'] for dct in trackers if dct['activity_date'] == temp.date()), 0)
        student_activity.append([temp.strftime("%d %b %Y"),count])
        
    # get leaderboard
    leaderboard = cohort.get_leaderboard(10)
    
    
    return render_to_response('oppia/course/cohort-activity.html',
                              {'cohort':cohort,
                               'activity_graph_data': student_activity, 
                               'leaderboard': leaderboard, }, 
                              context_instance=RequestContext(request))
    
def cohort_leaderboard_view(request,cohort_id):
    
    cohort, response = can_view_cohort(request,cohort_id)
    
    if cohort is None:
        return response
        
    # get leaderboard
    lb = cohort.get_leaderboard(0)
    
    paginator = Paginator(lb, 25) # Show 25 contacts per page

    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        leaderboard = paginator.page(page)
    except (EmptyPage, InvalidPage):
        leaderboard = paginator.page(paginator.num_pages)

    
    return render_to_response('oppia/course/cohort-leaderboard.html',
                              {'cohort':cohort,
                               'page':leaderboard, }, 
                              context_instance=RequestContext(request))

def cohort_edit(request,cohort_id):
    if not can_edit_cohort(request, cohort_id):
        return HttpResponse('Unauthorized', status=401)  
    cohort = Cohort.objects.get(pk=cohort_id)
    if request.method == 'POST':
        form = CohortForm(request.POST)
        if form.is_valid(): 
            cohort.school = form.cleaned_data.get("description")
            cohort.start_date = form.cleaned_data.get("start_date")
            cohort.end_date = form.cleaned_data.get("end_date")
            cohort.save()
            
            Participant.objects.filter(cohort=cohort).delete()
            
            students=User.objects.filter(userprofile__school_code=form.cleaned_data.get("description"), userprofile__status="Student")
            #if len(students) > 0:
            for s in students:
                try:
                    participant = Participant()
                    participant.cohort = cohort
                    participant.user = User.objects.get(username=s.username)
                    participant.role = Participant.STUDENT
                    participant.save()
                except User.DoesNotExist:
                    pass
            teachers=User.objects.filter(userprofile__school_code=form.cleaned_data.get("description"),userprofile__status="Tutor")
            #if len(teachers) > 0:
            for t in teachers:
                try:
                    participant = Participant()
                    participant.cohort = cohort
                    participant.user = User.objects.get(username=t.username)
                    participant.role = Participant.TEACHER
                    participant.save()
                except User.DoesNotExist:
                    pass
             
            CourseCohort.objects.filter(cohort=cohort).delete()       
            courses=Course.objects.all()
            #if len(courses) > 0:
            for c in courses:
                try:
                    course = Course.objects.get(shortname=c.shortname)
                    CourseCohort(cohort=cohort, course=course).save()
                except Course.DoesNotExist:
                    pass
                    
            return HttpResponseRedirect('../../')
           
    else:
        '''participant_teachers = Participant.objects.filter(cohort=cohort,role=Participant.TEACHER)
        teacher_list = []
        for pt in participant_teachers:
            teacher_list.append(pt.user.username)
        teachers = ", ".join(teacher_list)
        
        participant_students = Participant.objects.filter(cohort=cohort,role=Participant.STUDENT)
        student_list = []
        for ps in participant_students:
            student_list.append(ps.user.username)
        students = ", ".join(student_list)
        
        cohort_courses = Course.objects.filter(coursecohort__cohort=cohort)
        course_list = []
        for c in cohort_courses:
            course_list.append(c.shortname)
        courses = ", ".join(course_list)'''
        
        form = CohortForm(initial={'description': cohort.school,
                                   'start_date': cohort.start_date,
                                   'end_date': cohort.end_date,
                                  }) 

    return render(request, 'oppia/cohort-form.html',{'form': form,}) 

def cohort_course_view(request, cohort_id, course_id): 
    cohort, response = can_view_cohort(request,cohort_id)
    if response is not None:
        return response
    
    try:
        course = Course.objects.get(pk=course_id, coursecohort__cohort=cohort)
    except Course.DoesNotExist:
        raise Http404()
    
    start_date = timezone.now() - datetime.timedelta(days=31)
    end_date = timezone.now()
    student_activity = []
    no_days = (end_date-start_date).days + 1
    users =  User.objects.filter(participant__role=Participant.STUDENT, participant__cohort=cohort).order_by('first_name', 'last_name')   
    trackers = Tracker.objects.filter(course=course, 
                                       user__is_staff=False,
                                       user__in=users,  
                                       tracker_date__gte=start_date,
                                       tracker_date__lte=end_date).extra({'activity_date':"date(tracker_date)"}).values('activity_date').annotate(count=Count('id'))
    for i in range(0,no_days,+1):
        temp = start_date + datetime.timedelta(days=i)
        count = next((dct['count'] for dct in trackers if dct['activity_date'] == temp.date()), 0)
        student_activity.append([temp.strftime("%d %b %Y"),count])
     
    students = []
    for user in users:
        data = {'user': user,
                'no_quizzes_completed': course.get_no_quizzes_completed(course,user),
                'pretest_score': course.get_pre_test_score(course,user),
                'no_activities_completed': course.get_activities_completed(course,user),
                'no_quizzes_completed': course.get_no_quizzes_completed(course,user),
                'no_points': course.get_points(course,user),
                'no_badges': course.get_badges(course,user),}
        students.append(data)
       
    return render_to_response('oppia/course/cohort-course-activity.html',
                              {'course': course,
                               'cohort': cohort, 
                               'activity_graph_data': student_activity,
                               'students': students }, 
                              context_instance=RequestContext(request))
       
def leaderboard_view(request):
    lb = Points.get_leaderboard()
    paginator = Paginator(lb, 25) # Show 25 per page

    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        leaderboard = paginator.page(page)
    except (EmptyPage, InvalidPage):
        leaderboard = paginator.page(paginator.num_pages)

    return render_to_response('oppia/leaderboard.html',
                              {'page':leaderboard}, 
                              context_instance=RequestContext(request))

def course_quiz(request,course_id):
    course = check_owner(request,course_id)
    digests = Activity.objects.filter(section__course=course,type='quiz').order_by('section__order').distinct()
    quizzes = []
    for d in digests:
        try:
            q = Quiz.objects.get(quizprops__name='digest',quizprops__value=d.digest)
            q.section_name = d.section.title
            quizzes.append(q)
        except Quiz.DoesNotExist:
            pass
    return render_to_response('oppia/course/quizzes.html',
                              {'course': course, 
                               'quizzes':quizzes}, 
                              context_instance=RequestContext(request))

def course_quiz_attempts(request,course_id,quiz_id):
    # get the quiz digests for this course
    course = check_owner(request,course_id)
    quiz = Quiz.objects.get(pk=quiz_id)
    attempts = QuizAttempt.objects.filter(quiz=quiz).order_by('-attempt_date')
    
    paginator = Paginator(attempts, 25)
    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        attempts = paginator.page(page)
        for a in attempts:
            a.responses = QuizAttemptResponse.objects.filter(quizattempt=a)                
    except (EmptyPage, InvalidPage):
        tracks = paginator.page(paginator.num_pages)
    print  len(attempts)

    return render_to_response('oppia/course/quiz-attempts.html',
                              {'course': course,
                               'quiz':quiz, 
                               'page':attempts}, 
                              context_instance=RequestContext(request))

def course_feedback(request,course_id):
    course = check_owner(request,course_id)
    digests = Activity.objects.filter(section__course=course,type='feedback').order_by('section__order').values('digest').distinct()
    feedback = []
    for d in digests:
        try:
            q = Quiz.objects.get(quizprops__name='digest',quizprops__value=d['digest'])
            feedback.append(q)
        except Quiz.DoesNotExist:
            pass
        
    return render_to_response('oppia/course/feedback.html',
                              {'course': course,
                               'feedback':feedback}, 
                              context_instance=RequestContext(request))

def course_feedback_responses(request,course_id,quiz_id):
    #get the quiz digests for this course
    course = check_owner(request,course_id)
    quiz = Quiz.objects.get(pk=quiz_id)
    attempts = QuizAttempt.objects.filter(quiz=quiz).order_by('-attempt_date')
    
    paginator = Paginator(attempts, 25)
    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        attempts = paginator.page(page)
        for a in attempts:
            a.responses = QuizAttemptResponse.objects.filter(quizattempt=a)                
    except (EmptyPage, InvalidPage):
        tracks = paginator.page(paginator.num_pages)

    return render_to_response('oppia/course/feedback-responses.html',
                              {'course': course,
                               'quiz':quiz, 
                               'page':attempts}, 
                              context_instance=RequestContext(request))
