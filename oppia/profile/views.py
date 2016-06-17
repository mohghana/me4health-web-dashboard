# oppia/profile/views.py
import csv
import datetime
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (authenticate, login, views)
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Count, Max, Min, Sum, Avg
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.utils import timezone
from django.utils.translation import ugettext as _

from itertools import chain

from oppia.forms import DateRangeForm, DateRangeIntervalForm
from oppia.models import Points, Award, AwardCourse, Course, UserProfile, Tracker, Activity,SchoolCode,Program
from oppia.permissions import get_user, get_user_courses, can_view_course, can_edit_user
from oppia.profile.forms import LoginForm, RegisterForm, ResetForm, ProfileForm, UploadProfileForm,SchoolCodeForm,ProgramForm,UploadSchoolCodeForm
from oppia.quiz.models import Quiz, QuizAttempt

from tastypie.models import ApiKey


def login_view(request):
    username = password = ''
    
    # if already logged in
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('oppia_home'))
    
    if request.POST:
        form = LoginForm(request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        next = request.POST.get('next')
        next = None 
        print next
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(request,user)
            if next is not None:
                return HttpResponseRedirect(next)
            else:
                return HttpResponseRedirect(reverse('oppia_home'))
    else:
        form = LoginForm(initial={'next':request.GET.get('next'),})
        
    return render_to_response('oppia/form.html',
                              {'username': username, 
                               'form': form, 
                               'title': _(u'Login')},
                              context_instance=RequestContext(request),)

def register(request):
    if not settings.OPPIA_ALLOW_SELF_REGISTRATION:
        raise Http404
    
    if request.method == 'POST': # if form submitted...
        form = RegisterForm(request.POST)
        if form.is_valid(): # All validation rules pass
            # Create new user
            username = form.cleaned_data.get("phone_number")
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            first_name = form.cleaned_data.get("first_name")
            last_name = form.cleaned_data.get("last_name")
            gender = form.cleaned_data.get("gender")
            phone_number = form.cleaned_data.get("phone_number")
            phone_number_two = form.cleaned_data.get("phone_number_two")
            phone_number_three = form.cleaned_data.get("phone_number_three")
            year_group = form.cleaned_data.get("year_group")
            program = form.cleaned_data.get("program")
            status = form.cleaned_data.get("status")
            home_town = form.cleaned_data.get("home_town")
            school_code = form.cleaned_data.get("school_code")

            user = User.objects.create_user(username, email, password)
            user.first_name = first_name
            user.last_name = last_name
            user.year_group = year_group
            user.program = program
            user.status = status
            user.home_town = home_town
            user.school_code = school_code
            if status=='Tutor':
                user.is_staff=1

            user.save()

            user_profile = UserProfile()
            user_profile.user = user
            user_profile.job_title = form.cleaned_data.get("job_title")
            user_profile.organisation = form.cleaned_data.get("organisation")
            user_profile.phone_number = form.cleaned_data.get("phone_number")
            user_profile.phone_number_two = form.cleaned_data.get("phone_number_two")
            user_profile.phone_number_three = form.cleaned_data.get("phone_number_three")
            user_profile.year_group = form.cleaned_data.get("year_group")
            user_profile.program = form.cleaned_data.get("program")
            user_profile.status = form.cleaned_data.get("status")
            user_profile.home_town = form.cleaned_data.get("home_town")
            user_profile.school_code = form.cleaned_data.get("school_code")
            user_profile.gender = form.cleaned_data.get("gender")
            user_profile.save()
            u = authenticate(username=username, password=password)
            if u is not None:
                if u.is_active:
                    login(request, u)
                    return HttpResponseRedirect('thanks/')
            return HttpResponseRedirect('thanks/') # Redirect after POST
    else:
        form = RegisterForm(initial={'next':request.GET.get('next'),})

    return render_to_response('oppia/form.html', 
                              {'form': form, 
                               'title': _(u'Register'), },
                               context_instance=RequestContext(request),)

def reset(request):
    if request.method == 'POST': # if form submitted...
        form = ResetForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            try:
                user = User.objects.get(username__exact=username)
            except User.DoesNotExist:
                user = User.objects.get(email__exact=username)
            newpass = User.objects.make_random_password(length=8)
            user.set_password(newpass)
            user.save()
            if request.is_secure():
                prefix = 'https://'
            else:
                prefix = 'http://'
            # TODO - better way to manage email message content
            send_mail('OppiaMobile: Password reset', 'Here is your new password for OppiaMobile: '+newpass 
                      + '\n\nWhen you next log in you can update your password to something more memorable.' 
                      + '\n\n' + prefix + request.META['SERVER_NAME'] , 
                      settings.SERVER_EMAIL, [user.email], fail_silently=False)
            return HttpResponseRedirect('sent')
    else:
        form = ResetForm() # An unbound form

    return render_to_response( 
                  'oppia/form.html', 
                  {'form': form,
                   'title': _(u'Reset password')},
                  context_instance=RequestContext(request))

def school_code(request):
    if request.method == 'POST': # if form submitted...
        form = SchoolCodeForm(request.POST)
        if form.is_valid(): # All validation rules pass
            # Create new user
            school_code = form.cleaned_data.get("school_code")
            school_name = form.cleaned_data.get("school_name")
            school = SchoolCode()
            school.school_code = form.cleaned_data.get("school_code")
            school.school_name = form.cleaned_data.get("school_name")
            school.region = form.cleaned_data.get("region")
            school.school_type = form.cleaned_data.get("school_type")
            school.created_by = request.user
            school.save()
            messages.success(request, _(u"SchoolCode updated"))
    else:
        form = SchoolCodeForm()
    codes_list = SchoolCode.objects.raw('SELECT * FROM oppia_schoolcode s,auth_user u where u.id=s.created_by_id')
    return render_to_response('oppia/schoolcodeview.html', 
                              {'form': form, 
                               'title': _(u'School Code'), 
                               'codes_list':codes_list,},
                               context_instance=RequestContext(request),)

def program(request):
    if request.method == 'POST': # if form submitted...
        form = ProgramForm(request.POST)
        if form.is_valid(): # All validation rules pass
            # Create new user
           
            program = Program()
            program.program_name = form.cleaned_data.get("program_name")
            program.created_by = request.user
            program.save()
            messages.success(request, _(u"Program added"))
    else:
        form = ProgramForm()

    return render_to_response('oppia/form.html', 
                              {'form': form, 
                               'title': _(u'School Program'), },
                               context_instance=RequestContext(request),)

def edit(request, user_id=0):
    if user_id != 0:
        if can_edit_user(request, user_id):
            view_user = User.objects.get(pk=user_id)
        else:
            return HttpResponse('Unauthorized', status=401)
    else:
        view_user = request.user
    
    key = ApiKey.objects.get(user = view_user)
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            # update basic data
            email = form.cleaned_data.get("email")
            first_name = form.cleaned_data.get("first_name")
            last_name = form.cleaned_data.get("last_name")
            view_user.email = email
            view_user.first_name = first_name
            view_user.last_name = last_name
            if form.cleaned_data.get("status")=='Tutor':
                view_user.is_staff=1

            view_user.save()
            
            try:
                user_profile = UserProfile.objects.get(user=view_user)
                #user_profile.job_title = form.cleaned_data.get("job_title")
                #user_profile.organisation = form.cleaned_data.get("organisation")
                user_profile.phone_number = form.cleaned_data.get("phone_number")
                user_profile.phone_number_two = form.cleaned_data.get("phone_number_two")
                user_profile.phone_number_three = form.cleaned_data.get("phone_number_three")
                user_profile.year_group = form.cleaned_data.get("year_group")
                user_profile.program = form.cleaned_data.get("program")
                user_profile.gender = form.cleaned_data.get("gender")
                user_profile.status = form.cleaned_data.get("status")
                user_profile.home_town = form.cleaned_data.get("home_town")
                user_profile.school_code = form.cleaned_data.get("school_code")
                user_profile.save()
            except UserProfile.DoesNotExist:
                user_profile = UserProfile()
                user_profile.user = view_user
                #user_profile.job_title = form.cleaned_data.get("job_title")
                #user_profile.organisation = form.cleaned_data.get("organisation")
                user_profile.phone_number = form.cleaned_data.get("phone_number")
                user_profile.phone_number_two = form.cleaned_data.get("phone_number_two")
                user_profile.phone_number_three = form.cleaned_data.get("phone_number_three")
                user_profile.year_group = form.cleaned_data.get("year_group")
                user_profile.program = form.cleaned_data.get("program")
                user_profile.gender = form.cleaned_data.get("gender")
                user_profile.status = form.cleaned_data.get("status")
                user_profile.home_town = form.cleaned_data.get("home_town")
                user_profile.school_code = form.cleaned_data.get("school_code")
                user_profile.save()
            messages.success(request, _(u"Profile updated"))
            
            # if password should be changed
            password = form.cleaned_data.get("password")
            if password:
                view_user.set_password(password)
                view_user.save()
                messages.success(request, _(u"Password updated"))
    else:
        try:
            user_profile = UserProfile.objects.get(user=view_user)
        except UserProfile.DoesNotExist:
            user_profile = UserProfile()
        form = ProfileForm(initial={'username':view_user.username,
                                    'email':view_user.email,
                                    'first_name':view_user.first_name,
                                    'last_name':view_user.last_name,
                                    'api_key': key.key,
                                    'job_title': user_profile.job_title,
                                    'organisation': user_profile.organisation,
                                    'phone_number': user_profile.phone_number,
                                    'gender': user_profile.gender,
                                    'phone_number_two': user_profile.phone_number_two,
                                    'phone_number_three': user_profile.phone_number_three,
                                    'year_group': user_profile.year_group,
                                    'program': user_profile.program,
                                    'status': user_profile.status,
                                    'home_town': user_profile.home_town,
                                    'school_code': user_profile.school_code,})
        
    return render_to_response( 
                  'oppia/profile/profile.html', 
                  {'form': form,},
                  context_instance=RequestContext(request))

def points(request):
    points = Points.objects.filter(user=request.user).order_by('-date')
    paginator = Paginator(points, 25) # Show 25 contacts per page

    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        mypoints = paginator.page(page)
    except (EmptyPage, InvalidPage):
        mypoints = paginator.page(paginator.num_pages)
    return render_to_response('oppia/profile/points.html', 
                              {'page': mypoints,}, 
                              context_instance=RequestContext(request),)

def badges(request):
    awards = Award.objects.filter(user=request.user).order_by('-award_date')
    return render_to_response('oppia/profile/badges.html', 
                              {'awards': awards,},
                              context_instance=RequestContext(request),)


def user_activity(request, user_id):
    
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
    
    activity = []
    start_date = timezone.now() - datetime.timedelta(days=31)
    end_date = timezone.now()
    no_days = (end_date-start_date).days + 1
    
    course_ids = list(chain(cohort_courses.values_list('id',flat=True),other_courses.values_list('id',flat=True)))
    trackers = Tracker.objects.filter(course__id__in=course_ids, 
                                      user=view_user, 
                                      tracker_date__gte=start_date,
                                      tracker_date__lte=end_date) \
                                      .extra({'activity_date':"date(tracker_date)"}) \
                                      .values('activity_date') \
                                      .annotate(count=Count('id'))
    for i in range(0,no_days,+1):
        temp = start_date + datetime.timedelta(days=i)
        count = next((dct['count'] for dct in trackers if dct['activity_date'] == temp.date()), 0)
        activity.append([temp.strftime("%d %b %Y"),count])
        
    return render_to_response('oppia/profile/user-scorecard.html',
                              {'view_user': view_user,
                              'profile':profile,
                              'version':version,
                              'device':device,
                              'courses': courses, 
                               'activity_graph_data': activity }, 
                              context_instance=RequestContext(request))

def user_course_activity_view(request, user_id, course_id):
    
    view_user, response = get_user(request, user_id)
    if response is not None:
        return response
    
    course = can_view_course(request, course_id)

    act_quizzes = Activity.objects.filter(section__course=course,type=Activity.QUIZ).order_by('section__order','order')
    quizzes = []
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
                'no_attempts': attempts.count(),
                'max_score': max_score,
                'min_score': min_score,
                'first_score': first_score,
                'latest_score': latest_score,
                'avg_score': avg_score,
                 }
        quizzes.append(quiz);
    
    activity = []
    start_date = timezone.now() - datetime.timedelta(days=31)
    end_date = timezone.now()
    no_days = (end_date-start_date).days + 1
    
    trackers = Tracker.objects.filter(course=course, 
                                      user=view_user, 
                                      tracker_date__gte=start_date,
                                      tracker_date__lte=end_date) \
                                      .extra({'activity_date':"date(tracker_date)"}) \
                                      .values('activity_date') \
                                      .annotate(count=Count('id'))
    for i in range(0,no_days,+1):
        temp = start_date + datetime.timedelta(days=i)
        count = next((dct['count'] for dct in trackers if dct['activity_date'] == temp.date()), 0)
        activity.append([temp.strftime("%d %b %Y"),count])
    
    return render_to_response('oppia/profile/user-course-scorecard.html',
                              {'view_user': view_user,
                               'course': course, 
                               'quizzes': quizzes, 
                               'activity_graph_data': activity }, 
                              context_instance=RequestContext(request))

def upload_view(request):
    if not request.user.is_staff:
        raise Http404
    
    if request.method == 'POST': # if form submitted...
        form = UploadProfileForm(request.POST,request.FILES)
        if form.is_valid():
            request.FILES['upload_file'].open("rb")
            csv_file = csv.DictReader(request.FILES['upload_file'].file)
            required_fields = ['username','firstname','lastname','email','status','phone_number','school_code','year_group','program']
            results = []
            try:
                for row in csv_file:
                    # check all required fields defined
                    all_defined = True
                    for rf in required_fields:
                        if rf not in row or row[rf].strip() == '':
                            result = {}
                            result['username'] = row['phone_number']
                            result['created'] = False
                            result['message'] = _(u'No %s set' % rf)
                            results.append(result)
                            all_defined = False
                        
                    if not all_defined:    
                        continue
                    
                    user = User()
                    user.username = row['phone_number']
                    user.first_name = row['firstname']
                    user.last_name = row['lastname']
                    if row['status']=='Tutor':
                        user.is_staff=1
                    user.email = row['email']
                    auto_password = False
                    if 'password' in row:
                        user.set_password(row['password'])
                    else:
                        password = User.objects.make_random_password()
                        user.set_password(password)
                        auto_password = True
                    try:
                        user.save()
                        up = UserProfile()
                        up.user = user
                        for col_name in row:
                            setattr(up, col_name, row[col_name])

                        up.save()
                        result = {}
                        result['username'] = row['phone_number']
                        result['created'] = True
                        if auto_password:
                            result['message'] = _(u'User created with password: %s' % password)
                        else:
                            result['message'] = _(u'User created')
                        results.append(result)
                    except IntegrityError as ie:
                        result = {}
                        result['username'] = row['phone_number']
                        result['created'] = False
                        result['message'] = _(u'User already exists')
                        results.append(result)
                        continue
            except:
                result = {}
                result['username'] = None
                result['created'] = False
                result['message'] = _(u'Could not parse file')
                results.append(result)
            
    else:
        results = []
        form = UploadProfileForm()
        
    return render_to_response('oppia/profile/upload.html', 
                              {'form': form, 
                               'results': results},
                              context_instance=RequestContext(request),)

def upload_schools_view(request):
    
    if request.method == 'POST': # if form submitted...
        form = UploadSchoolCodeForm(request.POST,request.FILES)
        if form.is_valid():
            request.FILES['upload_file'].open("rb")
            csv_file = csv.DictReader(request.FILES['upload_file'].file)
            required_fields = ['school_name','school_code','region','school_type']
            results = []
            for row in csv_file:
                    # check all required fields defined
                all_defined = True
                for rf in required_fields:
                    if rf not in row or row[rf].strip() == '':
                        result = {}
                        result['school_name'] = row['school_name']
                        result['created'] = False
                        result['message'] = _(u'No %s set' % rf)
                        results.append(result)
                        all_defined = False
                        
                    if not all_defined:    
                        continue
                    
                   
                    try:
                        school = SchoolCode.objects.get(school_code=row['school_code'])
                        school.school_name=row['school_name']
                        school.school_code=row['school_code']
                        school.region=row['region']
                        school.school_type=row['school_type']
                        school.created_by = request.user
                        school.save()
                        result = {}
                        result['school_name'] = row['school_name']
                        result['created'] = False
                        result['message'] = _(u'School created')
                        results.append(result)
                    except SchoolCode.DoesNotExist:
                        school = SchoolCode()
                        school.school_name=row['school_name']
                        school.school_code=row['school_code']
                        school.region=row['region']
                        school.school_type=row['school_type']
                        school.created_by = request.user
                        school.save()
                        result = {}
                        result['school_name'] = row['school_name']
                        result['created'] = False
                        result['message'] = _(u'School created')
                        results.append(result)
                        #continue
            
            
    else:
        results = []
        form = UploadSchoolCodeForm()
        
    return render_to_response('oppia/profile/upload-school.html', 
                              {'form': form, 
                               'results': results},
                              context_instance=RequestContext(request),)
