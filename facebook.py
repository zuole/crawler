#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on 2018.03.09
Finished on 2018.04.13
@author: Wang Yuntao
"""

import re
import time
import utils
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

"""
    function:
        __init__(self, _user_name=None, _password=None, _browser_type="Chrome", 
                            is_headless=False)          __init__
        sign_in(self)                                   Facebook登录
        make_post(self)                                 发布状态
        page_refresh(self, _refresh_times=0)            页面下拉刷新
        get_myself_info(self)                           获取当前登录账户的信息 user_name, user_id, homepage_url
        enter_homepage_self(self)                       进入当前账户的个人主页 (方便对用户好友和照片的获取)
        get_user_id(self, _user_homepage_url)           获取用户id
        get_friends_number(self)                        获取当前账户的好友个数
        get_friends_list(self, _friends_number=None)    获取当前账户的好友列表 (列表存储各好友的user_name, user_id, homepage_url)
        search_users(self, _keyword, user_number)       获取当前搜索条件下的用户列表 (列表存储各用户的user_name, homepage_url, location, user_id)
        
        get_photos_list(self)                           获取照片的href，方便对原图的链接，发表时间等进行获取
        get_photo_info(self, _photo_href)               获取照片的链接，发布时间，发布位置，尺寸与对应的文字说明
        get_photos_info_list(self, _photos_href_list)   批量获取照片的链接，发布时间，发布位置，尺寸与对应的文字说明
        download_photos_one(self, _homepage_url)        下载单个用户的图片
        download_photos_batch(self, _homepage_url_list) 批量下载多个用户的图片
         def params_modify(self, post_class_name, 
         bottom_xpath_search, bottom_xpath_other, 
         main_container_class_name,myself_id_class_name)用于对可变参数进行修改
         
    Note:
        实际使用中还需要根据Facebook当前的页面架构进行相应调整
"""


class Facebook:
    def __init__(self, _user_name=None, _password=None, _browser_type="Chrome", _is_headless=False, _speed_mode="Normal"):
        """
        构造函数
        :param _user_name: Facebook登录所需邮箱
        :param _password: Facebook登录对应的密码
        :param _browser_type: 浏览器类型 (Chrome | Firefox)
        :param _is_headless: 是否适用无头浏览器
        :param _speed_mode: 运行速度模式选择 (Extreme | Fast | Normal | Slow)
        """
        # the variables which are fixed
        self.url = "https://www.facebook.com/"                              # facebook页面url
        self.user_name = _user_name                                         # 帐户名
        self.password = _password                                           # 密码
        self.soup_type = "html.parse"                                       # beautifulsoup解析类型

        # some identifier
        self.browser_state = None                                           # 浏览器选择状态
        self.login_state = None                                             # 登录状态

        # the variable about the current login account
        self.homepage_url = None                                            # 当前登录账号的主页url
        self.friends_number = 0                                             # 当前登录账号的好友数量

        # some parameters of webdriver
        self.cookie = None                                                  # 当前登录账号的cookie
        self.session_id = None                                              # 会话id，方便在当前打开窗口继续运行
        self.executor_url = None                                            # 会话的命令执行器连接
        self.cookies = None                                                 # 用户cookies

        # the initialization of list
        self.user_info_friends = list()                                     # 好友信息列表 (user_name, user_id, homepage_url)
        self.user_info_search = list()                                      # 通过搜索得到的用户信息列表 (user_name, homepage_url)

        # the variables which are static
        self.clearfix_flag = "clearfix"                                     # 网页消除浮动标识
        self.user_cover_class_name = "cover"                                # 用户封面对应的class name
        self.bottom_class_name = "uiHeaderTitle"                            # 用于确定图片、视频下载时有无下拉到最底的class name
        self.bottom_xpath_search = \
            "//*[@id=\"browse_end_of_results_footer\"]/div/div"             # 用户搜索时对应的bottom标识
        self.bottom_xpath_other = \
            "//*[@id=\"timeline-medley\"]/div/div[2]/div[1]/div/div"        # 照片好友信息遍历时的bottom标识
        self.main_container_class_name = "homeSideNav"                      # 用户获取当前登录账户信息的class name
        self.myself_id_class_name = "data-nav-item-id"                      # 用户id对应的字段名
        self.friends_list_class_name = "uiProfileBlockContent"
        self.friends_number_id_name = "pagelet_timeline_medley_friends"     # 用于获取好友数量的id name
        self.homepage_url_postfix_1 = "?fref=pb&hc_location=friends_tab"    # 一类URL的后缀
        self.homepage_url_postfix_2 = "&fref=pb&hc_location=friends_tab"    # 二类URL的后缀
        self.browse_results_container = "//*[@id=\"BrowseResultsContainer\"]/div[1]"

        # the variables which may be variant regularly
        self.post_class_name = "_3jk"                                       # 状态发布所需class name

        # 用户搜索所需class name
        self.user_search_class_name = None
        self.user_name_class_name = None

        # the selection of browser
        if _browser_type == "Chrome":
            try:
                options = webdriver.ChromeOptions()
                if _is_headless is True:
                    options.set_headless()
                    options.add_argument("--disable - gpu")
                self.driver = webdriver.Chrome(options=options)
                self.browser_state = 1
            except AttributeError:
                self.browser_state = 0

        if _browser_type == "Firefox":
            try:
                options = webdriver.FirefoxOptions()
                if _is_headless is True:
                    options.set_headless()
                    options.add_argument("--disable - gpu")
                self.driver = webdriver.Firefox(options=options)
                self.browser_state = 1
            except AttributeError:
                self.browser_state = 0

        # the run speed mode selection
        self.timeout = utils.get_timeout(_speed_mode)

    def params_modify(self, post_class_name, bottom_xpath_search, bottom_xpath_other, main_container_class_name,
                      myself_id_class_name):
        self.post_class_name = post_class_name
        self.bottom_xpath_search = bottom_xpath_search
        self.bottom_xpath_other = bottom_xpath_other
        self.main_container_class_name = main_container_class_name
        self.myself_id_class_name = myself_id_class_name

    def sign_in(self):
        """
        facebook log in via webdriver
        :return: a status code —— True: Success, False: False
        Note:
            如果facebook账号登录成功，则当前页面的url为:https://www.facebook.com
            如果facebook账号登录失败，则当前页面的url为:https://www.facebook.com/login.php?login_attempt=1&lwv=100
        """
        self.driver.get(self.url)

        # username
        email_element = self.driver.find_element_by_id('email')
        email_element.clear()
        email_element.send_keys(self.user_name)
        time.sleep(1)

        # password
        password_element = self.driver.find_element_by_id('pass')
        password_element.clear()
        password_element.send_keys(self.password)
        time.sleep(1)

        # click
        login = self.driver.find_element_by_id('loginbutton')
        login.click()

        # status judgement
        current_page_url = self.driver.current_url
        if current_page_url != self.url:
            self.login_state = 0
        else:
            self.login_state = 1

    def make_post(self):
        current_url = self.driver.current_url
        if current_url != self.url:
            self.enter_homepage_self()
        else:
            pass
        post_element = self.driver.find_element_by_class_name(self.post_class_name)
        post_element.click()

    def page_refresh_to_bottom(self, _item, _timeout=3, _poll_frequency=0.5):
        """
        页面刷新
        :param _item: 下拉页类型，分为用户搜索和照片搜索两类
        :param _timeout: 模拟下拉的时间延迟
        :param _poll_frequency: 模拟下拉的时间频率
        :return: NULL
        """
        if _item == "users":
            xpath = self.bottom_xpath_search
        else:
            xpath = self.bottom_xpath_other

        while True:
            # noinspection PyBroadException
            try:
                WebDriverWait(self.driver, timeout=_timeout, poll_frequency=_poll_frequency).until(
                    EC.presence_of_element_located((By.XPATH, xpath)))
                break
            except BaseException:
                self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')

    def page_refresh(self, _refresh_times=0):
        """
        页面刷新
        :param _refresh_times: 刷新次数
        :return: Null
        """
        for i in range(_refresh_times):
            self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            try:
                bottom_element = self.driver.find_element_by_xpath(self.bottom_xpath_search)
            except BaseException:
                bottom_element = self.driver.find_element_by_xpath(self.bottom_xpath_other)

            if bottom_element is not None:
                break

    def get_myself_info(self):
        """
        获取当前登录账户的信息
        :return:
            user_name: 用户名
            user_id: 用户id
            homepage_url: 用户主页
        """
        current_url = self.driver.current_url
        if current_url == self.url:
            pass
        else:
            self.driver.get(self.url)

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, self.soup_type)

        main_container = soup.find(class_=self.main_container_class_name)
        id_class = main_container.li
        user_id = id_class.get(self.myself_id_class_name)
        user_info_class = main_container.find_all("a")
        user_name = user_info_class[1].get("title")
        homepage_url = user_info_class[1].get("href")
        homepage_url = homepage_url.split("?")[0]

        return user_name, user_id, homepage_url

    def enter_homepage_self(self):
        """
        进入个人主页，facebook登录后页面仍停留在https://www.facebook.com，需要进一步跳转到个人主页，获取到主页url，
        方便对好友列表，照片的获取
        :return:
        """
        _, homepage_url, __ = self.get_myself_info()
        current_url = self.driver.current_url
        if current_url == homepage_url:
            pass
        else:
            self.driver.get(homepage_url)

    def get_user_id(self, _user_homepage_url):
        """
        根据用户的主页url获取其user id
        :param _user_homepage_url: 用户的主页url
        :return: user id
        """
        if utils.url_type_judge(_user_homepage_url) == 1:
            self.driver.get(_user_homepage_url)
            page = self.driver.page_source
            soup = BeautifulSoup(page, self.soup_type)
            cover = soup.find(class_=self.user_cover_class_name)
            _user_id = cover.a.get("data-referrerid")
        else:
            _user_id = _user_homepage_url.split("id=")[-1]

        return _user_id

    def get_friends_number(self):
        """
        获取当前登录账户的好友数量
        :return:
            self.friends_number: 当前登录账户的好友数量
        """
        friends_page_url = utils.get_jump_url(self.homepage_url, "friends")
        self.driver.get(friends_page_url)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, self.soup_type)

        friends_table = self.driver.find_element_by_id(self.friends_number_id_name)
        friends_table_class_name = friends_table.get_attribute("class")

        block = soup.find(class_=friends_table_class_name)
        content = block.find_all("div")
        content_text = content[5].a.text
        pattern = re.compile(r"\d+\.?\d*")

        self.friends_number = int(pattern.findall(content_text)[0])

    def get_friends_list(self, _friends_number=None):
        """
        获取当前登录账户的好友列表
        :param _friends_number: 待检索的好友数量
        :return:
            self.user_info_friends: 好友用户信息 [user_name, user_id, homepage_url]
        """
        self.get_friends_number()
        if _friends_number is None or _friends_number > self.friends_number:
            self.page_refresh_to_bottom("friends")
        else:
            refresh_times = _friends_number // 20
            self.page_refresh(refresh_times)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, self.soup_type)

        # 获取好友url列表
        contents = soup.find_all(class_=self.friends_list_class_name)
        for content in contents:
            homepage_url = content.a.get("href")
            if utils.url_type_judge(homepage_url) == 1:
                homepage_url = homepage_url.replace(self.homepage_url_postfix_1, "")
            if utils.url_type_judge(homepage_url) == 2:
                homepage_url = homepage_url.replace(self.homepage_url_postfix_2, "")
            user_name = content.a.text
            pattern = re.compile(r"id=\d+")
            user_id = pattern.findall(content.a.get("data-hovercard"))[0].split("id=")[-1]

            self.user_info_friends.append([user_name, user_id, homepage_url])

    def get_user_info(self, item):
        data_be_str = item.div.get("data-bt")
        user_id = utils.str2dict(data_be_str)["id"]

        # 获取user homepage url
        user_info = item.find(class_=self.clearfix_flag)
        user_homepage_url = user_info.a.get("href")

        user_name_block = user_info.div.find(class_=self.clearfix_flag).find_all("div")
        # user_name_class_name = user_name_block[-1].a.get("class")[0]
        user_name = user_name_block[-1].a.text

        about_items = user_info.find_all("div")
        about_class = about_items[11].find_all("div")

        try:
            about = about_class[5].text
        except BaseException:
            about = None

        return [user_name, user_id, user_homepage_url, about]

    def get_class_name_for_search(self):
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, self.soup_type)

        element = self.driver.find_element_by_xpath(self.browse_results_container)
        user_search_class_name = element.get_attribute("class")
        item = soup.find(class_=user_search_class_name)
        user_info = item.find(class_=self.clearfix_flag)
        user_name_block = user_info.div.find(class_=self.clearfix_flag).find_all("div")
        user_name_class_name = user_name_block[-1].a.get("class")[0]

        self.user_search_class_name = user_search_class_name
        self.user_name_class_name = user_name_class_name

    def search_users(self, _keyword="wahaha", user_number=None):
        """
        根据关键字进行用户搜索
        :param _keyword: 待检索关键字
        :param user_number: 需要检索的用户数量
        :return:
            self.user_info_search: 用户信息列表 [user_name, user_id, location, homepage_url]
        """
        search_url = "https://www.facebook.com/search/str/" + _keyword + "keywords_users"
        self.driver.get(search_url)

        # 页面刷新
        if user_number is None:
            self.page_refresh_to_bottom("users")
        else:
            refresh_times = user_number // 5
            self.page_refresh(refresh_times)

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, self.soup_type)

        if self.user_search_class_name is None and self.user_name_class_name is None:
            self.get_class_name_for_search()

        items = soup.find_all(class_=self.user_search_class_name)
        for item in items:
            self.user_info_search.append(self.get_user_info(item))

    def get_photos_list(self, _homepage_url):
        """
        获取照片
        :param _homepage_url:
        :return:
        """
        photos_url = utils.get_jump_url(_homepage_url, "photos")
        self.driver.get(photos_url)
        page = self.driver.page_source
        soup = BeautifulSoup(page, self.soup_type)
        bottom_element = self.driver.find_element_by_xpath(self.bottom_xpath_other)

        photos_href_list = list()
        while bottom_element is None:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            page = self.driver.page_source
            soup = BeautifulSoup(page, self.soup_type)
            bottom_element = self.driver.find_element_by_xpath(self.bottom_xpath_other)
            if bottom_element is not None:
                break

        for data in soup.find_all(class_="uiMediaThumb _6i9 uiMediaThumbMedium"):
            photos_href_list.append(data.get("href"))

        return photos_href_list

    def get_photo_info(self, _photo_href):
        """
        根据图像的链接对其信息进行获取
        :param _photo_href: 图像链接
        :return:
            _link: 原始图像对应的链接
            _date: 图像发布对应的时间
            _location: 图像发布对应的位置
            _text: 图像发布对应的文本内容
            _width: 图像的实际宽度
            _height: 图像的实际高度
        """
        self.driver.get(_photo_href)
        page = self.driver.page_source
        soup = BeautifulSoup(page, self.soup_type)

        publish_time = soup.find("span", {"id": "fbPhotoSnowliftTimestamp"})
        if publish_time is None:
            _date = []
        else:
            _date = publish_time.a.abbr.get("data-utime")                       # 图片发表的时间 (Unix时间戳)

        location_object = soup.find(class_="fbPhotosImplicitLocLink")           # 图片发表的位置信息
        if location_object is not None:
            _location = location_object.text
        else:
            _location = []

        text_object = soup.find("span", {"class": "hasCaption"})                # 图片发表时对应的文字说明
        if text_object is not None:
            _text = text_object.text
        else:
            _text = []

        # 进入全屏状态
        full_screen_element = self.driver.find_element_by_id("fbPhotoSnowliftFullScreenSwitch")
        full_screen_element.click()
        page = self.driver.page_source
        soup = BeautifulSoup(page, self.soup_type)

        spotlight = soup.find(class_="spotlight")
        _link = spotlight.get("src")                                            # 图片链接
        style = spotlight.get("style")                                          # 图片尺寸字符串
        _width, _height = utils.get_size(style)                                 # 获取图像的宽和高

        return _link, _date, _location, _text, _width, _height

    def get_photos_info_list(self, _photos_href_list):
        _photos_info_list = list()
        for photo_href in _photos_href_list:
            link, date, location, text, width, height = self.get_photo_info(photo_href)
            _photos_info_list.append([link, date, location, text, width, height])

        return _photos_info_list

    def download_photos_one(self, _homepage_url, start_date=None, end_date=None, _folder_name="./"):
        """
        单个用户的
        :param _homepage_url:
        :param start_date:
        :param end_date:
        :param _folder_name:
        :return:
        """
        utils.folder_make(_folder_name)
        photos_href_list = self.get_photos_list(_homepage_url)
        photos_info_list = self.get_photos_info_list(photos_href_list)

        if start_date is None and end_date is None:
            for photo_info in photos_info_list:
                utils.download_photos(photo_info[0], _folder_name)
        else:
            start_date_unix = utils.get_unix_stamp(start_date)
            end_date_unix = utils.get_unix_stamp(end_date)
            for photo_info in photos_info_list:
                unix_time = photo_info[1]
                if start_date_unix < unix_time < end_date_unix:
                    utils.download_photos(photo_info[0], _folder_name)
                else:
                    pass

    def download_photos_batch(self, _homepage_url_list, start_date=None, end_date=None):
        for _homepage_url in _homepage_url_list:
            folder_name = _homepage_url.split("/")[-1]
            self.download_photos_one(_homepage_url, start_date, end_date, folder_name)


if __name__ == "__main__":
    email, password = utils.get_account("account.csv", 0)
    fb = Facebook(email, password, "Chrome", False)
    if fb.browser_state == 1:
        fb.sign_in()
        fb.enter_homepage_self()
        fb.make_post()
        cookies = fb.cookies

    else:
        print("Initialization failed.")
