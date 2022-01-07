'''/***************************************************************************************
*  REFERENCES
*  Title: Create Custom Error Messages with Model Forms
*  Author: Moe Far
*  Date: <date>
*  Code version: <code version>
*  URL: https://stackoverflow.com/questions/3436712/create-custom-error-messages-with-model-forms
*  Software License: <license software is released under>
*
*  Title: Customize/remove Django select box blank option
*  URL: https://stackoverflow.com/questions/739260/customize-remove-django-select-box-blank-option
*
***************************************************************************************/'''

from django import forms

from core.models import Upload
from core.models import Course

class CalendarForm (forms.Form):
    eventName = forms.CharField(label='Name of Event', max_length = 200,required=True)
    eventDesc = forms.CharField(label='Event Details',max_length = 500,required=False)
    eventLocation = forms.CharField(label='Event Location', max_length = 500,required=False)
    eventStart = forms.DateTimeField(label='Start Time',required=True)
    eventEnd = forms.DateTimeField(label='End Time', required=True)
  
    def clean_eventEnd(self):
        eventStart = self.cleaned_data['eventStart']
        eventEnd = self.cleaned_data['eventEnd']
        if eventStart > eventEnd:
            self.add_error('eventEnd', "End date cannot be before start date.")
        return eventEnd


class UploadForm(forms.ModelForm):
  class Meta:
    model = Upload
    course=forms.ModelChoiceField(queryset=Course.objects.all())
    fields = ['course', 'title', 'upload_file']

  def __init__(self, *args, **kwargs):
    super(UploadForm, self).__init__(*args, **kwargs)
    self.fields['course'].queryset = self.fields['course'].queryset.order_by('dept', 'num')
    self.fields['course'].empty_label = "--Select Course--"
    # following line needed to refresh widget copy of choice list
    self.fields['course'].widget.choices = self.fields['course'].choices

    self.fields['course'].label = "Course"
    self.fields['title'].label = "File Name"
    self.fields['upload_file'].label = "Upload File"

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['dept', 'num']

    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)
        self.fields['dept'].label = "Department Abbreviation"
        self.fields['num'].label = "Course Number"

    def clean_dept(self):
        return self.cleaned_data['dept'].upper()
