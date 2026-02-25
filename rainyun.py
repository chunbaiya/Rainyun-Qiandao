#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# new Env('🌧️ 雨云全自动签到');
# cron: 30 8 * * *

import os
import sys

# --------- 核心环境隔离修复 (解决 Numpy/OpenCV 版本冲突) ---------
# 强制让脚本使用安装了 OpenCV 的底层系统 Python 运行
if sys.executable != '/usr/bin/python3' and os.path.exists('/usr/bin/python3'):
    os.execl('/usr/bin/python3', '/usr/bin/python3', *sys.argv)

# 加入项目根目录，确保能找到通知文件和依赖
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import random
import re
import time
import cv2
import requests
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import ICR

# --------- 尝试接入青龙通知模块 ---------
try:
    import notify
except ImportError:
    notify = None

def send_notification(title, content):
    logger.info(f"【推送通知】{title}")
    if notify:
        try:
            notify.send(title, content)
            logger.info("✅ 消息推送任务已提交给青龙系统！")
            logger.info("💡 PS：如果你手机没有收到上面的通知消息，说明你还没配置推送变量。")
            logger.info("   解决方法：去青龙面板左侧的【环境变量】里，添加你的推送密钥。")
            logger.info("   例如：添加变量名 QYWX_KEY (企业微信) 或 PUSH_PLUS_TOKEN (PushPlus) 等。")
            logger.info("   (配置好后，青龙里所有脚本的通知就都能推送了!)")
        except Exception as e:
            logger.error(f"⚠️ 通知推送执行失败: {e}")
    else:
        logger.warning("⚠️ 未找到青龙 notify 模块，跳过消息推送。")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --------- 核心 Selenium 配置 (青龙定制版) ---------
def init_selenium() -> WebDriver:
    ops = Options()
    ops.add_argument("--no-sandbox")
    ops.add_argument("--headless")
    ops.add_argument("--disable-gpu")
    ops.add_argument("--disable-dev-shm-usage") # 解决Docker容器内存崩溃
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=ops)

def download_image(url, filename):
    os.makedirs("temp", exist_ok=True)
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        path = os.path.join("temp", filename)
        with open(path, "wb") as f:
            f.write(response.content)
        return True
    return False

def get_url_from_style(style):
    return re.search(r'url\(["\']?(.*?)["\']?\)', style).group(1)

def get_width_from_style(style):
    return re.search(r'width:\s*([\d.]+)px', style).group(1)

def get_height_from_style(style):
    return re.search(r'height:\s*([\d.]+)px', style).group(1)

def download_captcha_img(wait):
    if os.path.exists("temp"):
        for filename in os.listdir("temp"):
            file_path = os.path.join("temp", filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
    img1_url = get_url_from_style(slideBg.get_attribute("style"))
    logger.info("开始下载验证码图片(1)...")
    download_image(img1_url, "captcha.jpg")
    sprite = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="instruction"]/div/img')))
    img2_url = sprite.get_attribute("src")
    logger.info("开始下载验证码图片(2)...")
    download_image(img2_url, "sprite.jpg")

# 引入 start_time 机制，完美防止验证码死循环
def process_captcha(driver, wait, start_time):
    if time.time() - start_time > 180:
        logger.error("❌ 严重超时：验证码识别超过3分钟，疑似遇到异常死循环，已强制中断跳过！")
        return False

    try:
        download_captcha_img(wait)
        logger.info("开始识别验证码...")
        captcha = cv2.imread("temp/captcha.jpg")
        result = ICR.main("temp/captcha.jpg", "temp/sprite.jpg")
        for info in result:
            rect = info['bg_rect']
            x, y = int(rect[0] + (rect[2] / 2)), int(rect[1] + (rect[3] / 2))
            logger.info(f"图案 {info['sprite_idx'] + 1} 位于 ({x}, {y})")
            slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
            style = slideBg.get_attribute("style")
            width_raw, height_raw = captcha.shape[1], captcha.shape[0]
            width, height = float(get_width_from_style(style)), float(get_height_from_style(style))
            x_offset, y_offset = float(-width / 2), float(-height / 2)
            final_x, final_y = int(x_offset + x / width_raw * width), int(y_offset + y / height_raw * height)
            ActionChains(driver).move_to_element_with_offset(slideBg, final_x, final_y).click().perform()
        
        confirm = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tcStatus"]/div[2]/div[2]/div/div')))
        logger.info("提交验证码...")
        confirm.click()
        time.sleep(5)
        
        result = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="tcOperation"]')))
        if result.get_attribute("class") == 'tc-opera pointer show-success':
            logger.info("✅ 验证码通过！")
            return True
        else:
            logger.warning("⚠️ 验证码未通过，正在重试...")
            reload = driver.find_element(By.XPATH, '//*[@id="reload"]')
            time.sleep(5)
            reload.click()
            time.sleep(5)
            return process_captcha(driver, wait, start_time)
            
    except TimeoutException:
        logger.error("❌ 获取验证码图片失败！")
        return False
    except Exception as e:
        logger.error(f"❌ 验证码处理异常: {e}")
        return False

# --------- 单账号签到流程 ---------
def run_sign_in(username, password):
    logger.info("初始化 Selenium 驱动...")
    driver = init_selenium()
    status_msg = ""
    try:
        if os.path.exists("stealth.min.js"):
            with open("stealth.min.js", mode="r") as f:
                js = f.read()
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": js})
            
        logger.info("发起登录请求...")
        driver.get("https://app.rainyun.com/auth/login")
        wait = WebDriverWait(driver, 15)
        
        user_input = wait.until(EC.visibility_of_element_located((By.NAME, 'login-field')))
        pwd_input = wait.until(EC.visibility_of_element_located((By.NAME, 'login-password')))
        login_btn = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div[1]/div[1]/div/div[2]/fade/div/div/span/form/button')))
        
        user_input.send_keys(username)
        pwd_input.send_keys(password)
        login_btn.click()
        
        try:
            wait.until(EC.visibility_of_element_located((By.ID, 'tcaptcha_iframe_dy')))
            logger.warning("触发登录验证码！")
            driver.switch_to.frame("tcaptcha_iframe_dy")
            if not process_captcha(driver, wait, time.time()):
                return f"账号 {username}: 登录验证码失败 ❌"
        except TimeoutException:
            logger.info("免验证码，直接尝试登录...")
            
        time.sleep(5)
        driver.switch_to.default_content()
        
        if driver.current_url == "https://app.rainyun.com/dashboard":
            logger.info("✅ 登录成功，转到赚取积分页...")
            driver.get("https://app.rainyun.com/account/reward/earn")
            driver.implicitly_wait(5)
            earn = driver.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[2]/div/div/div/div[1]/div/div[1]/div/div[1]/div/span[2]/a')
            earn.click()
            
            logger.info("处理签到验证码...")
            driver.switch_to.frame("tcaptcha_iframe_dy")
            if not process_captcha(driver, wait, time.time()):
                return f"账号 {username}: 签到验证码失败 ❌"
                
            driver.switch_to.default_content()
            driver.implicitly_wait(5)
            points_raw = driver.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[1]/div[1]/div/p/div/h3').get_attribute("textContent")
            current_points = int(''.join(re.findall(r'\d+', points_raw)))
            
            # --- 补回积分转人民币换算逻辑 ---
            money = current_points / 2000
            logger.info(f"🎉 任务执行成功！当前剩余积分: {current_points} | 约合: {money:.2f} 元")
            status_msg = f"账号 {username}: 签到成功 ✅ (当前积分:{current_points} | 约合:{money:.2f}元)"
        else:
            logger.error("❌ 登录失败，请检查账号密码。")
            status_msg = f"账号 {username}: 登录失败 ❌ (检查密码)"
            
    except Exception as e:
        logger.error(f"❌ 流程异常: {e}")
        status_msg = f"账号 {username}: 运行时异常 ❌"
    finally:
        # 无论成功失败，确保彻底关闭浏览器，防止内存泄漏
        try:
            driver.quit()
        except:
            pass
        logger.info("浏览器驱动已释放。")
        
    return status_msg

# --------- 主入口 ---------
if __name__ == "__main__":
    ver = "2.3 雨云签到工具青龙版"
    logger.info("=" * 60)
    logger.info(f"🌧️ 雨云签到工具 v{ver} ~")
    logger.info("Github发布页: https://github.com/SerendipityR-2022/Rainyun-Qiandao")
    logger.info("-------------当前版本为二开版本，原作者信息在上面-------------")
    logger.info("二开作者Q:16745603          交流讨论群:851107003")
    logger.info("本项目仅作为学习参考，请勿用于其他用途!")
    logger.info("=" * 60)

    env_str = os.environ.get("RAINYUN_USERS")
    if not env_str:
        logger.error("❌ 未找到环境变量 RAINYUN_USERS，请在青龙面板配置。")
        logger.info("💡 配置变量：账号,密码  多账号可换行配置！")
        sys.exit(1)
    
    accounts = []
    for line in env_str.replace('&', '\n').split('\n'):
        if not line.strip(): continue
        parts = line.split(',')
        if len(parts) >= 2:
            accounts.append({"username": parts[0].strip(), "password": parts[1].strip()})

    logger.info(f"\n🚀 准备就绪，开始执行 {len(accounts)} 个账号的自动签到...")
    notify_msg = []

    for idx, account in enumerate(accounts, 1):
        username = account['username']
        logger.info("-" * 40)
        logger.info(f"▶️ [ {idx} / {len(accounts)} ] 正在执行账号: {username}")
        
        msg = run_sign_in(username, account['password'])
        notify_msg.append(msg)
        
        if idx < len(accounts):
            logger.info("⏳ 延时冷却 5 秒后继续下一个账号...")
            time.sleep(5)

    logger.info("=" * 60)
    logger.info("🎉 所有账号处理流程结束！")
    send_notification("雨云签到执行结果", "\n".join(notify_msg))
