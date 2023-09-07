import pkg_resources
import logging
from django.conf import settings as DJANGO_SETTINGS
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String, Dict, Float, Boolean, List, DateTime, JSONField
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from xblockutils.resources import ResourceLoader
from django.template import Context, Template
from django.urls import reverse
from lms.djangoapps.certificates.models import CertificateStatuses, GeneratedCertificate
from django.contrib.auth.models import User
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory

from xmodule.modulestore.django import modulestore
from django.http import HttpResponse, HttpResponseBadRequest,HttpResponseServerError
from lms.djangoapps.certificates.api import regenerate_user_certificates
log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)
# Make '_' a no-op so we can scrape strings


def _(text): return text


def reify(meth):
    """
    Decorator which caches value so it is only computed once.
    Keyword arguments:
    inst
    """
    def getter(inst):
        """
        Set value to meth name in dict and returns value.
        """
        value = meth(inst)
        inst.__dict__[meth.__name__] = value
        return value
    return property(getter)


class CertificateLinkXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        display_name="Display Name",
        help="Display name for this module",
        default="Generar Certificado",
        scope=Scope.settings,
    )
    has_author_view = True
    has_score = False
    editable_fields = ('display_name')

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    @reify
    def block_course_id(self):
        """
        Return the course_id of the block.
        """
        return str(self.course_id)


    def get_certificate(self):
        # this function is in charge of searching for student, course_key and enrollment which are necessary to get_cert_data(),
        # this comes from courseware and is the one in charge of generating the certificates, it also controls the different # states that the certificates can have.
        # different states that the certificates can have.   
        from lms.djangoapps.courseware.views.views import get_cert_data
        from lms.djangoapps.courseware.courses import get_course_with_access
        from common.djangoapps.student.models import CourseEnrollment

        student = User.objects.get(id=self.scope_ids.user_id)
        course_key = self.course_id 
        course = get_course_with_access(student, 'load', course_key, check_if_enrolled=True)
        enrollment_mode, _ = CourseEnrollment.enrollment_mode_for_user(student, course_key)
        
        cert = get_cert_data(student,course, enrollment_mode)
        return cert

    def author_view(self, context=None):
        context = {}
        template = self.render_template(
            'static/html/author_view.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/view_certificate.css"))
        return frag

    def studio_view(self, context):
        """
        Render a form for editing this XBlock
        """
        fragment = Fragment()
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
        }
        fragment.content = self.render_template(
            'static/html/studio_view.html', context)
        fragment.add_css(self.resource_string("static/css/view_certificate.css"))
        fragment.add_javascript(self.resource_string(
            "static/js/src/view_certificate_studio.js"))
        fragment.initialize_js('CertificateLinkXBlock')
        return fragment

    def student_view(self, context=None):
        context = self.get_context_student()
        template = self.render_template(
            'static/html/view_certificate.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/view_certificate.css"))
        frag.add_javascript(self.resource_string(
            "static/js/src/view_certificate.js"))
        frag.initialize_js('CertificateLinkXBlock')
        return frag

    def _get_course_grade_passed(self):
        """
            Get 'passed' (Boolean representing whether the course has been
                    passed according to the course's grading policy.)
        """
        course_grade = CourseGradeFactory().read(User.objects.get(id=self.scope_ids.user_id), course_key=self.course_id)
        return course_grade.passed
 
    def get_context_student(self):
        # the context is given the function get_certificate(), post_url() that creates the path with the course_id and the status of the certificates that will be needed for the html. 
        # the status of the certificates that will be needed for the html.
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'cert': self.get_certificate(),
            'post_url': reverse('generate_user_cert', args=[str(self.course_id)]),
            'CertificateStatuses': CertificateStatuses(),
            'passed': self._get_course_grade_passed()
        }
        return context
    

    @XBlock.json_handler
    def certificate_data(self, data, suffix=''):
        # this def gets directly the cert_web_view_url to be able to use it in the js. If the url exists, I send it empty, 
        # until it generates it
        cert_Url = self.get_certificate()
        if cert_Url and cert_Url.cert_web_view_url:
            context = {
                'cert': cert_Url.cert_web_view_url,        
            }
        else: 
            context = {
                'cert': ""
            }
        return context

    @XBlock.json_handler
    def regenerate_certificate_for_user(self, data, suffix=''):
        log.info("entramos?")
        from common.djangoapps.student.models import CourseEnrollment
        user = User.objects.get(id=self.scope_ids.user_id)
        # Check that the course exists
        course = modulestore().get_course(self.course_id)
        if course is None:
            msg = _("The course {course_key} does not exist").format(course_key= str(self.course_id))
            return {"error":msg}

        # Check that the user is enrolled in the course
        if not CourseEnrollment.is_enrolled(user, self.course_id):
            msg = _("User {username} is not enrolled in the course {course_key}").format(
                username=user.username,
                course_key=str(self.course_id)
            )
            return {"error":msg}
        
        cert = GeneratedCertificate.certificate_for_student(user, self.course_id)
        if cert is None:
            msg = _("User {username} dont have a certificate in this course {course_key}").format(
                username=user.username,
                course_key=str(self.course_id)
            )
            return {"error":msg}


        # Attempt to regenerate certificates
        try:
            regenerate_user_certificates(user, self.course_id, course=course)
            print("AAAAAAAAAAALOOOOOOOOOOOOOOO")
        except Exception :  # pylint: disable=bare-except
            # We are pessimistic about the kinds of errors that might get thrown by the
            # certificates API.  This may be overkill, but we're logging everything so we can
            # track down unexpected errors.
            log.exception(
                "Could not regenerate certificates for user %s in course %s",
                user.id,
                str(self.course_id)
            )
            return {"error":_("An unexpected error occurred while regenerating certificates.")}

        log.info(
            "Started regenerating certificates for user %s in course %s from the support page.",
            user.id, str(self.course_id)
        )
        return {"result": "success"}

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        self.display_name = data.get('display_name')
        return {'result': 'success'}

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("CertificateLinkXBlock",
             """<generate_certificate/>
             """),
            ("Multiple CertificateLinkXBlock",
             """<vertical_demo>
                <generate_certificate/>
                <generate_certificate/>
                <generate_certificate/>
                </vertical_demo>
             """),
        ]