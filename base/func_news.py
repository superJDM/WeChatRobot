#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import re
import time
from datetime import datetime

import requests
from lxml import etree


class News(object):
    def __init__(self) -> None:
        self.LOG = logging.getLogger(__name__)
        self.week = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0"}

    def get_important_news(self):
        url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=7.7.5"
        data = {"type": "telegram", "keyword": "你需要知道的隔夜全球要闻", "page": 0, "rn": 1, "os": "web", "sv": "7.7.5", "app": "CailianpressWeb"}
        try:
            rsp = requests.post(url=url, headers=self.headers, data=data)
            data = json.loads(rsp.text)["data"]["telegram"]["data"][0]
            news = data["descr"]
            timestamp = data["time"]
            ts = time.localtime(timestamp)
            weekday_news = datetime(*ts[:6]).weekday()
        except Exception as e:
            self.LOG.error(e)
            return ""

        weekday_now = datetime.now().weekday()
        if weekday_news != weekday_now:
            return ""  # 旧闻，观察发现周二～周六早晨6点半左右发布

        fmt_time = time.strftime("%Y年%m月%d日", ts)
        news = re.sub(r"(\d{1,2}、)", r"\n\1", news)
        fmt_news = "".join(etree.HTML(news).xpath(" // text()"))
        fmt_news = re.sub(r"周[一|二|三|四|五|六|日]你需要知道的", r"", fmt_news)

        return f"{fmt_time} {self.week[weekday_news]}\n{fmt_news}"

    def get_hotLine(self):
        # url = "https://zj.v.api.aa1.cn/api/weibo-rs/"
        url = "https://api.oioweb.cn/api/common/HotList"
        news_list = []
        try:
            rsp = requests.post(url=url, headers=self.headers)
            # print(rsp.text)
            zhihu = json.loads(rsp.text)["result"]["知乎"][:5]
            weibo = json.loads(rsp.text)["result"]["微博"][:5]
            weixin = json.loads(rsp.text)["result"]["微信"][:5]
            now = datetime.now().strftime("%H时%M分的热点新闻")

        except Exception as e:
            self.LOG.error(e)
            return ""
        news_list.append(self.handle_news(zhihu, "知乎榜单"))
        news_list.append(self.handle_news(weibo, "微博热搜"))
        news_list.append(self.handle_news(weixin, "阅读精选"))
        return_news = "\n\n".join(news_list)
        return f"{now}:\n{return_news}"

    def news_60s(self):
        url = "https://jx.iqfk.top/60s.php"
        data = {
            "key": "54K55paw6Iqx6Zuo",
            "type": "json",
        }
        data1 = {
            "key": "54K55paw6Iqx6Zuo",
            "type": "zhihu",
        }
        try:
            rsp = requests.post(url=url, headers=self.headers, params=data)
            rsp1 = requests.post(url=url, headers=self.headers, params=data1)
            weiyu = json.loads(rsp1.text)["data"]["weiyu"]
            news = json.loads(rsp.text)["data"]["news"][:10]
            news_zhihu = json.loads(rsp1.text)["data"]["news"][:10]
            date = json.loads(rsp1.text)["data"]["date"]

        except Exception as e:
            self.LOG.error(e)
            return ""
        now = f"{date}\n小明助手为您带来每日要闻"

        news_list = news + self.handle_news_index(news_zhihu)

        return_news = "\n".join(news_list)

        return f"{now}:\n{return_news}\n\n{weiyu}"

    def handle_news(self, news_list=None, news_name=""):
        if news_list is None:
            news_list = []
        temp_list = []
        for slice in news_list:
            single: str = str(slice["index"]) + "." + slice["title"] + "\n详情：" + slice["href"]
            temp_list.append(single)
            fmt_news = "\n".join(temp_list)
        return f"{news_name}:\n{fmt_news}"

    def handle_news_index(self, old_list=None):
        # 将1-10 增加为11-20
        if old_list is None:
            old_list = []

        news_list = ["1" + slice for slice in old_list if slice[:2] != "10"]
        news_list.append(old_list[9].replace("10", "20", 1))
        return news_list


if __name__ == "__main__":
    news = News()
    print(news.get_hotLine())
