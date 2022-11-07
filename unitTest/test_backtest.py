from gevent import config
from backtest.exchange import UserInfo
from backtest.constants import BUY, SELL, Market
from backtest.config import ConfigEngine
import unittest

M1 = ['1630253100000', '20000',  '12200',  '20000',
      '20000', '20.2032413',  '978089.07178282']
M2 = ['1630253400000', '3000',  '3200',  '3000',
      '3000',  '9.77776054',  '473503.54160751']
COUNT = 2.0

CONFIG = {
    "initCoin": 0.0,  # 初始币数量
    "avgPx": 0.0,  # 开仓均价
    "liability": 0  # 初始负债
}


class test_backtest_trading(unittest.TestCase):

    def setUp(self):
        # 测试数据
        self.config = ConfigEngine().get_config()
        self.user = UserInfo({**self.config, **CONFIG})
        self.market = Market(M1)

    # 用户购买
    def test_user_buy(self):
        real_price = self.market.close * (1+self.config['slippage'])  # 购买价格
        new_liability = real_price * COUNT
        service_charge = new_liability * self.config['eatOrder']  # 手续费
        margin_lever = new_liability / self.user.lever
        expect_margin_lever = margin_lever + self.user.margin_lever  # 预期保证金
        expect_liability = new_liability + self.user.liability  # 预期总负债
        expect_avgPx = real_price if int(self.user.avgPx) == 0 else (
            self.user.avgPx + real_price)/2  # 预期持仓均价
        expect_availBal = self.user.availBal - \
            service_charge - expect_margin_lever  # 预期可用资产
        expect_availPos = self.user.availPos + COUNT  # 预期币量
        expect_uplRatio = (self.market.close*expect_availPos -
                           expect_liability)/expect_margin_lever  # 预期收益率

        print('总权益', self.market.close*expect_availPos, '预期保证金', expect_margin_lever, '预期总负债',
              expect_liability, '预期收益率', expect_uplRatio)

        # 操作
        self.user.user_trading(
            type=BUY, price=self.market.close, count=COUNT)
        # 检查
        self.assertTrue(expr=self.user.availBal ==
                        expect_availBal, msg='用户购买后可用资产更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availBal, truly=expect_availBal))
        self.assertTrue(expr=self.user.availPos ==
                        expect_availPos, msg='用户购买后持仓更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availPos, truly=expect_availPos))
        self.assertTrue(expr=self.user.avgPx ==
                        expect_avgPx, msg='用户购买后持仓均价更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.avgPx, truly=expect_avgPx))
        self.assertTrue(expr=self.user.uplRatio ==
                        expect_uplRatio, msg='用户购买后收益率更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.uplRatio, truly=expect_uplRatio))
        self.assertTrue(expr=self.user.liability ==
                        expect_liability, msg='用户购买后负债更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.liability, truly=expect_liability))
        self.assertTrue(expr=self.user.margin_lever ==
                        expect_margin_lever, msg='用户购买后保证金更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.margin_lever, truly=expect_margin_lever))

    # 用户出售
    def test_user_sell(self):

        real_price = self.market.close * (1-self.config['slippage'])  # 出售价格
        asset = real_price * self.user.availPos  # 仓位资产
        service_charge = asset * self.config['eatOrder']  # 手续费
        earnings = asset - self.user.liability - \
            service_charge + self.user.margin_lever  # 收益

        expect_avgPx = 0.0  # 预期持仓均价 (旧持仓均价 + 买入时价格) / 2
        expect_availBal = earnings + self.user.availBal  # 预期可用资产
        expect_availPos = 0.0  # 预期币量
        expect_uplRatio = 0.0  # 预期收益率
        expect_margin_lever = 0.0  # 预期保证金
        expect_liability = 0.0  # 预期总负债

        # 操作
        self.user.user_trading(
            type=SELL, price=self.market.close)
        # 检查
        self.assertTrue(expr=self.user.availBal ==
                        expect_availBal, msg='用户出售后资产更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availBal, truly=expect_availBal))
        self.assertTrue(expr=self.user.availPos ==
                        expect_availPos, msg='用户出售后持仓更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availPos, truly=expect_availPos))
        self.assertTrue(expr=self.user.avgPx ==
                        expect_avgPx, msg='用户出售后持仓均价更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.avgPx, truly=expect_avgPx))
        self.assertTrue(expr=self.user.uplRatio ==
                        expect_uplRatio, msg='用户出售后收益率更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.uplRatio, truly=expect_uplRatio))
        self.assertTrue(expr=self.user.liability ==
                        expect_liability, msg='用户出售后负债更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.liability, truly=expect_liability))
        self.assertTrue(expr=self.user.margin_lever ==
                        expect_margin_lever, msg='用户出售后保证金更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.margin_lever, truly=expect_margin_lever))
