#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Matrix Synapse 安全配置验证脚本
验证监控、日志和安全配置的完整性
"""

import os
import re
import sys
from pathlib import Path

class SecurityConfigValidator:
    def __init__(self, synapse_root):
        self.synapse_root = Path(synapse_root)
        self.config_dir = self.synapse_root / "config"
        
    def check_file_content(self, file_path, patterns):
        """检查文件内容是否包含指定的模式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            results = {}
            for name, pattern in patterns.items():
                results[name] = bool(re.search(pattern, content, re.MULTILINE | re.DOTALL))
            return results
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
            return {name: False for name in patterns.keys()}
    
    def validate_security_config(self):
        """验证安全配置模块"""
        print("\n=== 验证安全配置模块 ===")
        
        # 检查服务器配置中的安全设置
        server_config_file = self.config_dir / "server.py"
        server_patterns = {
            "IP黑名单配置": r"ip_range_blacklist|ip_range_blocklist",
            "默认IP黑名单": r"DEFAULT_IP_RANGE_BLOCKLIST",
            "IP白名单配置": r"ip_range_allowlist|ip_range_whitelist",
            "监听器配置": r"class.*ListenerConfig",
            "HTTP配置": r"class.*HttpListenerConfig",
            "TLS配置": r"tls.*True|tls.*False",
            "X-Forwarded配置": r"x_forwarded",
            "CORS配置": r"experimental_cors_msc3886"
        }
        
        server_results = self.check_file_content(server_config_file, server_patterns)
        
        print("服务器安全配置:")
        for check, passed in server_results.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            
        return all(server_results.values())
    
    def validate_ratelimit_config(self):
        """验证速率限制配置模块"""
        print("\n=== 验证速率限制配置模块 ===")
        
        ratelimit_config_file = self.config_dir / "ratelimiting.py"
        ratelimit_patterns = {
            "速率限制设置类": r"class RatelimitSettings",
            "联邦速率限制": r"class FederationRatelimitSettings",
            "消息速率限制": r"rc_message",
            "注册速率限制": r"rc_registration",
            "登录速率限制": r"rc_login",
            "房间加入速率限制": r"rc_joins",
            "邀请速率限制": r"rc_invites",
            "密钥请求速率限制": r"rc_key_requests",
            "3PID验证速率限制": r"rc_3pid_validation"
        }
        
        ratelimit_results = self.check_file_content(ratelimit_config_file, ratelimit_patterns)
        
        print("速率限制配置:")
        for check, passed in ratelimit_results.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            
        return all(ratelimit_results.values())
    
    def validate_metrics_config(self):
        """验证监控配置模块"""
        print("\n=== 验证监控配置模块 ===")
        
        metrics_config_file = self.config_dir / "metrics.py"
        metrics_patterns = {
            "监控配置类": r"class MetricsConfig",
            "启用监控": r"enable_metrics",
            "监控端口": r"metrics_port",
            "监控绑定主机": r"metrics_bind_host",
            "统计报告": r"report_stats",
            "Sentry配置": r"sentry_enabled|sentry_dsn"
        }
        
        metrics_results = self.check_file_content(metrics_config_file, metrics_patterns)
        
        print("监控配置:")
        for check, passed in metrics_results.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            
        return all(metrics_results.values())
    
    def validate_logging_config(self):
        """验证日志配置模块"""
        print("\n=== 验证日志配置模块 ===")
        
        logging_config_file = self.config_dir / "logger.py"
        logging_patterns = {
            "日志配置类": r"class LoggingConfig",
            "日志配置文件": r"log_config",
            "标准输入输出重定向": r"no_redirect_stdio",
            "默认日志配置": r"DEFAULT_LOG_CONFIG",
            "日志格式化": r"formatter|format",
            "日志处理器": r"handler|Handler"
        }
        
        logging_results = self.check_file_content(logging_config_file, logging_patterns)
        
        print("日志配置:")
        for check, passed in logging_results.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            
        return all(logging_results.values())
    
    def validate_tls_security_config(self):
        """验证TLS安全配置模块"""
        print("\n=== 验证TLS安全配置模块 ===")
        
        tls_config_file = self.config_dir / "tls.py"
        tls_patterns = {
            "TLS配置类": r"class TlsConfig",
            "TLS证书路径": r"tls_certificate_path",
            "TLS私钥路径": r"tls_private_key_path",
            "联邦证书验证": r"federation_verify_certificates",
            "联邦TLS版本": r"federation_client_minimum_tls_version",
            "证书验证白名单": r"federation_certificate_verification_whitelist",
            "自定义CA证书": r"federation_custom_ca_list",
            "不安全SSL客户端": r"use_insecure_ssl_client_just_for_testing_do_not_use"
        }
        
        tls_results = self.check_file_content(tls_config_file, tls_patterns)
        
        print("TLS安全配置:")
        for check, passed in tls_results.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            
        return all(tls_results.values())
    
    def validate_api_security_config(self):
        """验证API安全配置模块"""
        print("\n=== 验证API安全配置模块 ===")
        
        api_config_file = self.config_dir / "api.py"
        api_patterns = {
            "API配置类": r"class ApiConfig",
            "房间预加入状态": r"room_prejoin_state",
            "用户IP跟踪": r"track_puppeted_user_ips",
            "状态过滤器": r"StateFilter",
            "配置验证": r"validate_config",
            "默认预加入状态": r"_DEFAULT_PREJOIN_STATE_TYPES_AND_STATE_KEYS"
        }
        
        api_results = self.check_file_content(api_config_file, api_patterns)
        
        print("API安全配置:")
        for check, passed in api_results.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            
        return all(api_results.values())
    
    def run_validation(self):
        """运行所有验证"""
        print("Matrix Synapse 安全配置验证")
        print("=" * 50)
        
        results = {
            "安全配置": self.validate_security_config(),
            "速率限制配置": self.validate_ratelimit_config(),
            "监控配置": self.validate_metrics_config(),
            "日志配置": self.validate_logging_config(),
            "TLS安全配置": self.validate_tls_security_config(),
            "API安全配置": self.validate_api_security_config()
        }
        
        print("\n=== 验证总结 ===")
        all_passed = True
        for module, passed in results.items():
            status = "✓" if passed else "✗"
            print(f"{status} {module}: {'通过' if passed else '失败'}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 所有安全配置模块验证通过！")
            return True
        else:
            print("\n❌ 部分安全配置模块验证失败，请检查相关配置。")
            return False

def main():
    # 获取Synapse代码根目录
    current_dir = Path(__file__).parent
    synapse_root = current_dir
    
    # 创建验证器并运行验证
    validator = SecurityConfigValidator(synapse_root)
    success = validator.run_validation()
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()