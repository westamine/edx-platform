"""
Test the cancel_user_retirement_request management command
"""
import pytest

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from openedx.core.djangoapps.user_api.models import UserRetirementStatus, RetirementState
from student.tests.factories import UserFactory
from student.models import get_retired_email_by_email

pytestmark = pytest.mark.django_db


@pytest.fixture
def retirement_user():
    return UserFactory.create(username='test_user')


def _create_retirement_request(user):
    """
    Returns a UserRetirementStatus test fixture object that has been logged out and email-changed.
    """
    RetirementState.objects.create(
        state_name='PENDING',
        state_execution_order=1,
        required=True,
        is_dead_end_state=False
    )
    RetirementState.objects.create(
        state_name='RETIRING_LMS',
        state_execution_order=2,
        required=False,
        is_dead_end_state=False
    )
    status = UserRetirementStatus.create_retirement(user)
    status.save()
    # Simulate the initial logout retirement endpoint.
    user.email = get_retired_email_by_email(user.email)
    user.set_unusable_password()
    user.save()
    return status


def test_successful_cancellation(retirement_user):  # pylint: disable=redefined-outer-name
    """
    Test a successfully cancelled retirement request.
    """
    status = _create_retirement_request(retirement_user)
    call_command('cancel_user_retirement_request', status.original_email)
    # Confirm that no retirement status exists for the user.
    with pytest.raises(UserRetirementStatus.DoesNotExist):
        UserRetirementStatus.objects.get(original_email=retirement_user.email)
    # Ensure user can be retrieved using the original email address.
    User.objects.get(email=status.original_email)


def test_cancellation_in_unrecoverable_state(retirement_user):  # pylint: disable=redefined-outer-name
    """
    Test a failed cancellation of a retirement request due to the retirement already beginning.
    """
    status = _create_retirement_request(retirement_user)
    retiring_lms_state = RetirementState.objects.get(state_name='RETIRING_LMS')
    status.current_state = retiring_lms_state
    status.save()
    with pytest.raises(CommandError, match=r'Retirement requests can only be cancelled for users in the PENDING state'):
        call_command('cancel_user_retirement_request', status.original_email)


def test_cancellation_unknown_email_address(retirement_user):  # pylint: disable=redefined-outer-name
    """
    Test attempting to cancel a non-existent request of a user.
    """
    with pytest.raises(CommandError, match=r'No retirement request with email address'):
        call_command('cancel_user_retirement_request', retirement_user.email)
