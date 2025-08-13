#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Matrix Synapse处理器代码的功能完整性
检查用户注册、认证和房间管理相关的处理器是否包含必要的功能
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Set

class SynapseHandlerValidator:
    def __init__(self, synapse_root: str):
        self.synapse_root = Path(synapse_root)
        self.handlers_dir = self.synapse_root / "handlers"
        self.rest_dir = self.synapse_root / "rest"
        
        # 需要验证的功能模块
        self.required_features = {
            "用户注册": {
                "files": ["rest/client/register.py", "handlers/register.py"],
                "classes": ["RegisterRestServlet", "RegistrationHandler"],
                "methods": ["register_user", "check_username", "on_POST"]
            },
            "用户认证": {
                "files": ["rest/client/login.py", "handlers/auth.py"],
                "classes": ["LoginRestServlet", "AuthHandler"],
                "methods": ["on_POST", "check_password", "validate_login"]
            },
            "房间创建": {
                "files": ["rest/client/room.py", "handlers/room.py"],
                "classes": ["RoomCreateRestServlet", "RoomCreationHandler"],
                "methods": ["create_room", "on_POST", "_do"]
            },
            "房间成员管理": {
                "files": ["rest/client/room.py", "handlers/room_member.py"],
                "classes": ["RoomMembershipRestServlet", "RoomMemberHandler"],
                "methods": ["update_membership", "join", "leave", "invite"]
            },
            "消息发送": {
                "files": ["rest/client/room.py", "handlers/message.py"],
                "classes": ["RoomSendEventRestServlet", "MessageHandler"],
                "methods": ["send_event", "create_and_send_nonmember_event"]
            }
        }
    
    def check_file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        full_path = self.synapse_root / file_path
        return full_path.exists()
    
    def find_classes_in_file(self, file_path: str) -> Set[str]:
        """在文件中查找类定义"""
        full_path = self.synapse_root / file_path
        classes = set()
        
        if not full_path.exists():
            return classes
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找类定义
                class_pattern = r'^class\s+(\w+)\s*\([^)]*\)\s*:'
                matches = re.findall(class_pattern, content, re.MULTILINE)
                classes.update(matches)
        except Exception as e:
            print(f"⚠️  读取文件 {file_path} 时出错: {e}")
            
        return classes
    
    def find_methods_in_file(self, file_path: str) -> Set[str]:
        """在文件中查找方法定义"""
        full_path = self.synapse_root / file_path
        methods = set()
        
        if not full_path.exists():
            return methods
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找方法定义（包括async方法）
                method_pattern = r'^\s+(?:async\s+)?def\s+(\w+)\s*\([^)]*\)\s*:'
                matches = re.findall(method_pattern, content, re.MULTILINE)
                methods.update(matches)
        except Exception as e:
            print(f"⚠️  读取文件 {file_path} 时出错: {e}")
            
        return methods
    
    def validate_feature(self, feature_name: str, feature_config: Dict) -> Dict[str, any]:
        """验证单个功能模块"""
        result = {
            "feature": feature_name,
            "files_found": [],
            "files_missing": [],
            "classes_found": [],
            "classes_missing": [],
            "methods_found": [],
            "methods_missing": [],
            "success": True
        }
        
        # 检查文件
        for file_path in feature_config["files"]:
            if self.check_file_exists(file_path):
                result["files_found"].append(file_path)
            else:
                result["files_missing"].append(file_path)
                result["success"] = False
        
        # 检查类和方法（只在存在的文件中检查）
        all_classes = set()
        all_methods = set()
        
        for file_path in result["files_found"]:
            file_classes = self.find_classes_in_file(file_path)
            file_methods = self.find_methods_in_file(file_path)
            all_classes.update(file_classes)
            all_methods.update(file_methods)
        
        # 检查必需的类
        for class_name in feature_config["classes"]:
            if class_name in all_classes:
                result["classes_found"].append(class_name)
            else:
                result["classes_missing"].append(class_name)
        
        # 检查必需的方法
        for method_name in feature_config["methods"]:
            if method_name in all_methods:
                result["methods_found"].append(method_name)
            else:
                result["methods_missing"].append(method_name)
        
        return result
    
    def validate_all_features(self) -> List[Dict]:
        """验证所有功能模块"""
        results = []
        
        print(f"🔍 开始验证Matrix Synapse处理器功能完整性")
        print(f"📁 Synapse根目录: {self.synapse_root}\n")
        
        for feature_name, feature_config in self.required_features.items():
            print(f"🔧 验证功能: {feature_name}")
            result = self.validate_feature(feature_name, feature_config)
            results.append(result)
            
            # 输出验证结果
            if result["success"]:
                print(f"✅ {feature_name} - 功能完整")
            else:
                print(f"❌ {feature_name} - 功能不完整")
            
            # 详细信息
            if result["files_found"]:
                print(f"   📄 找到文件: {', '.join(result['files_found'])}")
            if result["files_missing"]:
                print(f"   ❌ 缺失文件: {', '.join(result['files_missing'])}")
            
            if result["classes_found"]:
                print(f"   🏗️  找到类: {', '.join(result['classes_found'])}")
            if result["classes_missing"]:
                print(f"   ❌ 缺失类: {', '.join(result['classes_missing'])}")
            
            if result["methods_found"]:
                print(f"   ⚙️  找到方法: {', '.join(result['methods_found'])}")
            if result["methods_missing"]:
                print(f"   ❌ 缺失方法: {', '.join(result['methods_missing'])}")
            
            print()
        
        return results
    
    def generate_summary(self, results: List[Dict]) -> None:
        """生成验证总结"""
        total_features = len(results)
        successful_features = sum(1 for r in results if r["success"])
        
        print("📊 验证总结:")
        print(f"   总功能模块: {total_features}")
        print(f"   完整功能: {successful_features}")
        print(f"   不完整功能: {total_features - successful_features}")
        print(f"   完整率: {successful_features/total_features*100:.1f}%")
        
        if successful_features == total_features:
            print("\n🎉 所有核心功能模块验证通过！")
        else:
            print("\n⚠️  部分功能模块需要检查")
            
            # 列出不完整的功能
            incomplete_features = [r["feature"] for r in results if not r["success"]]
            print(f"   不完整的功能: {', '.join(incomplete_features)}")

def main():
    """主函数"""
    # 获取Synapse代码根目录
    current_dir = Path.cwd()
    synapse_root = current_dir.parent  # 假设当前在test_deploy目录中
    
    if len(sys.argv) > 1:
        synapse_root = Path(sys.argv[1])
    
    print(f"Matrix Synapse代码根目录: {synapse_root}")
    
    if not synapse_root.exists():
        print(f"❌ 目录不存在: {synapse_root}")
        sys.exit(1)
    
    validator = SynapseHandlerValidator(str(synapse_root))
    
    try:
        results = validator.validate_all_features()
        validator.generate_summary(results)
        
        # 根据验证结果设置退出码
        all_success = all(r["success"] for r in results)
        sys.exit(0 if all_success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()