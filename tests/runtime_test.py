import unittest
import signal
import os

import stackimpact
from stackimpact.runtime import runtime_info, register_signal


class RuntimeTestCase(unittest.TestCase):

    def test_register_signal(self):
        if runtime_info.OS_WIN:
            return

        result = {'handler': 0}

        def _handler(signum, frame):
            result['handler'] += 1

        register_signal(signal.SIGUSR1, _handler)

        os.kill(os.getpid(), signal.SIGUSR1)
        os.kill(os.getpid(), signal.SIGUSR1)

        signal.signal(signal.SIGUSR1, signal.SIG_DFL)

        self.assertEqual(result['handler'], 2)


    '''def test_register_signal_default(self):
        result = {'handler': 0}

        def _handler(signum, frame):
            result['handler'] += 1

        register_signal(signal.SIGUSR1, _handler, once = True)

        os.kill(os.getpid(), signal.SIGUSR1)
        os.kill(os.getpid(), signal.SIGUSR1)

        self.assertEqual(result['handler'], 1)'''


if __name__ == '__main__':
    unittest.main()


