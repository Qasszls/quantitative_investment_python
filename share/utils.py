"""
    我是注释
"""
import json
import time
from tqdm import tqdm
from timeit import default_timer as timer



def to_json_parse(data):
    if type(data) == str:
        return json.loads(data)
    else:
        raise Exception('请输入字符串参数，该函数会帮助你解析')


def to_json_stringify(data):
    return json.dumps(data)


def get_time_stamp(tss):
    times = time.strptime(tss, "%Y-%m-%d %H:%M:%S")
    timestamp = int(time.mktime(times)) * 1000
    return timestamp


def get_time_normal(tamp):
    if type(tamp) != type(1):
        tamp = int(tamp)
    times = time.localtime(int(tamp) / 1000)
    otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", times)
    return otherStyleTime


def is_pass(input):
    pass_list = ['', 'y', 'yes', 'Y', 'YES']
    if input in pass_list:
        return True
    else:
        return False

    # 将时间粒度换算成毫秒值


def timestamp_to_ms(unit, bar_val):
    divide = ''
    if unit == 'm':
        divide = bar_val * 60 * 1000
    elif unit == 'H':
        divide = bar_val * 60 * 60 * 1000
    elif unit == 'D':
        divide = bar_val * 60 * 24 * 60 * 1000
    elif unit == 'W':
        divide = bar_val * 7 * 24 * 60 * 60 * 1000
    elif unit == 'M':
        divide = bar_val * 24 * 30 * 60 * 60 * 1000
    elif unit == 'Y':
        divide = bar_val * 12 * 24 * 30 * 60 * 60 * 1000
    return int(round(divide))

    # 根据粒度换算出一共需要请求多少次


def get_divide(ms, unit, bar_val):
    """根据粒度换算出一共需要请求多少次

    Args:
        unit (str): 时间粒度单位
        ms (int): 毫秒级时间段
        val (int): 时间粒度值

    Returns:
        int: 次数
    """
    divide = ''
    if unit == 'm':
        divide = ms / 1000 / 60 / bar_val
    elif unit == 'H':
        divide = ms / 1000 / 60 / 60 / bar_val
    elif unit == 'D':
        divide = ms / 1000 / 60 / 60 / 24 / bar_val
    elif unit == 'W':
        divide = ms / 1000 / 60 / 60 / 24 / 7 / bar_val
    elif unit == 'M':
        divide = ms / 1000 / 60 / 60 / 24 / 30 / bar_val
    elif unit == 'Y':
        divide = ms / 1000 / 60 / 60 / 24 / 30 / 12 / bar_val
    return int(round(divide))


# class DownloadBar:
#     def __init__(self):
#         self.bar = ''

#     def update(self, count, limit):
#         self.bar.set_description(
#             emoji.emojize('本次传输剩余   {count}条   每次{limit}条 📆'.format(count=count, limit=limit)))

#         self.bar.update(limit)

#     def create_bar(self, *args, **kwargs):
#         self.bar = tqdm(*args, **kwargs)

#     def destroy_all(self):
#         self.bar = ''
