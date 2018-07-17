"""
Management command to change many user enrollments in many courses using
csv file.
"""
import csv
import logging
from os import path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from student.models import CourseEnrollment, User
from student.models import CourseEnrollmentAttribute

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Command(BaseCommand):
    """
        Management command to change many user enrollments in many
        courses using the csv file
        """

    help = """
        Change the enrollment status of all the users specified in
        the csv file in the specified course to specified course
        mode.
        Could be used to update Effected users by order
        placement issues. If number of students is a lot for the
        different courses.
        Similar to bulk_change_enrollment but uses the csv file
        input format and can enroll students in multiple courses.

        Example:
            $ ... bulk_change_enrollment_csv csv_file_path
        """

    def add_arguments(self, parser):
        """ Add argument to the command parser. """
        parser.add_argument(
            '--csv_file_path',
            required=True,
            help='Csv file path'
        )

    def handle(self, *args, **options):
        """ Main handler for the command."""
        file_path = options['csv_file_path']

        if not path.isfile(file_path):
            raise CommandError("File not found.")

        with open(file_path, 'rb') as file:
            file_reader = csv.DictReader(file)
            for row in file_reader:
                try:
                    course_key = CourseKey.from_string(row['course_id'])
                except InvalidKeyError:
                    raise CommandError('Invalid or non-existant course id {}'.format(row['course_id']))

                try:
                    user = User.objects.get(username=row['user'])
                except:
                    raise CommandError('Invalid or non-existant user {}'.format(row['user']))

                try:
                    # Student might be or not enrolled in course
                    course_enrollment = CourseEnrollment.get_or_create_enrollment(user=user, course_key=course_key)

                    if course_enrollment.mode == row['mode']:
                        logger.info("Student [%s] is already enrolled in Course [%s] in mode [%s].", user.username,
                                    course_key, course_enrollment.mode)
                        # set the enrollment to active if its not already active.
                        if not course_enrollment.is_active:
                            course_enrollment.is_active = True
                        course_enrollment.save()
                    else:
                        with transaction.atomic():
                            enrollment_attrs = []
                            course_enrollment.update_enrollment(
                                mode=row['mode'],
                                is_active=True,
                                skip_refund=True
                            )
                            course_enrollment.save()
                            if row['mode'] == 'credit':
                                enrollment_attrs.append({
                                    'namespace': 'credit',
                                    'name': 'provider_id',
                                    'value': course_key.org,
                                })
                                CourseEnrollmentAttribute.add_enrollment_attr(enrollment=course_enrollment,
                                                                              data_list=enrollment_attrs)
                except Exception as e:
                    logger.info("Unable to Update student [%s] course [%s] enrollment to mode [%s] "
                                "because of Exception [%s]", user.username, course_key, row['mode'], repr(e))
