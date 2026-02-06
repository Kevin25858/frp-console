"""
辅助函数测试模块
测试登录速率限制、重启频率限制等辅助功能
"""
import pytest
import time
from unittest.mock import patch


class TestLoginRateLimit:
    """登录速率限制测试类"""

    def test_check_login_rate_limit_first_attempt(self):
        """测试首次登录尝试"""
        from utils.helpers import check_login_rate_limit, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        allowed, message = check_login_rate_limit('192.168.1.1', max_attempts=5, lockout_time=900)
        assert allowed is True
        assert message == ''

    def test_check_login_rate_limit_under_limit(self):
        """测试未达到限制次数"""
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        ip = '192.168.1.2'
        
        # 记录4次失败（限制为5次）
        for i in range(4):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)
        
        allowed, message = check_login_rate_limit(ip, max_attempts=5, lockout_time=900)
        assert allowed is True
        assert message == ''

    def test_check_login_rate_limit_exceeded(self):
        """测试超过限制次数后被锁定"""
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        ip = '192.168.1.3'
        
        # 记录5次失败（达到限制）
        for i in range(5):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)
        
        # 第6次应该被锁定
        allowed, message = check_login_rate_limit(ip, max_attempts=5, lockout_time=900)
        assert allowed is False
        assert '登录失败次数过多' in message
        assert '秒后重试' in message

    def test_check_login_rate_limit_lockout_expires(self):
        """测试锁定时间过期后重置"""
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        ip = '192.168.1.4'
        
        # 记录5次失败
        for i in range(5):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=1)
        
        # 验证被锁定
        allowed, _ = check_login_rate_limit(ip, max_attempts=5, lockout_time=1)
        assert allowed is False
        
        # 等待锁定时间过期
        time.sleep(1.1)
        
        # 应该允许登录了
        allowed, message = check_login_rate_limit(ip, max_attempts=5, lockout_time=1)
        assert allowed is True
        assert message == ''

    def test_record_login_attempt_success(self):
        """测试记录成功登录"""
        from utils.helpers import record_login_attempt, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        ip = '192.168.1.5'
        
        # 先记录一些失败
        for i in range(3):
            record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)
        
        # 记录成功登录
        record_login_attempt(ip, success=True, max_attempts=5, lockout_time=900)
        
        # 计数应该被重置
        assert login_attempts[ip]['count'] == 0
        assert login_attempts[ip]['locked_until'] == 0

    def test_record_login_attempt_failure(self):
        """测试记录失败登录"""
        from utils.helpers import record_login_attempt, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        ip = '192.168.1.6'
        
        # 记录失败
        record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)
        
        assert login_attempts[ip]['count'] == 1
        
        # 再记录一次
        record_login_attempt(ip, success=False, max_attempts=5, lockout_time=900)
        
        assert login_attempts[ip]['count'] == 2

    def test_different_ips_independent(self):
        """测试不同IP的速率限制相互独立"""
        from utils.helpers import check_login_rate_limit, record_login_attempt, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        ip1 = '192.168.1.10'
        ip2 = '192.168.1.11'
        
        # IP1 达到限制
        for i in range(5):
            record_login_attempt(ip1, success=False, max_attempts=5, lockout_time=900)
        
        # IP1 被锁定
        allowed, _ = check_login_rate_limit(ip1, max_attempts=5, lockout_time=900)
        assert allowed is False
        
        # IP2 应该可以正常登录
        allowed, _ = check_login_rate_limit(ip2, max_attempts=5, lockout_time=900)
        assert allowed is True


class TestRestartLimit:
    """重启频率限制测试类"""

    def test_check_restart_limit_first_time(self):
        """测试首次重启"""
        from utils.helpers import check_restart_limit, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        allowed, message = check_restart_limit(1, max_restarts=3, window=300, cooldown=10)
        assert allowed is True
        assert message == ''

    def test_check_restart_limit_cooldown(self):
        """测试重启冷却时间"""
        from utils.helpers import check_restart_limit, record_restart, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        client_id = 1
        
        # 记录一次重启
        record_restart(client_id, success=True)
        
        # 立即再次重启应该被限制
        allowed, message = check_restart_limit(client_id, max_restarts=3, window=300, cooldown=10)
        assert allowed is False
        assert '重启过于频繁' in message
        assert '秒后重试' in message

    def test_check_restart_limit_window(self):
        """测试重启时间窗口限制"""
        from utils.helpers import check_restart_limit, record_restart, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        client_id = 2
        
        # 记录3次失败重启（限制为3次）
        for i in range(3):
            record_restart(client_id, success=False)
        
        # 第4次应该被限制
        allowed, message = check_restart_limit(client_id, max_restarts=3, window=300, cooldown=0)
        assert allowed is False
        assert '重启次数已达上限' in message

    def test_check_restart_limit_force(self):
        """测试强制重启忽略限制"""
        from utils.helpers import check_restart_limit, record_restart, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        client_id = 3
        
        # 记录多次失败重启
        for i in range(5):
            record_restart(client_id, success=False)
        
        # 强制重启应该允许
        allowed, message = check_restart_limit(client_id, max_restarts=3, window=300, cooldown=10, force=True)
        assert allowed is True
        assert message == ''

    def test_record_restart_success(self):
        """测试记录成功重启"""
        from utils.helpers import record_restart, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        client_id = 4
        
        # 记录一些失败
        for i in range(2):
            record_restart(client_id, success=False)
        
        assert restart_records[client_id]['consecutive_failures'] == 2
        
        # 记录成功
        record_restart(client_id, success=True)
        
        # 连续失败计数应该被重置
        assert restart_records[client_id]['consecutive_failures'] == 0

    def test_reset_restart_record(self):
        """测试重置重启记录"""
        from utils.helpers import record_restart, reset_restart_record, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        client_id = 5
        
        # 记录一些重启
        record_restart(client_id, success=True)
        record_restart(client_id, success=False)
        
        assert client_id in restart_records
        
        # 重置记录
        reset_restart_record(client_id)
        
        assert client_id not in restart_records

    def test_different_clients_independent(self):
        """测试不同客户端的重启限制相互独立"""
        from utils.helpers import check_restart_limit, record_restart, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        client1 = 10
        client2 = 11
        
        # Client1 达到限制
        for i in range(3):
            record_restart(client1, success=False)
        
        # Client1 被限制
        allowed, _ = check_restart_limit(client1, max_restarts=3, window=300, cooldown=0)
        assert allowed is False
        
        # Client2 应该可以正常重启
        allowed, _ = check_restart_limit(client2, max_restarts=3, window=300, cooldown=0)
        assert allowed is True


class TestHelperEdgeCases:
    """辅助函数边界情况测试类"""

    def test_check_restart_limit_nonexistent_client(self):
        """测试不存在的客户端重启检查"""
        from utils.helpers import check_restart_limit, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        # 检查不存在的客户端
        allowed, message = check_restart_limit(999, max_restarts=3, window=300, cooldown=10)
        assert allowed is True
        assert message == ''

    def test_record_restart_updates_timestamp(self):
        """测试重启记录更新时间戳"""
        from utils.helpers import record_restart, restart_records
        
        # 清空之前的记录
        restart_records.clear()
        
        client_id = 20
        
        # 记录第一次重启
        before_time = time.time()
        record_restart(client_id, success=True)
        after_time = time.time()
        
        last_restart = restart_records[client_id]['last_restart']
        assert before_time <= last_restart <= after_time

    def test_check_login_rate_limit_invalid_ip(self):
        """测试无效IP的登录限制"""
        from utils.helpers import check_login_rate_limit, login_attempts
        
        # 清空之前的记录
        login_attempts.clear()
        
        # 空IP应该也能正常工作
        allowed, message = check_login_rate_limit('', max_attempts=5, lockout_time=900)
        assert allowed is True
        assert message == ''