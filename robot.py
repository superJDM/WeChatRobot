# -*- coding: utf-8 -*-

import logging
import re
import time
import xml.etree.ElementTree as ET
from queue import Empty
from threading import Thread

from wcferry import Wcf, WxMsg

from base.func_bard import BardAssistant
from base.func_chatglm import ChatGLM
from base.func_chatgpt import ChatGPT
from base.func_chengyu import cy
from base.func_news import News
from base.func_tigerbot import TigerBot
from base.func_xinghuo_web import XinghuoWeb
from base.func_zhipu import ZhiPu
from configuration import Config
from constants import ChatType
from job_mgmt import Job
from upgrade import print_msg_types, random_string_from_list

__version__ = "39.0.10.1"


class Robot(Job):
    """个性化自己的机器人"""

    def __init__(self, config: Config, wcf: Wcf, chat_type: int) -> None:
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.getAllContacts()
        # self.LOG.info(f"获取消息类型:{self.wcf.get_msg_types()}")

        if ChatType.is_in_chat_types(chat_type):
            if chat_type == ChatType.TIGER_BOT.value and TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif chat_type == ChatType.CHATGPT.value and ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif chat_type == ChatType.XINGHUO_WEB.value and XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif chat_type == ChatType.CHATGLM.value and ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif chat_type == ChatType.BardAssistant.value and BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif chat_type == ChatType.ZhiPu.value and ZhiPu.value_check(self.config.ZHIPU):
                self.chat = ZhiPu(self.config.ZHIPU)
            else:
                self.LOG.warning("未配置模型")
                self.chat = None
        else:
            if TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif ZhiPu.value_check(self.config.ZhiPu):
                self.chat = ZhiPu(self.config.ZhiPu)
            else:
                self.LOG.warning("未配置模型")
                self.chat = None

        self.LOG.info(f"已选择: {self.chat}")

    @staticmethod
    def value_check(args: dict) -> bool:
        if args:
            return all(value is not None for key, value in args.items() if key != "proxy")
        return False

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        return self.toChitchat(msg)

    def toChengyu(self, msg: WxMsg) -> bool:
        """
        处理成语查询/接龙消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        status = False
        texts = re.findall(r"^([#|?|？])(.*)$", msg.content)
        # [('#', '天天向上')]
        if texts:
            flag = texts[0][0]
            text = texts[0][1]
            if flag == "#":  # 接龙
                if cy.isChengyu(text):
                    rsp = cy.getNext(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True
            elif flag in ["?", "？"]:  # 查词
                if cy.isChengyu(text):
                    rsp = cy.getMeaning(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True

        return status

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT"""
        if msg.sender not in self.config.FRIENDS:  # 没权限的人问
            rsp_list = [
                "你找我干嘛？",
                "?",
                "嗯?",
                "有什么事情吗？",
                "你好",
                "好的",
                "我现在有点忙，后面有时间再说",
                "谢谢",
                "好，我知道了",
                "你应该知道我只是AI吧",
                "如你所想，我只是个AI",
            ]
            # 过于沙雕 关了
            # rsp = random_string_from_list(rsp_list)
            return True
        else:  # 报备微信ID，智能回复
            rsp_list = [
                "请稍后....",
                "请给我一点思考的时间!",
                "信息接收中...",
                "收到，稍后回复您",
                "麻烦您稍等",
                "等我问问看",
                "我想想噢",
            ]
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            # 等待时的临时回复
            temp_answer = random_string_from_list(rsp_list)
            self.sendTextMsg(temp_answer, (msg.roomid if msg.from_group() else msg.sender), (msg.sender if msg.from_group() else ""))
            if "热点新闻" in msg.content:
                rsp = News().get_hotLine()
                self.sendImageMsg(f"https://jx.iqfk.top/60s.php?key=54K55paw6Iqx6Zuo&type=img", msg.sender)
            else:
                rsp = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))
        if rsp:
            if "multi_image_url" in rsp:
                picurl = rsp.split("{")[1].split("}")[0][7:-1]
                if msg.from_group():
                    self.sendImageMsg(picurl, msg.roomid, msg.sender)
                else:
                    self.sendImageMsg(picurl, msg.sender)

            else:
                if msg.from_group():
                    self.sendTextMsg(rsp, msg.roomid, msg.sender)
                else:
                    self.sendTextMsg(rsp, msg.sender)

            return True
        else:
            self.LOG.error(f"无法从AI助手处获得答案")
            return False

    def processMsg(self, msg: WxMsg) -> None:
        """当接收到消息的时候，会调用本方法。如果不实现本方法，则打印原始消息。
        此处可进行自定义发送的内容,如通过 msg.content 关键字自动获取当前天气信息，并发送到对应的群组@发送者
        群号：msg.roomid  微信ID：msg.sender  消息内容：msg.content
        content = "xx天气信息为："
        receivers = msg.roomid
        self.sendTextMsg(content, receivers, msg.sender)
        """

        # 群聊消息
        if msg.from_group():
            # 如果在群里被 @
            if msg.roomid not in self.config.GROUPS:  # 不在配置的响应的群列表里，忽略
                return

            if msg.is_at(self.wxid):  # 被@
                self.toAt(msg)

            # else:  # 其他消息
            #     self.toChengyu(msg)

            return  # 处理完群聊信息，后面就不需要处理了

        # 非群聊信息，按消息类型进行处理
        """{0: '朋友圈消息', 1: '文字', 3: '图片', 34: '语音', 37: '好友确认', 40: 'POSSIBLEFRIEND_MSG', 42: '名片', 43: '视频', 47: '石头剪刀布 | 表情图片', 
          48: '位置', 49: '共享实时位置、文件、转账、链接', 50: 'VOIPMSG', 51: '微信初始化', 52: 'VOIPNOTIFY', 53: 'VOIPINVITE', 62: '小视频', 66: '微信红包',
          9999: 'SYSNOTICE', 10000: '红包、系统消息', 10002: '撤回消息', 1048625: '搜狗表情', 16777265: '链接', 436207665: '微信红包', 536936497: '红包封面', 
          754974769: '视频号视频', 771751985: '视频号名片', 822083633: '引用消息', 922746929: '拍一拍', 973078577: '视频号直播', 974127153: '商品链接', 
          975175729: '视频号直播', 1040187441: '音乐链接', 1090519089: '文件'}
        """
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)

        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)

        elif msg.type == 0x01:  # 文本消息
            # 让配置加载更灵活，自己可以更新配置。也可以利用定时任务更新。
            self.LOG.info(f"已接收：{msg.content}")
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新")
            else:
                self.toChitchat(msg)  # 闲聊

    def onMsg(self, msg: WxMsg) -> int:
        try:
            self.LOG.info(msg)  # 打印信息
            self.processMsg(msg)
        except Exception as e:
            self.LOG.error(e)

        return 0

    def enableRecvMsg(self) -> None:
        self.wcf.enable_recv_msg(self.onMsg)

    def enableReceivingMsg(self) -> None:
        def innerProcessMsg(wcf: Wcf):
            while wcf.is_receiving_msg():
                try:
                    msg = wcf.get_msg()
                    self.LOG.info(msg)
                    self.processMsg(msg)
                except Empty:
                    continue  # Empty message
                except Exception as e:
                    self.LOG.error(f"Receiving message error: {e}")

        self.wcf.enable_receiving_msg()
        Thread(target=innerProcessMsg, name="GetMessage", args=(self.wcf,), daemon=True).start()

    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                wxids = at_list.split(",")
                for wxid in wxids:
                    # 根据 wxid 查找群昵称
                    ats += f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三
        if ats == "":
            self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"To {receiver}: {ats}\r{msg}")
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

    def sendImageMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """发送图片消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        wxids = at_list.split(",")
        picname = msg.split("?")[0].split("/")[-1]
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                wxids = at_list.split(",")
                for wxid in wxids:
                    # 根据 wxid 查找群昵称
                    ats += f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三
        if ats == "":
            self.LOG.info(f"发送图片给 {receiver} 图片名称: {picname} ")
            self.wcf.send_image(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"发送图片给 {receiver} 图片名称: {picname} ")
            self.wcf.send_image(f"{msg}", receiver, at_list)

    def getAllContacts(self) -> dict:
        """
        获取联系人（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in contacts}

    def keepRunningAndBlockProcess(self) -> None:
        """
        保持机器人运行，不让进程退出
        """
        while True:
            self.runPendingJobs()
            time.sleep(1)

    def autoAcceptFriendRequest(self, msg: WxMsg) -> None:
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            self.wcf.accept_new_friend(v3, v4, scene)

        except Exception as e:
            self.LOG.error(f"同意好友出错：{e}")

    def sayHiToNewFriend(self, msg: WxMsg) -> None:
        nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
        if nickName:
            # 添加了好友，更新好友列表
            self.allContacts[msg.sender] = nickName[0]
            self.sendTextMsg(f"Hi {nickName[0]}，我自动通过了你的好友请求。", msg.sender)

    def newsReport(self) -> None:
        receivers = self.config.NEWS
        if not receivers:
            return

        news = News().get_important_news()
        # 0521 新增红色背景每日新闻，在没有财经新闻或问的时候出现
        if len(news) < 10:
            new_news = News().news_60s()
            for r in receivers:
                # self.LOG.info(f"发送新闻图片给 {r} ")
                # self.sendImageMsg(f"https://zj.v.api.aa1.cn/api/60s-v2/?cc=小明助手", r)
                self.sendTextMsg(new_news, r)
        else:
            for r in receivers:
                self.sendTextMsg(news, r)

    def send_news(self, reciver=None) -> None:
        receivers = self.config.FRIENDS
        if not receivers:
            return
        # 0525 新增热点新闻
        hot_news = News().get_hotLine()
        if reciver in receivers:
            self.sendTextMsg(hot_news, reciver)
