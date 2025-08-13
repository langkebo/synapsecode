#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Matrix Synapse用户注册、认证和房间管理功能
"""

import json
import requests
import time
import sys
from typing import Dict, Any, Optional

class MatrixAPITester:
    def __init__(self, base_url: str = "http://localhost:8008"):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.device_id: Optional[str] = None
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None, auth_required: bool = False) -> Dict[str, Any]:
        """发送HTTP请求到Matrix API"""
        url = f"{self.base_url}/_matrix/client/r0{endpoint}"
        
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
            
        if auth_required and self.access_token:
            request_headers["Authorization"] = f"Bearer {self.access_token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=request_headers)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=request_headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=request_headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": 200 <= response.status_code < 300
            }
        except requests.exceptions.RequestException as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
        except json.JSONDecodeError:
            return {
                "status_code": response.status_code,
                "data": {"error": "Invalid JSON response"},
                "success": False
            }
    
    def test_server_availability(self) -> bool:
        """测试服务器是否可用"""
        print("🔍 测试服务器可用性...")
        result = self._make_request("GET", "/versions")
        
        if result["success"]:
            print(f"✅ 服务器可用，支持的版本: {result['data'].get('versions', [])}")
            return True
        else:
            print(f"❌ 服务器不可用: {result['data']}")
            return False
    
    def test_user_registration(self, username: str = "testuser", password: str = "testpass123") -> bool:
        """测试用户注册功能"""
        print(f"📝 测试用户注册 (用户名: {username})...")
        
        registration_data = {
            "username": username,
            "password": password,
            "auth": {"type": "m.login.dummy"}
        }
        
        result = self._make_request("POST", "/register", registration_data)
        
        if result["success"]:
            self.user_id = result["data"].get("user_id")
            self.access_token = result["data"].get("access_token")
            self.device_id = result["data"].get("device_id")
            print(f"✅ 用户注册成功: {self.user_id}")
            return True
        else:
            error_code = result["data"].get("errcode", "unknown")
            if error_code == "M_USER_IN_USE":
                print(f"⚠️  用户已存在，尝试登录...")
                return self.test_user_login(username, password)
            else:
                print(f"❌ 用户注册失败: {result['data']}")
                return False
    
    def test_user_login(self, username: str = "testuser", password: str = "testpass123") -> bool:
        """测试用户登录功能"""
        print(f"🔐 测试用户登录 (用户名: {username})...")
        
        login_data = {
            "type": "m.login.password",
            "user": username,
            "password": password
        }
        
        result = self._make_request("POST", "/login", login_data)
        
        if result["success"]:
            self.user_id = result["data"].get("user_id")
            self.access_token = result["data"].get("access_token")
            self.device_id = result["data"].get("device_id")
            print(f"✅ 用户登录成功: {self.user_id}")
            return True
        else:
            print(f"❌ 用户登录失败: {result['data']}")
            return False
    
    def test_room_creation(self, room_name: str = "测试房间") -> Optional[str]:
        """测试房间创建功能"""
        print(f"🏠 测试房间创建 (房间名: {room_name})...")
        
        if not self.access_token:
            print("❌ 需要先登录才能创建房间")
            return None
            
        room_data = {
            "name": room_name,
            "topic": "这是一个测试房间",
            "preset": "private_chat"
        }
        
        result = self._make_request("POST", "/createRoom", room_data, auth_required=True)
        
        if result["success"]:
            room_id = result["data"].get("room_id")
            print(f"✅ 房间创建成功: {room_id}")
            return room_id
        else:
            print(f"❌ 房间创建失败: {result['data']}")
            return None
    
    def test_room_join(self, room_id: str) -> bool:
        """测试加入房间功能"""
        print(f"🚪 测试加入房间: {room_id}...")
        
        if not self.access_token:
            print("❌ 需要先登录才能加入房间")
            return False
            
        result = self._make_request("POST", f"/rooms/{room_id}/join", {}, auth_required=True)
        
        if result["success"]:
            print(f"✅ 成功加入房间: {room_id}")
            return True
        else:
            print(f"❌ 加入房间失败: {result['data']}")
            return False
    
    def test_room_state(self, room_id: str) -> bool:
        """测试获取房间状态"""
        print(f"📊 测试获取房间状态: {room_id}...")
        
        if not self.access_token:
            print("❌ 需要先登录才能获取房间状态")
            return False
            
        result = self._make_request("GET", f"/rooms/{room_id}/state", auth_required=True)
        
        if result["success"]:
            state_events = result["data"]
            print(f"✅ 成功获取房间状态，包含 {len(state_events)} 个状态事件")
            return True
        else:
            print(f"❌ 获取房间状态失败: {result['data']}")
            return False
    
    def test_send_message(self, room_id: str, message: str = "Hello, Matrix!") -> bool:
        """测试发送消息功能"""
        print(f"💬 测试发送消息到房间: {room_id}...")
        
        if not self.access_token:
            print("❌ 需要先登录才能发送消息")
            return False
            
        message_data = {
            "msgtype": "m.text",
            "body": message
        }
        
        # 使用当前时间戳作为事务ID
        txn_id = str(int(time.time() * 1000))
        
        result = self._make_request(
            "PUT", 
            f"/rooms/{room_id}/send/m.room.message/{txn_id}", 
            message_data, 
            auth_required=True
        )
        
        if result["success"]:
            event_id = result["data"].get("event_id")
            print(f"✅ 消息发送成功: {event_id}")
            return True
        else:
            print(f"❌ 消息发送失败: {result['data']}")
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🚀 开始Matrix Synapse功能测试\n")
        
        # 测试服务器可用性
        if not self.test_server_availability():
            return False
        print()
        
        # 测试用户注册/登录
        if not self.test_user_registration():
            return False
        print()
        
        # 测试房间创建
        room_id = self.test_room_creation()
        if not room_id:
            return False
        print()
        
        # 测试房间状态获取
        if not self.test_room_state(room_id):
            return False
        print()
        
        # 测试发送消息
        if not self.test_send_message(room_id):
            return False
        print()
        
        print("🎉 所有测试通过！")
        return True

def main():
    """主函数"""
    # 检查是否提供了服务器URL
    base_url = "http://localhost:8008"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Matrix服务器URL: {base_url}")
    
    tester = MatrixAPITester(base_url)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()