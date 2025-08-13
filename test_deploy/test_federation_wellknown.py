#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Matrix Synapse 联邦网络和Well-Known配置验证脚本

此脚本验证以下功能模块：
1. Well-Known配置 (.well-known/matrix/server 和 .well-known/matrix/client)
2. 联邦服务器处理 (接收和处理来自其他服务器的请求)
3. 联邦客户端处理 (向其他服务器发送请求)
4. 联邦配置选项 (域名白名单、证书验证等)
5. 联邦传输层 (HTTP传输和认证)
"""

import os
import sys
import re
from typing import List, Dict, Any

class FederationWellKnownValidator:
    """联邦网络和Well-Known配置验证器"""
    
    def __init__(self, synapse_root: str):
        self.synapse_root = synapse_root
        self.validation_results = []
        
    def validate_module(self, module_name: str, file_path: str, 
                       required_classes: List[str], 
                       key_methods: Dict[str, List[str]]) -> bool:
        """验证模块是否包含必要的类和方法"""
        try:
            # 检查文件是否存在
            full_path = os.path.join(self.synapse_root, file_path)
            if not os.path.exists(full_path):
                print(f"❌ {module_name}: 文件不存在 - {file_path}")
                return False
                
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查必要的类
            missing_classes = []
            for class_name in required_classes:
                class_pattern = rf'class\s+{re.escape(class_name)}\s*[\(:]'
                if not re.search(class_pattern, content):
                    missing_classes.append(class_name)
                    
            if missing_classes:
                print(f"❌ {module_name}: 缺少类 - {', '.join(missing_classes)}")
                return False
                
            # 检查关键方法
            for class_name, methods in key_methods.items():
                # 找到类的定义位置
                class_pattern = rf'class\s+{re.escape(class_name)}\s*[\(:]'
                class_match = re.search(class_pattern, content)
                if class_match:
                    # 从类定义开始查找方法
                    class_start = class_match.start()
                    class_content = content[class_start:]
                    
                    missing_methods = []
                    for method in methods:
                        # 查找方法定义（def method_name 或 async def method_name）
                        method_pattern = rf'(?:async\s+)?def\s+{re.escape(method)}\s*\('
                        if not re.search(method_pattern, class_content):
                            missing_methods.append(method)
                    
                    if missing_methods:
                        print(f"❌ {module_name}.{class_name}: 缺少方法 - {', '.join(missing_methods)}")
                        return False
                        
            print(f"✅ {module_name}: 验证通过")
            return True
            
        except Exception as e:
            print(f"❌ {module_name}: 验证失败 - {str(e)}")
            return False
    
    def run_validation(self) -> bool:
        """运行所有验证"""
        print("开始验证Matrix Synapse联邦网络和Well-Known配置...\n")
        
        # 定义要验证的模块
        modules_to_validate = [
            {
                "name": "Well-Known配置",
                "file_path": "rest/well_known.py",
                "required_classes": ["WellKnownBuilder", "ClientWellKnownResource", "ServerWellKnownResource"],
                "key_methods": {
                    "WellKnownBuilder": ["get_well_known"],
                    "ClientWellKnownResource": ["render_GET"],
                    "ServerWellKnownResource": ["render_GET"]
                }
            },
            {
                "name": "联邦服务器处理",
                "file_path": "federation/federation_server.py",
                "required_classes": ["FederationServer"],
                "key_methods": {
                    "FederationServer": ["on_incoming_transaction", "on_pdu_request", "on_room_state_request"]
                }
            },
            {
                "name": "联邦客户端处理",
                "file_path": "federation/federation_client.py",
                "required_classes": ["FederationClient"],
                "key_methods": {
                    "FederationClient": ["make_query", "get_pdu", "send_join"]
                }
            },
            {
                "name": "联邦配置",
                "file_path": "config/federation.py",
                "required_classes": ["FederationConfig"],
                "key_methods": {
                    "FederationConfig": ["read_config"]
                }
            },
            {
                "name": "联邦传输层",
                "file_path": "federation/transport/server/federation.py",
                "required_classes": ["BaseFederationServerServlet", "FederationSendServlet"],
                "key_methods": {
                    "FederationSendServlet": ["on_PUT"],
                    "BaseFederationServerServlet": ["__init__"]
                }
            }
        ]
        
        # 执行验证
        all_passed = True
        for module_config in modules_to_validate:
            result = self.validate_module(
                module_config["name"],
                module_config["file_path"],
                module_config["required_classes"],
                module_config["key_methods"]
            )
            self.validation_results.append({
                "module": module_config["name"],
                "passed": result
            })
            if not result:
                all_passed = False
        
        # 输出总结
        print("\n" + "="*50)
        print("联邦网络和Well-Known配置验证结果:")
        print("="*50)
        
        for result in self.validation_results:
            status = "✅ 通过" if result["passed"] else "❌ 失败"
            print(f"{result['module']}: {status}")
        
        print("\n总体结果:", "✅ 所有模块验证通过" if all_passed else "❌ 部分模块验证失败")
        
        return all_passed

def main():
    # 获取Synapse代码根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    synapse_root = os.path.dirname(script_dir)
    
    print(f"Synapse根目录: {synapse_root}")
    print(f"当前工作目录: {os.getcwd()}")
    print()
    
    # 创建验证器并运行验证
    validator = FederationWellKnownValidator(synapse_root)
    success = validator.run_validation()
    
    # 根据验证结果设置退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()