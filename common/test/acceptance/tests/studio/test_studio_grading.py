"""
Acceptance tests for grade settings in Studio.
"""
from common.test.acceptance.pages.studio.settings_graders import GradingPage
from common.test.acceptance.tests.studio.base_studio_test import StudioCourseTest
from common.test.acceptance.pages.studio.overview import CourseOutlinePage
from common.test.acceptance.fixtures.course import XBlockFixtureDesc


class GradingPageTest(StudioCourseTest):
    """
    Bockchoy tests to add/edit grade settings in studio.
    """

    url = None

    def setUp(self):  # pylint: disable=arguments-differ
        super(GradingPageTest, self).setUp()
        self.grading_page = GradingPage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )

        self.grading_page.visit()

    def populate_course_fixture(self, course_fixture):
        """
        Return a test course fixture.
        """
        course_fixture.add_children(
            XBlockFixtureDesc("chapter", "Test Section").add_children(
                XBlockFixtureDesc("sequential", "Test Subsection").add_children(
                )
            )
        )

    def test_add_grade_range(self):
        """
        Scenario: Users can add grading ranges
            Given I have opened a new course in Studio
            And I am viewing the grading settings
            When I add "1" new grade
            Then I see I now have "3"
        """
        length = self.grading_page.total_number_of_grades
        self.grading_page.click_add_grade()
        self.assertTrue(self.grading_page.is_grade_added(length))
        self.grading_page.save()
        self.grading_page.refresh_and_wait_for_load()
        total_number_of_grades = self.grading_page.total_number_of_grades
        self.assertEqual(total_number_of_grades, 3)

    def test_staff_can_add_up_to_five_grades_only(self):
        """
        Scenario: Users can only have up to 5 grading ranges
            Given I have opened a new course in Studio
            And I am viewing the grading settings
            When I try to add more than 5 grades
            Then I see I have only "5" grades
        """
        for grade_ordinal in range(1, 5):
            length = self.grading_page.total_number_of_grades
            self.grading_page.click_add_grade()
            # By default page has 2 grades, so greater than 3 means, attempt is made to add 6th grade
            if grade_ordinal > 3:
                self.assertFalse(self.grading_page.is_grade_added(length))
            else:
                self.assertTrue(self.grading_page.is_grade_added(length))
        self.grading_page.save()
        self.grading_page.refresh_and_wait_for_load()
        total_number_of_grades = self.grading_page.total_number_of_grades
        self.assertEqual(total_number_of_grades, 5)

    def test_grades_remain_consistent(self):
        """
        Scenario: When user removes a grade the remaining grades should be consistent
            Given I have opened a new course in Studio
            And I am viewing the grading settings
            When I add "2" new grade
            Then Grade list has "A,B,C,F" grades
            And I delete a grade
            Then Grade list has "A,B,F" grades
        """
        for _ in range(2):
            length = self.grading_page.total_number_of_grades
            self.grading_page.click_add_grade()
            self.assertTrue(self.grading_page.is_grade_added(length))
        self.grading_page.save()
        grades_alphabets = self.grading_page.grade_letters
        self.assertEqual(grades_alphabets, ['A', 'B', 'C', 'F'])
        self.grading_page.remove_grades(1)
        self.grading_page.save()
        grades_alphabets = self.grading_page.grade_letters
        self.assertEqual(grades_alphabets, ['A', 'B', 'F'])

    def test_staff_can_delete_grade_range(self):
        """
        Scenario: Users can delete grading ranges
            Given I have opened a new course in Studio
            And I am viewing the grading settings
            When I add "1" new grade
            And I delete a grade
            Then I see I now have "2" grades
        """
        length = self.grading_page.total_number_of_grades
        self.grading_page.click_add_grade()
        self.assertTrue(self.grading_page.is_grade_added(length))
        self.grading_page.save()
        total_number_of_grades = self.grading_page.total_number_of_grades
        self.assertEqual(total_number_of_grades, 3)
        self.grading_page.remove_grades(1)
        total_number_of_grades = self.grading_page.total_number_of_grades
        self.assertEqual(total_number_of_grades, 2)

    def test_staff_can_move_grading_ranges(self):
        """
        Scenario: Users can move grading ranges
            Given I have opened a new course in Studio
            And I am viewing the grading settings
            When I move a grading section
            Then I see that the grade range has changed
        """
        grade_ranges = self.grading_page.grades_range
        self.assertIn('0-50', grade_ranges)
        self.grading_page.drag_and_drop_grade()
        grade_ranges = self.grading_page.grades_range
        self.assertIn(
            '0-3',
            grade_ranges,
            'expected range: 0-3, not found in grade ranges:{}'.format(grade_ranges)
        )

    def test_modify_assignment_type(self):
        """
        Scenario: Users can modify Assignment types
            Given I have populated a new course in Studio
            And I am viewing the grading settings
            When I change assignment type "Homework" to "New Type"
            And I press the "Save" notification button
            And I go back to the main course page
            Then I do see the assignment name "New Type"
            And I do not see the assignment name "Homework"
        """
        self.grading_page.change_assignment_name('Homework', 'New Type')
        self.grading_page.save()
        course_outline_page = CourseOutlinePage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )
        course_outline_page.visit()
        subsection = course_outline_page.section('Test Section').subsection('Test Subsection')
        modal = subsection.edit()
        # Set new values
        modal.policy = 'New Type'
        modal.save()
        grade = course_outline_page.policy
        self.assertEqual(grade, 'New Type')
