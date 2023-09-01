#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mock import patch, Mock, MagicMock
from collections import namedtuple
from django.urls import reverse
from django.test import TestCase, Client
from django.test import Client
from django.conf import settings
from django.contrib.auth.models import User
from common.djangoapps.util.testing import UrlResetMixin
from urllib.parse import parse_qs
from opaque_keys.edx.locator import CourseLocator
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from common.djangoapps.course_modes.models import CourseMode
from xblock.field_data import DictFieldData
from django.utils import timezone
import json
import urllib.parse
from .generate_certificate import CertificateLinkXBlock
from datetime import datetime
from pytz import UTC
from lms.djangoapps.certificates.models import CertificateTemplate, CertificateGenerationCourseSetting
from lms.djangoapps.certificates.models import CertificateStatuses, CertificateGenerationConfiguration
from lms.djangoapps.certificates.tests.factories import GeneratedCertificateFactory
# Create your tests here.

class TestRequest(object):
    # pylint: disable=too-few-public-methods
    # cuando solo consumimos una api externa. 
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None

class TestCertificateLinkXBlock(UrlResetMixin, ModuleStoreTestCase):

    def make_an_xblock(cls, course, **kw):
        """
        Helper method that creates a CertificateLinkXBlock
        """
        course = course
        runtime = Mock(
            course_id=course.id,
            user_is_staff=False,
            service=Mock(
                return_value=Mock(_catalog={}),
            ),
        )
        scope_ids = Mock()
        field_data = DictFieldData(kw)
        xblock = CertificateLinkXBlock(runtime, field_data, scope_ids)
        xblock.xmodule_runtime = runtime
        xblock.location = course.location
        xblock.course_id = course.id
        xblock.category = 'generate_certificate'
        return xblock

    def setUp(self):
        # aca se crea el curso y tambien se puede configurar el certificado

        super(TestCertificateLinkXBlock, self).setUp()
        self.course = CourseFactory.create(org='foo', course='baz', run='bar', start= datetime(2013, 9, 16, 7, 17, 28),certificate_available_date=datetime.now(UTC))
        self.course2 = CourseFactory.create(org='foo', course='xd', run='bar', start= datetime(2013, 9, 16, 7, 17, 28),certificate_available_date=datetime.now(UTC))
        aux = CourseOverview.get_from_id(self.course.id)
        aux2 = CourseOverview.get_from_id(self.course2.id)
        self.xblock = self.make_an_xblock(self.course)
        self.xblock2 = self.make_an_xblock(self.course2)

        cert_temp = CertificateTemplate(name= str(self.course.id), template= "", organization_id= 0
        ,course_key= self.course.id, mode= "honor")

        cert_gen_set= CertificateGenerationCourseSetting(course_key= str(self.course.id), self_generation_enabled= True
        ,language_specific_templates_enabled= False, include_hours_of_effort= None)
    
        CourseMode.objects.get_or_create(
            course_id=self.course.id,
            mode_display_name='honor',
            mode_slug='honor',
            min_price= 0,
        )

        with patch('common.djangoapps.student.models.cc.User.save'):
            self.student_client = Client()
            self.student = UserFactory(
                username='student',
                password='12345',
                email='student2@edx.org')
            self.studentHonor = UserFactory(
                username='studentHonor',
                password='12345',
                email='studentHonor@edx.org')

            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)
            self.assertTrue(
                self.student_client.login(
                    username='student',
                    password='12345'))
            CourseEnrollmentFactory(
                user=self.studentHonor, course_id=self.course.id, mode= "honor")
            CourseEnrollmentFactory(
                user=self.studentHonor, course_id=self.course2.id, mode= "honor") 
 
    def test_validate_field_data(self):
        """
            Verify if default xblock is created correctly
        """
        self.assertEqual(self.xblock.display_name, 'Generar Certificado')

    def test_edit_block_studio(self):
        """
            Verify submit studio edits is working
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
    
    def test_context_student(self):
        """
            Test context student view
        """
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context_student()
        self.assertIsNotNone(response['cert'])
        self.assertEqual(response['post_url'], "/courses/{}/generate_user_cert".format(str(self.course.id)))
        self.assertEqual(response['CertificateStatuses'].downloadable, CertificateStatuses.downloadable)
        self.assertEqual(response['passed'], False)

        self.assertEqual(response['cert'].cert_status,'audit_passing')
        self.assertEqual(response['cert'].title, "Your enrollment: Audit track")
        # self.assertEqual(response['cert'].msg, "You are enrolled in the audit track for this course. The audit track does not include a certificate")
        self.assertEqual(response['cert'].download_url, None)
        self.assertEqual(response['cert'].cert_web_view_url, None)
    
    @patch('lms.djangoapps.grades.course_grade_factory.CourseGradeFactory.read')
    def test_context_student_2(self, coursegradefractory_read):
        grade = Mock()
        grade.passed = False


        coursegradefractory_read.return_value=grade 
 
        self.xblock.scope_ids.user_id = self.studentHonor.id
        response = self.xblock.get_context_student()
        self.assertEqual(response['cert'], None)
        self.assertEqual(response['post_url'], "/courses/{}/generate_user_cert".format(str(self.course.id)))
        # self.assertEqual(response['CertificateStatuses'].downloadable, CertificateStatuses.downloadable)
        self.assertFalse(response['passed'])
    
    @patch('openedx.core.djangoapps.certificates.api.can_show_certificate_message')
    @patch('lms.djangoapps.certificates.api.cert_generation_enabled')
    @patch('lms.djangoapps.certificates.api.get_active_web_certificate')
    @patch('lms.djangoapps.grades.course_grade_factory.CourseGradeFactory.read')
    def test_context_student_3(self, coursegradefractory_read, get_web_cert ,cert_api, auto_certs_api):
        # honor awaiting the certificate
        grade = Mock()
        grade.passed = True

        cert_api.return_value=True
        auto_certs_api.return_value=True
        get_web_cert.return_value= True
        # return the value of grade.passed
        coursegradefractory_read.return_value=grade 

        self.xblock.scope_ids.user_id = self.studentHonor.id
        response = self.xblock.get_context_student()
        self.assertIsNotNone(response['cert'])
        self.assertEqual(response['post_url'], "/courses/{}/generate_user_cert".format(str(self.course.id)))
        self.assertEqual(response['CertificateStatuses'].downloadable, CertificateStatuses.downloadable)
 
        self.assertEqual(response['cert'].cert_status,'requesting')
        self.assertEqual(response['cert'].title, "Congratulations, you qualified for a certificate!")
        # self.assertEqual(response['cert'].msg, "You are enrolled in the audit track for this course. The audit track does not include a certificate")
        self.assertEqual(response['cert'].download_url, None)
        self.assertEqual(response['cert'].cert_web_view_url, None)
    
    @patch('openedx.core.djangoapps.certificates.api.can_show_certificate_message')
    @patch('lms.djangoapps.certificates.api.cert_generation_enabled')
    @patch('lms.djangoapps.certificates.api.get_active_web_certificate')
    @patch('lms.djangoapps.grades.course_grade_factory.CourseGradeFactory.read')
    def test_context_student_4(self, coursegradefractory_read, get_web_cert ,cert_api, auto_certs_api):
        # with only one model
        grade = Mock()
        grade.passed = True
        cert_temp2 = CertificateTemplate(name= str(self.course2.id), template= "", organization_id= 0
        ,course_key= self.course2.id, mode= "honor")
        cert_api.return_value=False
        auto_certs_api.return_value=False
        get_web_cert.return_value= False
        
        coursegradefractory_read.return_value=grade

        self.xblock2.scope_ids.user_id = self.studentHonor.id
        response = self.xblock2.get_context_student()
        
        self.assertIsNone(response['cert'])
    
    @patch('openedx.core.djangoapps.certificates.api.can_show_certificate_message')
    @patch('lms.djangoapps.certificates.api.cert_generation_enabled')
    @patch('lms.djangoapps.certificates.api.get_active_web_certificate')
    @patch('lms.djangoapps.grades.course_grade_factory.CourseGradeFactory.read')
    def test_context_student_5(self, coursegradefractory_read, get_web_cert ,cert_api, auto_certs_api):
        #with two models
        grade = Mock()
        grade.passed = True
        cert_temp2 = CertificateTemplate(name= str(self.course2.id), template= "", organization_id= 0
        ,course_key= self.course2.id, mode= "honor")

        cert_gen_set2= CertificateGenerationCourseSetting(course_key= str(self.course2.id), self_generation_enabled= True
        ,language_specific_templates_enabled= False, include_hours_of_effort= None)
            
        cert_api.return_value=True
        auto_certs_api.return_value=False
        get_web_cert.return_value= False

        coursegradefractory_read.return_value=grade 

        self.xblock2.scope_ids.user_id = self.studentHonor.id
        response = self.xblock2.get_context_student()
        
        self.assertIsNone(response['cert'])
    
    @patch.dict('django.conf.settings.FEATURES', {'CERTIFICATES_HTML_VIEW': True})
    @patch('openedx.core.djangoapps.certificates.api.can_show_certificate_message')
    @patch('lms.djangoapps.certificates.api.cert_generation_enabled')
    @patch('lms.djangoapps.certificates.api.get_active_web_certificate')
    @patch('lms.djangoapps.grades.course_grade_factory.CourseGradeFactory.read')
    def test_context_student_6(self, coursegradefractory_read, get_web_cert ,cert_api, auto_certs_api):
        # student who has a certificate and passed
        grade = Mock()
        grade.passed = True
        cert_temp2 = CertificateTemplate(name= str(self.course2.id), template= "", organization_id= 0
        ,course_key= self.course2.id, mode= "honor")

        cert_gen_set2= CertificateGenerationCourseSetting(course_key= str(self.course2.id), self_generation_enabled= True
        ,language_specific_templates_enabled= False, include_hours_of_effort= None)
        verify_uuid = "d5abdada532940f5b32750b2efd9c060"
        GeneratedCertificateFactory.create(user = self.studentHonor,course_id= self.course2.id, status=CertificateStatuses.downloadable, download_url= "/prueba/certificado", verify_uuid= verify_uuid) 

            
        cert_api.return_value=True
        auto_certs_api.return_value=True
        get_web_cert.return_value= True
        coursegradefractory_read.return_value=grade 
        
        self.xblock2.scope_ids.user_id = self.studentHonor.id
        response = self.xblock2.get_context_student()

        self.assertIsNotNone(response['cert'])
        self.assertEqual(response['cert'].cert_status,'downloadable')
        self.assertEqual(response['cert'].title, "Your certificate is available")
        # self.assertEqual(response['cert'].msg, "You are enrolled in the audit track for this course. The audit track does not include a certificate")
        self.assertEqual(response['cert'].download_url, None)
        self.assertEqual(response['cert'].cert_web_view_url, "/certificates/{}".format(verify_uuid))

    @patch('openedx.core.djangoapps.certificates.api.can_show_certificate_message')
    @patch('lms.djangoapps.certificates.api.cert_generation_enabled')
    @patch('lms.djangoapps.certificates.api.get_active_web_certificate')
    def test_context_student_7(self, get_web_cert ,cert_api, auto_certs_api):
        #student has generated certificate but failed a course
        cert_temp2 = CertificateTemplate(name= str(self.course2.id), template= "", organization_id= 0
        ,course_key= self.course2.id, mode= "honor")

        cert_gen_set2= CertificateGenerationCourseSetting(course_key= str(self.course2.id), self_generation_enabled= True
        ,language_specific_templates_enabled= False, include_hours_of_effort= None)

        GeneratedCertificateFactory.create(user = self.studentHonor,course_id= self.course2.id, status=CertificateStatuses.notpassing) 
        cert_api.return_value=True
        auto_certs_api.return_value=False
        get_web_cert.return_value= True
        
        with patch('lms.djangoapps.grades.course_grade_factory.CourseGradeFactory.read') as mock_create:
            course_grade = mock_create.return_value
            course_grade.passed = False
            course_grade.summary = {'grade': 'notpassing', 'percent': 0.0, 'section_breakdown': [],
                                    'grade_breakdown': {}}        
            self.xblock2.scope_ids.user_id = self.studentHonor.id
            response = self.xblock2.get_context_student()

            self.assertIsNone(response['cert'])

    @patch('openedx.core.djangoapps.certificates.api.can_show_certificate_message')
    @patch('lms.djangoapps.certificates.api.cert_generation_enabled')
    @patch('lms.djangoapps.certificates.api.get_active_web_certificate')
    @patch('lms.djangoapps.grades.course_grade_factory.CourseGradeFactory.read')
    def test_context_student_8(self, coursegradefractory_read, get_web_cert ,cert_api, auto_certs_api):
        # student has honor certificate, changes to audit.
        grade = Mock()
        grade.passed = True

        GeneratedCertificateFactory.create(user = self.student,course_id= self.course.id, status=CertificateStatuses.downloadable, mode= "honor") 
    
        cert_api.return_value=True
        auto_certs_api.return_value=True
        get_web_cert.return_value= True
        coursegradefractory_read.return_value=grade 
        
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context_student()
        self.assertIsNotNone(response['cert'])
        self.assertEqual(response['post_url'], "/courses/{}/generate_user_cert".format(str(self.course.id)))
        self.assertEqual(response['CertificateStatuses'].downloadable, CertificateStatuses.downloadable)

        self.assertEqual(response['cert'].cert_status,'audit_passing')
        self.assertEqual(response['cert'].title, "Your enrollment: Audit track")
        # self.assertEqual(response['cert'].msg, "You are enrolled in the audit track for this course. The audit track does not include a certificate")
        self.assertEqual(response['cert'].download_url, None)
        self.assertEqual(response['cert'].cert_web_view_url, None)