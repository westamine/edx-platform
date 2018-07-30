"""
When a user requests retirement mistakenly
"""
from __future__ import print_function

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from openedx.core.djangoapps.user_api.models import UserRetirementStatus


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Implementation of the populate command
    """
    help = 'Cancels the retirement of a user who has requested retirement - but has not yet been retired.'

    def add_arguments(self, parser):
        parser.add_argument('email_address',
                            help='Email address of user whose retirement request will be cancelled.')

    def handle(self, *args, **options):
        """
        Execute the command.
        """
        email_address = options['email_address']

        try:
            # Load the user retirement status.
            retirement_status = UserRetirementStatus.objects.select_related('current_state').get(
                original_email=email_address
            )
        except UserRetirementStatus.DoesNotExist:
            raise CommandError("No retirement request with email address '{}' exists.".format(email_address))

        # Check if the user has started the retirement process -or- not.
        if retirement_status.current_state.state_name != 'PENDING':
            raise CommandError(
                "Retirement requests can only be cancelled for users in the PENDING state."
                " Current request state for '{}': {}".format(
                    email_address,
                    retirement_status.current_state.state_name
                )
            )

        # Load the user record using the retired email address -and- change the email address back.
        user = User.objects.get(email=retirement_status.retired_email)
        user.email = email_address
        user.save()

        # Delete the user retirement status record.
        # No need to delete the accompanying "permanent" retirement request record - it gets done via Django signal.
        retirement_status.delete()

        print("Successfully cancelled retirement request for user with email address '{}'.")
