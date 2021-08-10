# -*- coding:UTF-8 -*-

import matplotlib.pyplot as plt
import numpy as np

from util.TimeStamp import TimeTamp


class DrawMacd():
    def __init__(self, coinDataFrame):
        self.coinDataFrame = coinDataFrame
        self.long = 1000

    def run(self, coinDataFrame):
        timeStamp = TimeTamp()
        long = self.long
        plt.close('all')

        deaY = coinDataFrame['dea'].loc[0:long].values
        deaX = range(len(deaY))

        difY = coinDataFrame['dif'].loc[0:long].values
        difX = range(len(difY))
        # print(x, '/n', y)
        plt.plot(deaX, deaY, ls="-", lw=1, color="red", label='DEA')
        plt.plot(difX, difY, ls="-", lw=1, color="blue", label='DIF')

        # 开始绘图
        # plt.figure()

        # 设置MACD柱状图
        redBar = []
        greenBar = []
        tamp = []
        for item in coinDataFrame.loc[0:long]['id_tamp'].values:
            tamp.append(timeStamp.get_time_normal(item))
        for index, row in coinDataFrame.iterrows():
            if index > long:
                break
            if (row['macd'] > 0):  # 大于0则用红色
                redBar.append(row['macd'] * 2)
                greenBar.append(0)
            else:  # 小于等于0则用绿色
                greenBar.append(row['macd'] * 2)
                redBar.append(0)

        plt.bar(tamp, redBar, width=0.5, color='red')
        plt.bar(tamp, greenBar, width=0.5, color='green')

        # 设置x轴坐标的标签和旋转角度
        major_index = [0, 1]
        major_xtics = [2, 3]
        plt.xticks(major_index, major_xtics)
        # plt.setp(plt.gca().get_xticklabels(), rotation=30)
        # 带网格线，且设置了网格样式
        # plt.grid(linestyle='-.')
        plt.title("aaaaa")
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.legend(loc='best')

        plt.show()
