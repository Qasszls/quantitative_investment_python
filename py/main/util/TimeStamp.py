# -*- coding:UTF-8 -*-
import time


class TimeTamp:
    def __init__(self):
        None

    def get_time_stamp(self, tss):
        times = time.strptime(tss, "%Y-%m-%d %H:%M:%S")
        timeStamp = int(time.mktime(times))
        return timeStamp

    def get_time_normal(self, tamp):
        times = time.localtime(int(tamp) / 1000)
        otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", times)
        return otherStyleTime
