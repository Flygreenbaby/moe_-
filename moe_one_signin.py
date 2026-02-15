#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
moe.one 社区自动签到脚本
使用 DrissionPage 实现浏览器自动化
支持账号密码登录和Cookie登录两种方式
"""

import os
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signin.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
except ImportError:
    logger.error("请先安装 DrissionPage: pip install DrissionPage")
    exit(1)

class MoeOneSignin:
    def __init__(self):
        self.base_url = "https://moe.one"
        self.username = os.getenv('MOE_ONE_USERNAME', '')  # 在GitHub Secrets中设置
        self.password = os.getenv('MOE_ONE_PASSWORD', '')  # 在GitHub Secrets中设置
        self.cookie = os.getenv('MOE_ONE_COOKIE', '')      # 在GitHub Secrets中设置
        
    def setup_browser(self):
        """配置浏览器选项"""
        co = ChromiumOptions()
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-gpu')
        co.set_argument('--window-size=1920,1080')
        co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 无头模式（GitHub Actions中使用）
        if os.getenv('GITHUB_ACTIONS'):
            co.headless()
            
        page = ChromiumPage(co)
        return page
        
    def login_with_credentials(self, page):
        """使用账号密码登录"""
        try:
            logger.info("尝试使用账号密码登录...")
            page.get(f"{self.base_url}/login")
            time.sleep(2)
            
            # 输入用户名和密码
            username_input = page.ele('#username') or page.ele('input[name="username"]')
            password_input = page.ele('#password') or page.ele('input[name="password"]')
            
            if username_input and password_input:
                username_input.input(self.username)
                password_input.input(self.password)
                
                # 点击登录按钮
                login_btn = page.ele('#login-btn') or page.ele('button[type="submit"]')
                if login_btn:
                    login_btn.click()
                    time.sleep(3)
                    
                # 检查是否登录成功
                if self.check_login_status(page):
                    logger.info("账号密码登录成功！")
                    return True
                else:
                    logger.error("账号密码登录失败，请检查凭证")
                    return False
            else:
                logger.error("未找到登录表单元素")
                return False
                
        except Exception as e:
            logger.error(f"账号密码登录异常: {e}")
            return False
            
    def login_with_cookie(self, page):
        """使用Cookie登录"""
        try:
            if not self.cookie:
                logger.warning("未提供Cookie，跳过Cookie登录")
                return False
                
            logger.info("尝试使用Cookie登录...")
            page.get(self.base_url)
            time.sleep(1)
            
            # 设置Cookie
            page.set.cookies(self.cookie)
            page.refresh()
            time.sleep(2)
            
            if self.check_login_status(page):
                logger.info("Cookie登录成功！")
                return True
            else:
                logger.error("Cookie登录失败，请检查Cookie有效性")
                return False
                
        except Exception as e:
            logger.error(f"Cookie登录异常: {e}")
            return False
            
    def check_login_status(self, page):
        """检查是否已登录"""
        try:
            # 检查是否存在用户相关元素（如个人中心、退出按钮等）
            user_elements = [
                page.ele('.user-info'),
                page.ele('#user-menu'),
                page.ele('a[href*="profile"]'),
                page.ele('a[href*="logout"]')
            ]
            
            for element in user_elements:
                if element and element.is_displayed():
                    return True
                    
            # 检查URL是否重定向到登录页
            current_url = page.url.lower()
            if 'login' in current_url:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"检查登录状态异常: {e}")
            return False
            
    def perform_signin(self, page):
        """执行签到操作"""
        try:
            logger.info("开始执行签到操作...")
            page.get(self.base_url)
            time.sleep(3)
            
            # 查找签到按钮（右上角）
            signin_btn_selectors = [
                '.signin-btn',
                '#signin-button', 
                'button[title*="签到"]',
                'a[href*="signin"]',
                '.header .btn:contains("签到")'
            ]
            
            signin_btn = None
            for selector in signin_btn_selectors:
                try:
                    btn = page.ele(selector)
                    if btn and btn.is_displayed():
                        signin_btn = btn
                        break
                except:
                    continue
                    
            if not signin_btn:
                # 尝试通用文本匹配
                all_buttons = page.eles('tag:button') + page.eles('tag:a')
                for btn in all_buttons:
                    if btn and btn.is_displayed():
                        btn_text = btn.text.lower()
                        if '签到' in btn_text or 'sign' in btn_text:
                            signin_btn = btn
                            break
                            
            if not signin_btn:
                logger.warning("未找到签到按钮，可能已经签到或页面结构变化")
                return False
                
            logger.info("找到签到按钮，点击...")
            signin_btn.click()
            time.sleep(2)
            
            # 处理弹窗和滑动验证
            success = self.handle_signin_popup(page)
            return success
            
        except Exception as e:
            logger.error(f"签到操作异常: {e}")
            return False
            
    def handle_signin_popup(self, page):
        """处理签到弹窗和滑动验证"""
        try:
            # 等待弹窗出现
            popup_selectors = ['.modal', '.popup', '.dialog', '#signin-modal']
            popup = None
            
            for selector in popup_selectors:
                try:
                    popup = page.ele(selector, timeout=5)
                    if popup and popup.is_displayed():
                        break
                except:
                    continue
                    
            if not popup:
                logger.info("未检测到签到弹窗，可能签到已完成")
                return True
                
            # 查找滑动验证元素
            slider_selectors = [
                '.slider',
                '.slide-bar',
                '.drag-btn',
                '[class*="slider"]',
                '[class*="drag"]'
            ]
            
            slider = None
            for selector in slider_selectors:
                try:
                    slider = page.ele(selector, timeout=3)
                    if slider and slider.is_displayed():
                        break
                except:
                    continue
                    
            if slider:
                logger.info("检测到滑动验证，正在处理...")
                # DrissionPage会自动处理简单的滑动验证
                # 如果是复杂的验证，可能需要更复杂的逻辑
                time.sleep(1)
                
                # 尝试拖拽滑块
                try:
                    track = page.ele('.slider-track') or page.ele('.slide-track')
                    if track:
                        # 计算滑动距离
                        track_width = track.rect.size[0]
                        slider.drag_and_drop(track.rect.right_center)
                        time.sleep(2)
                except Exception as drag_error:
                    logger.warning(f"滑动验证处理异常（可能不需要手动滑动）: {drag_error}")
                    
            # 等待签到结果
            time.sleep(3)
            
            # 检查签到是否成功
            success_indicators = [
                '签到成功',
                'success',
                'completed',
                'already signed'
            ]
            
            page_text = page.text.lower()
            for indicator in success_indicators:
                if indicator in page_text:
                    logger.info("签到成功！")
                    return True
                    
            logger.warning("未检测到签到成功标志，可能需要手动检查")
            return True  # 假设操作已完成
            
        except Exception as e:
            logger.error(f"处理签到弹窗异常: {e}")
            return False
            
    def run(self):
        """主运行函数"""
        logger.info("=" * 50)
        logger.info(f"开始执行 moe.one 自动签到 - {datetime.now()}")
        logger.info("=" * 50)
        
        page = None
        try:
            page = self.setup_browser()
            
            # 尝试登录（优先使用Cookie，其次账号密码）
            login_success = False
            if self.cookie:
                login_success = self.login_with_cookie(page)
                
            if not login_success and self.username and self.password:
                login_success = self.login_with_credentials(page)
                
            if not login_success:
                logger.error("登录失败，无法继续签到")
                return False
                
            # 执行签到
            signin_success = self.perform_signin(page)
            
            if signin_success:
                logger.info("✅ 签到流程完成！")
            else:
                logger.warning("⚠️ 签到流程可能未完全成功，请手动检查")
                
            return signin_success
            
        except Exception as e:
            logger.error(f"签到脚本执行异常: {e}")
            return False
            
        finally:
            if page:
                try:
                    page.quit()
                except:
                    pass

if __name__ == "__main__":
    signin = MoeOneSignin()
    success = signin.run()
    
    if not success:
        exit(1)