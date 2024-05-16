import random
import logging
from wcferry import Wcf, WxMsg

LOG = logging.getLogger("Robot")

def random_string_from_list(string_list):
    return random.choice(string_list)

def print_msg_types():
    return LOG.info(f"获取消息类型:{Wcf.get_msg_types(self)}")
    