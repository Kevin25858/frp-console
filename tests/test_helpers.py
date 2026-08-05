"""
辅助函数测试模块
测试登录速率限制功能
"""
import time


class TestLoginRateLimit:
    """登录速率限制测试类"""

    def test_check_login_rate_limit_first_attempt(self):
        from utils.helpers import check_login_rate_limit, login_attempts
        login_attempts.clear()

        allowed, message = check_login_rate_limit('192.168.1.1', max_attempts=5, lockout_time=900)
        assert allowed is True
        assert message == ''

    def test_check_login_rate_limit_under_limit(self):
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        login_attempts.clear()

        ip = '192.168.1.2'
        for i in range(4):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)

        allowed, message = check_login_rate_limit(ip, max_attempts=5, lockout_time=900)
        assert allowed is True
        assert message == ''

    def test_check_login_rate_limit_exceeded(self):
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        login_attempts.clear()

        ip = '192.168.1.3'
        for i in range(5):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)

        allowed, message = check_login_rate_limit(ip, max_attempts=5, lockout_time=900)
        assert allowed is False
        assert '登录失败次数过多' in message

    def test_check_login_rate_limit_lockout_expires(self):
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        login_attempts.clear()

        ip = '192.168.1.4'
        for i in range(5):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=1)

        allowed, _ = check_login_rate_limit(ip, max_attempts=5, lockout_time=1)
        assert allowed is False

        time.sleep(1.1)

        allowed, message = check_login_rate_limit(ip, max_attempts=5, lockout_time=1)
        assert allowed is True
        assert message == ''

    def test_record_login_attempt_success(self):
        from utils.helpers import record_login_attempt, login_attempts
        login_attempts.clear()

        ip = '192.168.1.5'
        for i in range(3):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)

        record_login_attempt(ip, success=True, max_attempts=5, lockout_time=900)

        assert login_attempts[ip]['count'] == 0
        assert login_attempts[ip]['locked_until'] == 0

    def test_record_login_attempt_failure(self):
        from utils.helpers import record_login_attempt, login_attempts
        login_attempts.clear()

        ip = '192.168.1.6'
        record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)
        assert login_attempts[ip]['count'] == 1

        record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)
        assert login_attempts[ip]['count'] == 2

    def test_different_ips_independent(self):
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        login_attempts.clear()

        ip1 = '192.168.1.10'
        ip2 = '192.168.1.11'

        for i in range(5):
            record_login_attempt(ip1, success=False, max_attempts=5, lockout_time=900)

        allowed, _ = check_login_rate_limit(ip1, max_attempts=5, lockout_time=900)
        assert allowed is False

        allowed, _ = check_login_rate_limit(ip2, max_attempts=5, lockout_time=900)
        assert allowed is True
