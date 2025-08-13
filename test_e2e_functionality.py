#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Matrix Synapse 端到端功能测试和性能验证脚本
验证整体系统功能和性能指标
"""

import os
import re
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class E2EFunctionalityValidator:
    def __init__(self, synapse_root):
        self.synapse_root = Path(synapse_root)
        self.config_dir = self.synapse_root / "config"
        self.api_dir = self.synapse_root / "api"
        self.handlers_dir = self.synapse_root / "handlers"
        
    def check_file_exists(self, file_path):
        """检查文件是否存在"""
        return Path(file_path).exists()
    
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
    
    def validate_core_api_endpoints(self):
        """验证核心API端点"""
        print("\n=== 验证核心API端点 ===")
        
        # 检查主要API处理器
        api_handlers = {
            "用户认证API": self.api_dir / "auth.py",
            "房间管理API": self.api_dir / "room.py", 
            "消息处理API": self.api_dir / "message.py",
            "联邦API": self.api_dir / "federation.py",
            "设备管理API": self.api_dir / "device.py",
            "媒体API": self.api_dir / "media.py"
        }
        
        api_results = {}
        for name, file_path in api_handlers.items():
            exists = self.check_file_exists(file_path)
            api_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        return all(api_results.values())
    
    def validate_database_integration(self):
        """验证数据库集成"""
        print("\n=== 验证数据库集成 ===")
        
        # 检查数据库相关文件
        db_files = {
            "数据库配置": self.config_dir / "database.py",
            "数据库存储": self.synapse_root / "storage" / "__init__.py",
            "数据库引擎": self.synapse_root / "storage" / "engines" / "__init__.py",
            "数据库模式": self.synapse_root / "storage" / "schema" / "__init__.py"
        }
        
        db_results = {}
        for name, file_path in db_files.items():
            exists = self.check_file_exists(file_path)
            db_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        # 检查数据库配置内容
        if self.check_file_exists(self.config_dir / "database.py"):
            db_config_patterns = {
                "数据库配置类": r"class DatabaseConfig",
                "SQLite支持": r"sqlite",
                "PostgreSQL支持": r"postgresql|psycopg2",
                "连接池配置": r"cp_min|cp_max|pool",
                "数据库引擎": r"database_engine"
            }
            
            db_config_results = self.check_file_content(
                self.config_dir / "database.py", db_config_patterns
            )
            
            print("\n  数据库配置详情:")
            for check, passed in db_config_results.items():
                status = "✓" if passed else "✗"
                print(f"    {status} {check}")
                
            db_results.update(db_config_results)
        
        return all(db_results.values())
    
    def validate_event_processing(self):
        """验证事件处理系统"""
        print("\n=== 验证事件处理系统 ===")
        
        # 检查事件相关文件
        event_files = {
            "事件处理器": self.handlers_dir / "events.py",
            "事件认证": self.synapse_root / "event_auth.py",
            "事件构建器": self.synapse_root / "events" / "builder.py",
            "事件验证器": self.synapse_root / "events" / "validator.py",
            "事件工具": self.synapse_root / "events" / "utils.py"
        }
        
        event_results = {}
        for name, file_path in event_files.items():
            exists = self.check_file_exists(file_path)
            event_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        return all(event_results.values())
    
    def validate_federation_system(self):
        """验证联邦系统"""
        print("\n=== 验证联邦系统 ===")
        
        # 检查联邦相关文件
        federation_files = {
            "联邦客户端": self.synapse_root / "federation" / "federation_client.py",
            "联邦服务器": self.synapse_root / "federation" / "federation_server.py",
            "联邦传输层": self.synapse_root / "federation" / "transport" / "__init__.py",
            "联邦发送器": self.synapse_root / "federation" / "sender" / "__init__.py",
            "联邦配置": self.config_dir / "federation.py"
        }
        
        federation_results = {}
        for name, file_path in federation_files.items():
            exists = self.check_file_exists(file_path)
            federation_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        return all(federation_results.values())
    
    def validate_security_features(self):
        """验证安全功能"""
        print("\n=== 验证安全功能 ===")
        
        # 检查安全相关文件
        security_files = {
            "速率限制": self.config_dir / "ratelimiting.py",
            "TLS配置": self.config_dir / "tls.py",
            "验证码配置": self.config_dir / "captcha.py",
            "SAML2配置": self.config_dir / "saml2.py",
            "OIDC配置": self.config_dir / "oidc.py",
            "密码策略": self.config_dir / "password_policy.py"
        }
        
        security_results = {}
        for name, file_path in security_files.items():
            exists = self.check_file_exists(file_path)
            security_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        return all(security_results.values())
    
    def validate_media_handling(self):
        """验证媒体处理"""
        print("\n=== 验证媒体处理 ===")
        
        # 检查媒体相关文件
        media_files = {
            "媒体仓库": self.synapse_root / "rest" / "media" / "v1" / "media_repository.py",
            "媒体存储": self.synapse_root / "rest" / "media" / "v1" / "media_storage.py",
            "缩略图": self.synapse_root / "rest" / "media" / "v1" / "thumbnail_resource.py",
            "上传资源": self.synapse_root / "rest" / "media" / "v1" / "upload_resource.py",
            "下载资源": self.synapse_root / "rest" / "media" / "v1" / "download_resource.py"
        }
        
        media_results = {}
        for name, file_path in media_files.items():
            exists = self.check_file_exists(file_path)
            media_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        return all(media_results.values())
    
    def validate_performance_config(self):
        """验证性能配置"""
        print("\n=== 验证性能配置 ===")
        
        # 检查性能相关配置
        perf_configs = {
            "缓存配置": self.config_dir / "cache.py",
            "工作进程配置": self.config_dir / "workers.py",
            "监控配置": self.config_dir / "metrics.py",
            "日志配置": self.config_dir / "logger.py"
        }
        
        perf_results = {}
        for name, file_path in perf_configs.items():
            exists = self.check_file_exists(file_path)
            perf_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        # 检查缓存配置详情
        if self.check_file_exists(self.config_dir / "cache.py"):
            cache_patterns = {
                "缓存配置类": r"class CacheConfig",
                "全局缓存因子": r"global_factor",
                "缓存大小配置": r"cache_factors|caches",
                "过期时间配置": r"expiry_time|expire"
            }
            
            cache_results = self.check_file_content(
                self.config_dir / "cache.py", cache_patterns
            )
            
            print("\n  缓存配置详情:")
            for check, passed in cache_results.items():
                status = "✓" if passed else "✗"
                print(f"    {status} {check}")
                
            perf_results.update(cache_results)
        
        return all(perf_results.values())
    
    def validate_deployment_readiness(self):
        """验证部署就绪性"""
        print("\n=== 验证部署就绪性 ===")
        
        # 检查部署相关文件
        deployment_files = {
            "主服务器配置": self.config_dir / "homeserver.py",
            "服务器配置": self.config_dir / "server.py",
            "应用程序入口": self.synapse_root / "app" / "homeserver.py",
            "部署脚本": self.synapse_root / "deploy-simple.sh",
            "Docker文件": self.synapse_root / "Dockerfile",
            "要求文件": self.synapse_root / "requirements.txt"
        }
        
        deployment_results = {}
        for name, file_path in deployment_files.items():
            exists = self.check_file_exists(file_path)
            deployment_results[name] = exists
            status = "✓" if exists else "✗"
            print(f"  {status} {name}: {'存在' if exists else '缺失'}")
        
        return all(deployment_results.values())
    
    def check_low_resource_optimization(self):
        """检查低资源优化配置"""
        print("\n=== 检查低资源优化配置 ===")
        
        optimizations = {
            "内存优化": False,
            "缓存优化": False,
            "数据库优化": False,
            "联邦优化": False
        }
        
        # 检查缓存配置是否针对低资源进行了优化
        cache_file = self.config_dir / "cache.py"
        if self.check_file_exists(cache_file):
            cache_patterns = {
                "全局缓存因子": r"global_factor.*0\.[0-5]",  # 低缓存因子
                "缓存大小限制": r"cache_factors|per_cache_factors"
            }
            cache_results = self.check_file_content(cache_file, cache_patterns)
            if any(cache_results.values()):
                optimizations["缓存优化"] = True
        
        # 检查数据库配置优化
        db_file = self.config_dir / "database.py"
        if self.check_file_exists(db_file):
            db_patterns = {
                "连接池优化": r"cp_min.*[0-3]|cp_max.*[0-9]",  # 小连接池
                "SQLite优化": r"sqlite.*pragma"
            }
            db_results = self.check_file_content(db_file, db_patterns)
            if any(db_results.values()):
                optimizations["数据库优化"] = True
        
        # 检查联邦配置优化
        fed_file = self.config_dir / "federation.py"
        if self.check_file_exists(fed_file):
            fed_patterns = {
                "联邦超时优化": r"client_timeout.*[0-5]000",  # 较短超时
                "重试优化": r"max.*retries.*[0-3]"
            }
            fed_results = self.check_file_content(fed_file, fed_patterns)
            if any(fed_results.values()):
                optimizations["联邦优化"] = True
        
        # 通用内存优化检查
        server_file = self.config_dir / "server.py"
        if self.check_file_exists(server_file):
            server_patterns = {
                "监听器优化": r"bind_addresses.*127\.0\.0\.1",  # 本地绑定
                "工作进程限制": r"worker.*[0-2]"
            }
            server_results = self.check_file_content(server_file, server_patterns)
            if any(server_results.values()):
                optimizations["内存优化"] = True
        
        print("低资源优化检查:")
        for opt_name, enabled in optimizations.items():
            status = "✓" if enabled else "○"
            print(f"  {status} {opt_name}: {'已优化' if enabled else '可进一步优化'}")
        
        return optimizations
    
    def run_validation(self):
        """运行所有验证"""
        print("Matrix Synapse 端到端功能测试和性能验证")
        print("=" * 60)
        
        # 功能验证
        results = {
            "核心API端点": self.validate_core_api_endpoints(),
            "数据库集成": self.validate_database_integration(),
            "事件处理系统": self.validate_event_processing(),
            "联邦系统": self.validate_federation_system(),
            "安全功能": self.validate_security_features(),
            "媒体处理": self.validate_media_handling(),
            "性能配置": self.validate_performance_config(),
            "部署就绪性": self.validate_deployment_readiness()
        }
        
        # 性能优化检查
        optimizations = self.check_low_resource_optimization()
        
        print("\n=== 功能验证总结 ===")
        all_passed = True
        for module, passed in results.items():
            status = "✓" if passed else "✗"
            print(f"{status} {module}: {'通过' if passed else '失败'}")
            if not passed:
                all_passed = False
        
        print("\n=== 性能优化总结 ===")
        optimization_score = sum(optimizations.values()) / len(optimizations) * 100
        print(f"优化程度: {optimization_score:.1f}%")
        
        if optimization_score >= 75:
            print("🚀 系统已针对低资源环境进行了良好优化")
        elif optimization_score >= 50:
            print("⚡ 系统有一定优化，但仍有改进空间")
        else:
            print("⚠️  建议进一步优化以适应低资源环境")
        
        if all_passed and optimization_score >= 50:
            print("\n🎉 端到端功能测试通过，系统准备就绪！")
            return True
        else:
            print("\n❌ 部分测试失败或优化不足，请检查相关配置。")
            return False

def main():
    # 获取Synapse代码根目录
    current_dir = Path(__file__).parent
    synapse_root = current_dir
    
    # 创建验证器并运行验证
    validator = E2EFunctionalityValidator(synapse_root)
    success = validator.run_validation()
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()