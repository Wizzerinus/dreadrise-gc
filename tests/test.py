from unittest import TestResult, TestSuite

from tests.unittests.mana import TestMana


def run_tests():
    """Run the unit tests."""
    result = TestResult()
    suite = TestSuite()

    suite.addTest(TestMana('run_all'))
    suite.run(result)

    return result
