import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().discover(start_dir="./"))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
