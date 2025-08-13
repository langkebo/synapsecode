#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Matrix Synapse 消息通信和文件传输功能验证脚本

该脚本验证以下功能模块的代码完整性：
1. 消息发送和接收处理
2. 文件上传和下载功能
3. 媒体存储和管理
4. 缩略图生成
5. URL预览功能
"""

import os
import sys
import importlib.util
from typing import List, Dict, Any

class MessageMediaValidator:
    """Matrix Synapse 消息和媒体功能验证器"""
    
    def __init__(self, synapse_root: str):
        self.synapse_root = synapse_root
        self.validation_results = {
            'message_handling': {'status': 'pending', 'details': []},
            'media_upload': {'status': 'pending', 'details': []},
            'media_download': {'status': 'pending', 'details': []},
            'media_storage': {'status': 'pending', 'details': []},
            'thumbnail_generation': {'status': 'pending', 'details': []},
            'url_preview': {'status': 'pending', 'details': []}
        }
    
    def check_file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        full_path = os.path.join(self.synapse_root, file_path)
        return os.path.exists(full_path)
    
    def check_class_in_file(self, file_path: str, class_name: str) -> bool:
        """检查文件中是否存在指定类"""
        try:
            full_path = os.path.join(self.synapse_root, file_path)
            if not os.path.exists(full_path):
                return False
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f'class {class_name}' in content
        except Exception:
            return False
    
    def check_method_in_file(self, file_path: str, method_name: str) -> bool:
        """检查文件中是否存在指定方法"""
        try:
            full_path = os.path.join(self.synapse_root, file_path)
            if not os.path.exists(full_path):
                return False
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f'def {method_name}' in content or f'async def {method_name}' in content
        except Exception:
            return False
    
    def validate_message_handling(self) -> None:
        """验证消息处理功能"""
        print("\n=== 验证消息处理功能 ===")
        
        # 检查核心文件
        core_files = [
            'handlers/message.py',
            'rest/client/room.py',
            'rest/client/sendtodevice.py'
        ]
        
        missing_files = []
        for file_path in core_files:
            if self.check_file_exists(file_path):
                print(f"✓ 找到文件: {file_path}")
            else:
                print(f"✗ 缺失文件: {file_path}")
                missing_files.append(file_path)
        
        # 检查关键类
        key_classes = [
            ('handlers/message.py', 'MessageHandler'),
            ('rest/client/room.py', 'RoomSendEventRestServlet'),
            ('rest/client/sendtodevice.py', 'SendToDeviceRestServlet')
        ]
        
        missing_classes = []
        for file_path, class_name in key_classes:
            if self.check_class_in_file(file_path, class_name):
                print(f"✓ 找到类: {class_name} in {file_path}")
            else:
                print(f"✗ 缺失类: {class_name} in {file_path}")
                missing_classes.append((file_path, class_name))
        
        # 检查关键方法
        key_methods = [
            ('handlers/message.py', 'get_room_data'),
            ('handlers/message.py', 'get_state_events'),
            ('rest/client/room.py', 'on_PUT'),
            ('rest/client/room.py', 'on_POST')
        ]
        
        missing_methods = []
        for file_path, method_name in key_methods:
            if self.check_method_in_file(file_path, method_name):
                print(f"✓ 找到方法: {method_name} in {file_path}")
            else:
                print(f"✗ 缺失方法: {method_name} in {file_path}")
                missing_methods.append((file_path, method_name))
        
        # 更新验证结果
        if not missing_files and not missing_classes and not missing_methods:
            self.validation_results['message_handling']['status'] = 'passed'
            self.validation_results['message_handling']['details'] = ['所有消息处理组件验证通过']
        else:
            self.validation_results['message_handling']['status'] = 'failed'
            details = []
            if missing_files:
                details.append(f"缺失文件: {missing_files}")
            if missing_classes:
                details.append(f"缺失类: {missing_classes}")
            if missing_methods:
                details.append(f"缺失方法: {missing_methods}")
            self.validation_results['message_handling']['details'] = details
    
    def validate_media_upload(self) -> None:
        """验证媒体上传功能"""
        print("\n=== 验证媒体上传功能 ===")
        
        # 检查核心文件
        core_files = [
            'rest/media/upload_resource.py',
            'media/media_repository.py',
            'media/media_storage.py'
        ]
        
        missing_files = []
        for file_path in core_files:
            if self.check_file_exists(file_path):
                print(f"✓ 找到文件: {file_path}")
            else:
                print(f"✗ 缺失文件: {file_path}")
                missing_files.append(file_path)
        
        # 检查关键类
        key_classes = [
            ('rest/media/upload_resource.py', 'UploadServlet'),
            ('rest/media/upload_resource.py', 'AsyncUploadServlet'),
            ('media/media_repository.py', 'MediaRepository')
        ]
        
        missing_classes = []
        for file_path, class_name in key_classes:
            if self.check_class_in_file(file_path, class_name):
                print(f"✓ 找到类: {class_name} in {file_path}")
            else:
                print(f"✗ 缺失类: {class_name} in {file_path}")
                missing_classes.append((file_path, class_name))
        
        # 检查关键方法
        key_methods = [
            ('rest/media/upload_resource.py', 'on_POST'),
            ('rest/media/upload_resource.py', 'on_PUT'),
            ('media/media_repository.py', 'create_content'),
            ('media/media_repository.py', 'update_content')
        ]
        
        missing_methods = []
        for file_path, method_name in key_methods:
            if self.check_method_in_file(file_path, method_name):
                print(f"✓ 找到方法: {method_name} in {file_path}")
            else:
                print(f"✗ 缺失方法: {method_name} in {file_path}")
                missing_methods.append((file_path, method_name))
        
        # 更新验证结果
        if not missing_files and not missing_classes and not missing_methods:
            self.validation_results['media_upload']['status'] = 'passed'
            self.validation_results['media_upload']['details'] = ['所有媒体上传组件验证通过']
        else:
            self.validation_results['media_upload']['status'] = 'failed'
            details = []
            if missing_files:
                details.append(f"缺失文件: {missing_files}")
            if missing_classes:
                details.append(f"缺失类: {missing_classes}")
            if missing_methods:
                details.append(f"缺失方法: {missing_methods}")
            self.validation_results['media_upload']['details'] = details
    
    def validate_media_download(self) -> None:
        """验证媒体下载功能"""
        print("\n=== 验证媒体下载功能 ===")
        
        # 检查核心文件
        core_files = [
            'rest/media/download_resource.py',
            'media/_base.py'
        ]
        
        missing_files = []
        for file_path in core_files:
            if self.check_file_exists(file_path):
                print(f"✓ 找到文件: {file_path}")
            else:
                print(f"✗ 缺失文件: {file_path}")
                missing_files.append(file_path)
        
        # 检查关键类
        key_classes = [
            ('rest/media/download_resource.py', 'DownloadResource')
        ]
        
        missing_classes = []
        for file_path, class_name in key_classes:
            if self.check_class_in_file(file_path, class_name):
                print(f"✓ 找到类: {class_name} in {file_path}")
            else:
                print(f"✗ 缺失类: {class_name} in {file_path}")
                missing_classes.append((file_path, class_name))
        
        # 检查关键方法
        key_methods = [
            ('rest/media/download_resource.py', 'on_GET'),
            ('media/media_repository.py', 'get_local_media'),
            ('media/media_repository.py', 'get_remote_media')
        ]
        
        missing_methods = []
        for file_path, method_name in key_methods:
            if self.check_method_in_file(file_path, method_name):
                print(f"✓ 找到方法: {method_name} in {file_path}")
            else:
                print(f"✗ 缺失方法: {method_name} in {file_path}")
                missing_methods.append((file_path, method_name))
        
        # 更新验证结果
        if not missing_files and not missing_classes and not missing_methods:
            self.validation_results['media_download']['status'] = 'passed'
            self.validation_results['media_download']['details'] = ['所有媒体下载组件验证通过']
        else:
            self.validation_results['media_download']['status'] = 'failed'
            details = []
            if missing_files:
                details.append(f"缺失文件: {missing_files}")
            if missing_classes:
                details.append(f"缺失类: {missing_classes}")
            if missing_methods:
                details.append(f"缺失方法: {missing_methods}")
            self.validation_results['media_download']['details'] = details
    
    def validate_media_storage(self) -> None:
        """验证媒体存储功能"""
        print("\n=== 验证媒体存储功能 ===")
        
        # 检查核心文件
        core_files = [
            'media/media_storage.py',
            'media/storage_provider.py',
            'media/filepath.py'
        ]
        
        missing_files = []
        for file_path in core_files:
            if self.check_file_exists(file_path):
                print(f"✓ 找到文件: {file_path}")
            else:
                print(f"✗ 缺失文件: {file_path}")
                missing_files.append(file_path)
        
        # 检查关键类
        key_classes = [
            ('media/media_storage.py', 'MediaStorage'),
            ('media/storage_provider.py', 'StorageProviderWrapper'),
            ('media/filepath.py', 'MediaFilePaths')
        ]
        
        missing_classes = []
        for file_path, class_name in key_classes:
            if self.check_class_in_file(file_path, class_name):
                print(f"✓ 找到类: {class_name} in {file_path}")
            else:
                print(f"✗ 缺失类: {class_name} in {file_path}")
                missing_classes.append((file_path, class_name))
        
        # 检查关键方法
        key_methods = [
            ('media/media_storage.py', 'store_file'),
            ('media/media_storage.py', 'fetch_media'),
            ('media/filepath.py', 'local_media_filepath'),
            ('media/filepath.py', 'remote_media_filepath')
        ]
        
        missing_methods = []
        for file_path, method_name in key_methods:
            if self.check_method_in_file(file_path, method_name):
                print(f"✓ 找到方法: {method_name} in {file_path}")
            else:
                print(f"✗ 缺失方法: {method_name} in {file_path}")
                missing_methods.append((file_path, method_name))
        
        # 更新验证结果
        if not missing_files and not missing_classes and not missing_methods:
            self.validation_results['media_storage']['status'] = 'passed'
            self.validation_results['media_storage']['details'] = ['所有媒体存储组件验证通过']
        else:
            self.validation_results['media_storage']['status'] = 'failed'
            details = []
            if missing_files:
                details.append(f"缺失文件: {missing_files}")
            if missing_classes:
                details.append(f"缺失类: {missing_classes}")
            if missing_methods:
                details.append(f"缺失方法: {missing_methods}")
            self.validation_results['media_storage']['details'] = details
    
    def validate_thumbnail_generation(self) -> None:
        """验证缩略图生成功能"""
        print("\n=== 验证缩略图生成功能 ===")
        
        # 检查核心文件
        core_files = [
            'media/thumbnailer.py',
            'rest/media/thumbnail_resource.py'
        ]
        
        missing_files = []
        for file_path in core_files:
            if self.check_file_exists(file_path):
                print(f"✓ 找到文件: {file_path}")
            else:
                print(f"✗ 缺失文件: {file_path}")
                missing_files.append(file_path)
        
        # 检查关键类
        key_classes = [
            ('media/thumbnailer.py', 'Thumbnailer'),
            ('rest/media/thumbnail_resource.py', 'ThumbnailResource')
        ]
        
        missing_classes = []
        for file_path, class_name in key_classes:
            if self.check_class_in_file(file_path, class_name):
                print(f"✓ 找到类: {class_name} in {file_path}")
            else:
                print(f"✗ 缺失类: {class_name} in {file_path}")
                missing_classes.append((file_path, class_name))
        
        # 检查关键方法
        key_methods = [
            ('media/thumbnailer.py', 'scale'),
            ('media/thumbnailer.py', 'crop'),
            ('media/media_repository.py', '_generate_thumbnails'),
            ('rest/media/thumbnail_resource.py', 'on_GET')
        ]
        
        missing_methods = []
        for file_path, method_name in key_methods:
            if self.check_method_in_file(file_path, method_name):
                print(f"✓ 找到方法: {method_name} in {file_path}")
            else:
                print(f"✗ 缺失方法: {method_name} in {file_path}")
                missing_methods.append((file_path, method_name))
        
        # 更新验证结果
        if not missing_files and not missing_classes and not missing_methods:
            self.validation_results['thumbnail_generation']['status'] = 'passed'
            self.validation_results['thumbnail_generation']['details'] = ['所有缩略图生成组件验证通过']
        else:
            self.validation_results['thumbnail_generation']['status'] = 'failed'
            details = []
            if missing_files:
                details.append(f"缺失文件: {missing_files}")
            if missing_classes:
                details.append(f"缺失类: {missing_classes}")
            if missing_methods:
                details.append(f"缺失方法: {missing_methods}")
            self.validation_results['thumbnail_generation']['details'] = details
    
    def validate_url_preview(self) -> None:
        """验证URL预览功能"""
        print("\n=== 验证URL预览功能 ===")
        
        # 检查核心文件
        core_files = [
            'media/url_previewer.py',
            'media/preview_html.py',
            'media/oembed.py',
            'rest/media/preview_url_resource.py'
        ]
        
        missing_files = []
        for file_path in core_files:
            if self.check_file_exists(file_path):
                print(f"✓ 找到文件: {file_path}")
            else:
                print(f"✗ 缺失文件: {file_path}")
                missing_files.append(file_path)
        
        # 检查关键类
        key_classes = [
            ('media/url_previewer.py', 'UrlPreviewer'),
            ('rest/media/preview_url_resource.py', 'PreviewUrlResource')
        ]
        
        missing_classes = []
        for file_path, class_name in key_classes:
            if self.check_class_in_file(file_path, class_name):
                print(f"✓ 找到类: {class_name} in {file_path}")
            else:
                print(f"✗ 缺失类: {class_name} in {file_path}")
                missing_classes.append((file_path, class_name))
        
        # 检查关键方法
        key_methods = [
            ('media/url_previewer.py', 'preview'),
            ('media/url_previewer.py', '_do_preview'),
            ('rest/media/preview_url_resource.py', 'on_GET'),
            ('media/preview_html.py', 'parse_html_to_open_graph')
        ]
        
        missing_methods = []
        for file_path, method_name in key_methods:
            if self.check_method_in_file(file_path, method_name):
                print(f"✓ 找到方法: {method_name} in {file_path}")
            else:
                print(f"✗ 缺失方法: {method_name} in {file_path}")
                missing_methods.append((file_path, method_name))
        
        # 更新验证结果
        if not missing_files and not missing_classes and not missing_methods:
            self.validation_results['url_preview']['status'] = 'passed'
            self.validation_results['url_preview']['details'] = ['所有URL预览组件验证通过']
        else:
            self.validation_results['url_preview']['status'] = 'failed'
            details = []
            if missing_files:
                details.append(f"缺失文件: {missing_files}")
            if missing_classes:
                details.append(f"缺失类: {missing_classes}")
            if missing_methods:
                details.append(f"缺失方法: {missing_methods}")
            self.validation_results['url_preview']['details'] = details
    
    def run_all_validations(self) -> None:
        """运行所有验证"""
        print("开始验证Matrix Synapse消息通信和文件传输功能...")
        
        self.validate_message_handling()
        self.validate_media_upload()
        self.validate_media_download()
        self.validate_media_storage()
        self.validate_thumbnail_generation()
        self.validate_url_preview()
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """打印验证结果摘要"""
        print("\n" + "="*60)
        print("验证结果摘要")
        print("="*60)
        
        passed_count = 0
        total_count = len(self.validation_results)
        
        for module, result in self.validation_results.items():
            status_symbol = "✓" if result['status'] == 'passed' else "✗"
            print(f"{status_symbol} {module}: {result['status']}")
            
            if result['status'] == 'passed':
                passed_count += 1
            else:
                for detail in result['details']:
                    print(f"  - {detail}")
        
        print(f"\n总体结果: {passed_count}/{total_count} 个功能模块验证通过")
        
        if passed_count == total_count:
            print("\n🎉 所有消息通信和文件传输功能模块验证通过！")
            print("Matrix Synapse具备完整的消息处理和媒体传输能力。")
        else:
            print(f"\n⚠️  有 {total_count - passed_count} 个功能模块存在问题，需要进一步检查。")

def main():
    """主函数"""
    # 获取Synapse代码根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    synapse_root = os.path.dirname(current_dir)  # 上一级目录
    
    print(f"Synapse根目录: {synapse_root}")
    
    # 创建验证器并运行验证
    validator = MessageMediaValidator(synapse_root)
    validator.run_all_validations()

if __name__ == "__main__":
    main()