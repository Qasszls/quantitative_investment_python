# -*- coding:UTF-8 -*-
import time


class Timestamp:
    def __init__(self):
        None

    def get_time_stamp(self, tss):
        times = time.strptime(tss, "%Y-%m-%d %H:%M:%S")
        timestamp = int(time.mktime(times)) * 1000
        return timestamp

    def get_time_normal(self, tamp):
        if type(tamp) != type(1):
            tamp = int(tamp)
        times = time.localtime(int(tamp) / 1000)
        otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", times)
        return otherStyleTime


if __name__ == '__main__':
    times = Timestamp()
    print(times.get_time_stamp("2021-11-1 23:59:59"))
