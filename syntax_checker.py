#!/usr/bin/env python3
"""
Python语法错误检查工具

这个脚本会检查项目中所有Python文件的真正语法错误。
"""

import ast
import os
import sys
from typing import List, Tuple, Dict


class AccurateSyntaxChecker:
    """精确的Python语法检查器"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self.errors = []
        
    def find_python_files(self) -> List[str]:
        """查找所有Python文件"""
        python_files = []
        for root, dirs, files in os.walk(self.root_dir):
            # 跳过隐藏目录和常见的忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files
    
    def check_syntax(self, file_path: str) -> Tuple[bool, str]:
        """检查单个文件的语法"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用AST解析检查语法
            ast.parse(content, filename=file_path)
            return True, ""
        except SyntaxError as e:
            error_msg = f"语法错误: {e.msg}"
            if e.lineno:
                error_msg += f" (行 {e.lineno}"
                if e.offset:
                    error_msg += f", 列 {e.offset}"
                error_msg += ")"
            return False, error_msg
        except Exception as e:
            return False, f"解析错误: {str(e)}"
    
    def check_common_issues(self, file_path: str) -> List[str]:
        """检查常见的代码问题"""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # 首先确保文件语法正确
            try:
                ast.parse(content, filename=file_path)
            except SyntaxError:
                # 如果有语法错误，不进行其他检查
                return issues
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                
                # 检查明显的语法问题
                if stripped.endswith('if') or stripped.endswith('elif') or stripped.endswith('else'):
                    issues.append(f"行 {i}: 可能缺少冒号: {stripped}")
                
                # 检查缩进问题（混合制表符和空格）
                if line and not line.lstrip():
                    continue  # 空行跳过
                    
                leading_whitespace = line[:len(line) - len(line.lstrip())]
                if '\t' in leading_whitespace and ' ' in leading_whitespace:
                    issues.append(f"行 {i}: 混合使用制表符和空格进行缩进")
                        
        except Exception as e:
            issues.append(f"检查文件时出错: {str(e)}")
            
        return issues
    
    def run_checks(self) -> Dict[str, any]:
        """运行所有检查"""
        print("🔍 开始检查Python语法错误...\n")
        
        python_files = self.find_python_files()
        print(f"找到 {len(python_files)} 个Python文件\n")
        
        syntax_errors = []
        other_issues = []
        checked_files = 0
        
        for file_path in python_files:
            checked_files += 1
            if checked_files % 10 == 0:
                print(f"已检查 {checked_files}/{len(python_files)} 个文件...")
            
            # 语法检查
            is_valid, error_msg = self.check_syntax(file_path)
            if not is_valid:
                syntax_errors.append((file_path, error_msg))
                print(f"❌ {file_path}: {error_msg}")
                continue
            
            # 其他问题检查
            issues = self.check_common_issues(file_path)
            if issues:
                other_issues.extend([(file_path, issue) for issue in issues])
                for issue in issues:
                    print(f"⚠️  {file_path}: {issue}")
        
        print("\n" + "="*50)
        print("检查结果汇总:")
        print(f"检查文件总数: {len(python_files)}")
        print(f"语法错误: {len(syntax_errors)} 个")
        print(f"其他问题: {len(other_issues)} 个")
        
        if syntax_errors:
            print("\n❌ 语法错误详情:")
            for file_path, error in syntax_errors:
                print(f"  {file_path}: {error}")
        
        if other_issues:
            print("\n⚠️  其他问题详情:")
            for file_path, issue in other_issues:
                print(f"  {file_path}: {issue}")
        
        total_issues = len(syntax_errors) + len(other_issues)
        if total_issues == 0:
            print("\n🎉 所有检查通过，没有发现语法错误！")
        else:
            print(f"\n⚠️  总共发现 {total_issues} 个问题")
            if len(syntax_errors) > 0:
                print("❗ 请优先修复语法错误")
        
        return {
            "syntax_errors": syntax_errors,
            "other_issues": other_issues,
            "total_files": len(python_files),
            "total_issues": total_issues
        }


def main():
    """主函数"""
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    checker = AccurateSyntaxChecker(root_dir)
    results = checker.run_checks()
    
    # 只有语法错误才返回非零退出码
    sys.exit(0 if len(results["syntax_errors"]) == 0 else 1)


if __name__ == "__main__":
    main()