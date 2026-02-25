#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# new Env('🛠️ 雨云签到依赖修复');
# cron: 0 0 1 1 *

import subprocess
import sys

def main():
    print("="*50)
    print("🚀 开始执行：正在进行底层依赖全自动修复与安装...")
    print("="*50)
    
    print("\n[1/2] 正在向底层系统安装原生组件...")
    cmd1 = 'apk update && apk add --no-cache python3 py3-pip py3-opencv py3-numpy chromium chromium-chromedriver'
    result1 = subprocess.run(cmd1, shell=True)
    
    if result1.returncode != 0:
        print("❌ 系统组件安装失败，请检查网络是否正常！")
        sys.exit(1)

    print("\n[2/2] 正在为底层Python补充扩展库...")
    cmd2 = '/usr/bin/python3 -m pip install -q selenium requests --break-system-packages'
    result2 = subprocess.run(cmd2, shell=True)
    
    if result2.returncode != 0:
        print("❌ Python扩展库安装失败！")
        sys.exit(1)

    print("\n" + "="*50)
    print("✅ 所有依赖环境已安装！")
    print("💡 现在你可以去设置定时任务，并运行主签到脚本了。")
    print("="*50)

if __name__ == "__main__":
    main()