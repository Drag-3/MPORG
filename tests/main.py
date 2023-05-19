import os
import unittest
import xmlrunner
from acrcloud import acrcloud_extr_tool, recognizer

if __name__ == '__main__':
    root_dir = os.path.dirname(__file__)
    test_loader = unittest.TestLoader()
    package_tests = test_loader.discover(start_dir=root_dir)

    with open("test-results.xml", 'wb') as report:
        testRunner = xmlrunner.XMLTestRunner(output=report)
        testRunner.run(package_tests)