'''/***************************************************************************************
*  REFERENCES
*  Title: Google Calendar API
*  Author: <author(s) names>
*  Date: <date>
*  Code version: <code version>
*  URL: https://developers.google.com/calendar/api/v3/reference/calendarList/list#python
*  Software License: <license software is released under>
*
*  Title: ....
*
***************************************************************************************/'''

from django.http import HttpResponse
from django.http.response import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import render, redirect
from django.views import generic
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
#from __future__ import print_function
import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from .models import Temp
from .models import Calendar
from .forms import CalendarForm, UploadForm, CourseForm
from django.template import RequestContext, context
from django.core.files.storage import FileSystemStorage
from django.views.generic.edit import CreateView
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy
from .models import Upload, Course, User, Profile
import httplib2
import io

#import cv2
#import numpy as np

#for testing and researh
import json

def IndexView(request):
    return render(request, 'core/index.html')

def get_credentials(request):
    app = SocialApp.objects.get(provider='google')
    user_token = SocialToken.objects.get(account__user=request.user, account__provider='google')
   
    if user_token.token_secret:
        Profile.objects.update_or_create(user=request.user, defaults={'refresh_token': user_token.token_secret})
    else:
        user_token.token_secret = Profile.objects.get(user=request.user).refresh_token

    creds = Credentials(
        token=user_token.token,
        refresh_token=user_token.token_secret,
        token_uri='https://www.googleapis.com/oauth2/v3/token',
        client_id=app.client_id,
        client_secret=app.secret
    )

    ## Try to refresh access, if not return none so the user gets logged out
    if not creds or not creds.valid:
        return None

    return creds

def calendar_body():
    return {
        "summary": "StudyDo",
    }

def time_fix(time):
    return time[:11] + "05:00:00-" + time[11:]

def event_body(calendarEntry):
    return {
        'summary': calendarEntry['eventName'],
        'description': calendarEntry['eventDesc'],
        'location': calendarEntry['eventLocation'],
        'start': {
            'dateTime': time_fix(calendarEntry['eventStart']),
            'timeZone': 'America/New_York'
        },
        'end': {
            'dateTime': time_fix(calendarEntry['eventEnd']),
            'timeZone': 'America/New_York'
        },

    }


def CalendarView(request):
    if not request.user.is_authenticated:
        return render(request, 'core/calendar.html')
    if not request.user.socialaccount_set.exists():
        return render(request, 'core/calendar.html')

    ## get api credentials
    creds = get_credentials(request)
    ## if they don't exist, log them out so they can log back in.
    if creds == None:
        return redirect('logout')

    try:
        service = build('calendar', 'v3', credentials=creds)
    except:
        return redirect('logout')
        
    # get list of user's calendars
    found = False
    calendar_list = service.calendarList().list().execute()
    for calendar_list_entry in calendar_list['items']:
        if calendar_list_entry['summary'] == 'StudyDo':
            user_cal_objs = Calendar.objects.filter(user=request.user)
            if len(user_cal_objs) != 0:
                for x in user_cal_objs:
                    if calendar_list_entry['id'] == x.calendarId:
                        found = True
                        break
                else:
                    continue  # only executed if the inner loop did NOT break
                break

    # create an StudyDo calendar if it doesn't already exist
    if len(Calendar.objects.filter(user=request.user)) == 0 or found == False:
        calendar = service.calendars().insert(body=calendar_body()).execute()
        if len(Calendar.objects.filter(user=request.user)) == 0:
            Calendar.objects.create(user=request.user,calendarId=calendar['id'])
        else:
            Calendar.objects.filter(user=request.user).update(calendarId=calendar['id'])

    calendarId = Calendar.objects.filter(user=request.user)[0].calendarId

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    events_result = service.events().list(calendarId=calendarId,
                                        singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    upcoming = []

    if not events:
        print('No upcoming events found.')
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date'))
        end = e['end'].get('dateTime', e['end'].get('date'))
 
        event = {}
        event['name'] = e['summary']

        event['link'] = e.get('htmlLink')
        event['start'] = start
        event['end'] = end
        event['desc'] = e.get('description')
        

        upcoming.append(event)
    
    
    if request.method == 'POST':
        calendarEntry = CalendarForm(request.POST)
        if len(calendarEntry.errors) > 0:
            return render(request, 'core/calendar.html', {'form': calendarEntry, 'upcoming': upcoming})
        if calendarEntry.is_valid():
            #Code to actually write to the API here
            event = service.events().insert(calendarId=calendarId, body=event_body(request.POST)).execute()
            return HttpResponseRedirect(reverse('core:Calendar'))

    else:
        calendarEntry = CalendarForm()

    return render(request, 'core/calendar.html', {'form': calendarEntry, 'upcoming': upcoming})


#source: https://www.youtube.com/watch?v=KQJRwWpP8hs&t=724s
def upload_notes(request, c_title=None):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            # can only upload to classes you are in or if you are admin
            course = Course.objects.get(pk=int(form.data.get('course')))
            students = course.profile_set.all()
            if not request.user.is_superuser:
                if request.user.profile not in students:
                    messages.error(request, 'You cannot upload notes to a class you have not joined.')
                    return render(request, 'core/upload_notes.html',{'form':form})
            if len(Upload.objects.filter(title=form.data.get('title'), course=form.data.get('course'))) > 0:
                messages.error(request, 'File with same name exists! Use a different name.')
                return render(request, 'core/upload_notes.html',{'form':form})
            else:
                obj = form.save(commit=False)
                obj.user = request.user
                obj.save()
                course = Course.objects.get(pk=int(form.data.get('course')))
                return redirect(reverse('core:Courses', args=[course.slug()]))
    if(c_title is not None):
        dept = c_title[:c_title.index(' ')].upper()
        num = int(c_title[c_title.index(' ')+1:])
        c = Course.objects.get(dept=dept, num=num)
        form = UploadForm(initial={'course': c})
    else:
        form = UploadForm()
    return render(request, 'core/upload_notes.html',{
        'form':form
        } )

#source: https://ozenero.com/django-how-to-upload-file-using-modelform-tutorial-mysql
def delete_upload(request, slug, pk):
    if request.method == "POST":
        upload_delete = Upload.objects.get(pk=pk)
        if upload_delete.user == request.user.username:
            upload_delete.delete()
        else:
            messages.error(request, 'You can only delete files you uploaded.')
    return redirect(reverse('core:Courses', args=[slug]))

def Courses(request, slug=None):
    if(slug is not None):
        context = dict()
        dept = slug[:slug.index('-')].upper()
        num = int(slug[slug.index('-')+1:])
        c = Course.objects.get(dept=dept, num=num)
        context['course'] = c

        # student can only view course if they join it
        students = c.profile_set.all()
        # admin can view without joining
        if request.user.is_superuser:
            context['isAdmin'] = 'true'
            context['enrolled'] = "true"
            uploads = display_uploads(request, c)
            context['uploads'] = uploads
        else:
            context['isAdmin'] = 'false'
            if request.user.profile not in students:
                context['enrolled'] = "false"
            else:
                context['enrolled'] = "true"
                uploads = display_uploads(request, c)
                context['uploads'] = uploads

        if len(students) != 0:
            students = students.order_by('user__first_name', 'user__last_name', 'user__email')
        context['students'] = students
        template = 'core/course.html'
    else:
        sortby = None
        if request.method == "POST":
            sortby = request.POST.get('sortby')
        if(sortby is not None):
            if(sortby == "desc"):
                all_courses = Course.objects.all().order_by('-dept', '-num')
            elif(sortby == "asc"):
                all_courses = Course.objects.all().order_by('dept', 'num')
        else: 
            all_courses = Course.objects.all().order_by('dept', 'num')

        template = 'core/allcourses.html'
        context = {
            'all_courses_list': all_courses,
        }
    return render(request, template, context)

def display_uploads(request, course):
    sortbyNotes = None
    if request.method == "POST":
        sortbyNotes = request.POST.get('sortbyNotes')
    if(sortbyNotes is not None):
        if(sortbyNotes == "desc"):
            uploads = Upload.objects.filter(course=course).order_by('-course', '-title')
        elif(sortbyNotes == "asc"):
            uploads = Upload.objects.filter(course=course).order_by('course', 'title')
    else: 
        uploads = Upload.objects.filter(course=course).order_by('course', 'title')
    return uploads

def course_enroll(request, slug):
    if request.method == "POST":
        temp = request.POST.get("courseaction")
        values = temp.split()
        if values[0] == "join":
        # if is add
            print("dade")
            request.user.profile.courses.add(Course.objects.get(dept=values[1], num=values[2]))
        else:
        # if is remove
            print(values)
            print("no dade")
            request.user.profile.courses.remove(Course.objects.get(dept=values[1], num=values[2]))
    return redirect(reverse('core:Courses', args=[slug]))


def create_course(request):
    if request.method == 'POST':
        dtForm = CourseForm(request.POST)
        if dtForm.is_valid():
            dtForm.save()
            return HttpResponseRedirect(reverse('core:Courses'))
    else:
        dtForm = CourseForm()
    return render(request, 'core/courseform.html', {
        'form': dtForm,
    })

def cancelled_login(request):
    return redirect(reverse('core:Index'))
