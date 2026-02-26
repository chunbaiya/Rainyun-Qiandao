#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# new Env('🌧️ 雨云签到依赖修复');
# cron: 0 0 1 1 *

import subprocess
import sys
import shutil

def main():
    print("="*50)
    print("🚀 开始执行：正在进行底层依赖全自动修复与安装...")
    print("="*50)
    
    print("\n[1/2] 正在检测系统环境...")
    
    # 智能判断当前系统类型并执行对应的底层包管理器命令
    if shutil.which("apk"):
        print("📦 检测到系统为 Alpine，正在使用 apk 安装...(可能需要几分钟)")
        cmd1 = 'apk update && apk add --no-cache python3 py3-pip py3-opencv py3-numpy chromium chromium-chromedriver'
    elif shutil.which("apt-get"):
        print("📦 检测到系统为 Debian/Ubuntu，正在使用 apt-get 安装 (可能需要几分钟)...")
        cmd1 = 'apt-get update && apt-get install -y python3 python3-pip python3-opencv python3-numpy chromium chromium-driver'
    elif shutil.which("dnf"):
        print("📦 检测到系统为 CentOS 8+/Fedora/Rocky，正在使用 dnf 安装...(可能需要几分钟)")
        cmd1 = 'dnf install -y epel-release && dnf install -y python3 python3-pip chromium chromedriver'
    elif shutil.which("yum"):
        print("📦 检测到系统为 CentOS 7/RHEL，正在使用 yum 安装...(可能需要几分钟)")
        cmd1 = 'yum install -y epel-release && yum install -y python3 python3-pip chromium chromedriver'
    else:
        print("❌ 无法识别当前系统的包管理器 (未知的魔改系统)，安装中止！")
        sys.exit(1)

    result1 = subprocess.run(cmd1, shell=True)
    
    if result1.returncode != 0:
        print("❌ 系统组件安装失败，请检查网络或软件源是否正常！")
        sys.exit(1)

    print("\n[2/2] 正在为底层Python补充扩展库...")
    # 补充安装必要的 Python 依赖（兼容各平台不同的预装情况）
    cmd2 = '/usr/bin/python3 -m pip install -q selenium requests opencv-python-headless numpy --break-system-packages'
    result2 = subprocess.run(cmd2, shell=True)
    
    if result2.returncode != 0:
        print("⚠️ 尝试备用 pip 安装方案...")
        cmd2_fallback = '/usr/bin/python3 -m pip install -q selenium requests opencv-python-headless numpy'
        result2_fallback = subprocess.run(cmd2_fallback, shell=True)
        if result2_fallback.returncode != 0:
            print("❌ Python扩展库安装失败！")
            sys.exit(1)

    print("\n" + "="*50)
    print("✅ 所有依赖环境已安装！")
    print("💡 现在你可以去设置定时任务，并运行主签到脚本了。")
    print("="*50)

if __name__ == "__main__":
    main()