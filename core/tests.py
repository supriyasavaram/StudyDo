'''***************************************************************************************
*  REFERENCES
*  Title: django-allauth tests
*  Author: pennersr
*  URL: https://github.com/pennersr/django-allauth/blob/master/allauth/socialaccount/providers/google/tests.py
*
*  Title: Testing Demonstration Lecture 10/7
*
*  Title: google-calendar-api-test
*  Author: mizzsugar
*  URL: https://github.com/mizzsugar/google-calendar-api-test/blob/master/test.py
*
*  Title: How to unit test a Django model with a FileField
*  Author: semicolom (blog)
*  URL: #http://www.semicolom.com/blog/test-a-django-model-with-a-filefield/
*
***************************************************************************************/'''

#from _typeshed import SupportsAnext
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.files import File

from django.test.utils import override_settings
import unittest.mock
import mock

from allauth.account import app_settings as account_settings
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.tests import MockedResponse, TestCase

from googleapiclient.discovery import build

from .provider import GoogleProvider

from .models import Course
from django.urls import reverse
from .forms import UploadForm
from .models import Upload
from .views import upload_notes



class LoginTest(TestCase):
    # Set up for login tests
    def setUp(self):
        User = get_user_model()
        user = User.objects.create(username='testuser')
        user.set_password('!Password1')
        user.save()        
    
    def test_correctInput(self):
        c = Client()
        logged_correctly = c.login(username='testuser', password='!Password1')
        self.assertTrue(logged_correctly)

    def test_loggedOut(self):
        c = Client()
        c.login(username='testuser', password='!Password1')
        User = get_user_model()
        user = User.objects.get(username='testuser')
        self.assertTrue(user.is_authenticated)
        c.logout
        self.assertFalse(user.is_anonymous)


@override_settings(
    SOCIALACCOUNT_AUTO_SIGNUP=True,
    ACCOUNT_SIGNUP_FORM_CLASS=None,
    ACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.MANDATORY,
)
class GoogleLoginTests(OAuth2TestsMixin, TestCase):
    provider_id = GoogleProvider.id

    # helper method to get mocked allauth response for an existing google account
    def get_mocked_response(
        self,
        family_name="last",
        given_name="first",
        name="first last",
        email="test@test.com",
        verified_email=True,
    ):
        return MockedResponse(
            200,
            """
              {"family_name": "%s", "name": "%s",
               "picture": "https://lh5.googleusercontent.com/photo.jpg",
               "locale": "nl", "gender": "male",
               "email": "%s",
               "link": "https://plus.google.com/108204268033311374519",
               "given_name": "%s", "id": "108204268033311374519",
               "verified_email": %s }
        """
            % (
                family_name,
                name,
                email,
                given_name,
                (repr(verified_email).lower()),
            ),
        )

    def test_username_based_on_firstname(self):
        first_name = "first"
        last_name = "last"
        email = "test@test.com"
        self.login(
            self.get_mocked_response(
                name=first_name + " " + last_name,
                email=email,
                given_name=first_name,
                family_name=last_name,
                verified_email=True,
            )
        )
        user = User.objects.get(email=email)
        self.assertEqual(user.username, first_name)

    def test_email_verified(self):
        test_email = "test@test.com"
        self.login(self.get_mocked_response(verified_email=True))
        email_address = EmailAddress.objects.get(email=test_email, verified=True)
        self.assertFalse(
            EmailConfirmation.objects.filter(email_address__email=test_email).exists()
        )
        account = email_address.user.socialaccount_set.all()[0]
        self.assertEqual(account.extra_data["given_name"], "first")

    @override_settings(ACCOUNT_EMAIL_CONFIRMATION_HMAC=False)
    def test_email_not_verified(self):
        test_email = "test@test.com"
        self.login(self.get_mocked_response(verified_email=False))
        email_address = EmailAddress.objects.get(email=test_email)
        self.assertFalse(email_address.verified)
        self.assertTrue(
            EmailConfirmation.objects.filter(email_address__email=test_email).exists()
        )
    
    def test_account_connect(self):
        email = "test@test.com"
        user = User.objects.create(username="first", is_active=True, email=email)
        user.set_password("test")
        user.save()
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
        self.client.login(username=user.username, password="test")
        self.login(self.get_mocked_response(verified_email=True), process="connect")
        # Check if we connected...
        self.assertTrue(
            SocialAccount.objects.filter(user=user, provider=GoogleProvider.id).exists()
        )
        # For now, we do not pick up any new e-mail addresses on connect
        self.assertEqual(EmailAddress.objects.filter(user=user).count(), 1)
        self.assertEqual(EmailAddress.objects.filter(user=user, email=email).count(), 1)


class GoogleCalendarTests(TestCase):

    # helper method to get mocked response for an 2 existing calendar events
    def get_calendar_mocked_response(self):
        mocked_response_json = {
            "upcoming": [
                            {
                                "name": "test",
                                "link": "htmlLink",
                                "start": {
                                    "dateTime": "2019-06-03T02:00:00+09:00"
                                },
                            },
                            {
                                "name": "test",
                                "link": "htmlLink",
                                "start": {
                                    "dateTime": "2019-06-03T02:00:00+09:00"
                                },
                            },
                        ]
            },
        return mocked_response_json

    @unittest.mock.patch('googleapiclient.discovery.build')
    def test_valid_token(mock_build, mock_renew_token):
        credentials = unittest.mock.Mock(valid=True)
        build('calendar', 'v3', credentials=credentials)
        assert not mock_renew_token.called

    @unittest.mock.patch('googleapiclient.discovery.Resource')
    def test_fetch_events(self, mock_resource):
        mock_resource.events.return_value.list.return_value.execute.return_value = self.get_calendar_mocked_response()
        events_result = mock_resource.events().list(calendarId='primary').execute()[0]
        events = events_result.get('upcoming', [])
        assert 2 == len(events)

    @unittest.mock.patch('googleapiclient.discovery.Resource')
    def test_fetch_no_events(self, mock_resource):
        mock_resource.events.return_value.list.return_value.execute.return_value = {}
        events_result = mock_resource.events().list(calendarId='primary').execute()
        assert 0 == len(events_result)



def createCourse(department, numb):
    return Course.objects.create(dept = department, num = numb)


class CoursePageTests(TestCase):
    def test_no_courses(self):
        response = self.client.get(reverse('core:Courses'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['all_courses_list'], [])

    def test_add_course(self):
        q = createCourse(department = "CS", numb = 2110)
        response = self.client.get(reverse('core:Courses'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Course.objects.count(), 1)
        self.assertQuerysetEqual(
            response.context['all_courses_list'],
            [q],
        )

#http://www.semicolom.com/blog/test-a-django-model-with-a-filefield/
class UploadModelCreateViewTestCase(TestCase):
    def test_form_valid(self):
        """
        tests the Upload model
        """
        #q = createCourse(department = "CS", numb = 2110)
        file_mock = mock.MagicMock(spec=File)
        file_mock.name = 'test.pdf'
        file_model = Upload(upload_file=file_mock)
        self.assertEqual(file_model.upload_file.name, file_mock.name)
        
    def test_upload_view_no_uploads(self):
        response = self.client.get(reverse('core:upload_notes')) 
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Upload.objects.count(), 0)