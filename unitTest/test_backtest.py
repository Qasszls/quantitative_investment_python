from backtest.exchange import UserInfo
from backtest.constants import BUY, SELL, Market
from backtest.config import ConfigEngine
import unittest

M1 = ['1630253100000', '1000',  '1200',  '1000',
      '1000', '20.2032413',  '978089.07178282']
M2 = ['1630253400000', '3000',  '3200',  '3000',
      '3000',  '9.77776054',  '473503.54160751']
COUNT = 2.0


class test_backtest_trading(unittest.TestCase):

    def setUp(self):
        # 测试数据
        self.info = {
            'initCoin': 1.0,
            'initFund': 500000.0,
            'avgPx': 500.0,
            'name': 'quant',
            'uplRatio': 0.0,
        }
        self.config = ConfigEngine().get_config()
        self.user = UserInfo({**self.info, **self.config})
        self.market = Market(M1)

    # 用户购买
    def test_user_buy(self):

        total_price = self.market.close * COUNT * \
            BUY * (1+self.config['eatOrder']) * \
            (1+self.config['slippage'])  # 总价

        expect_avgPx = (self.user.avgPx + self.market.close) / \
            2  # 预期持仓均价 (旧持仓均价 + 买入时价格) / 2
        expect_availBal = total_price + self.user.availBal  # 预期可用资产
        expect_availPos = self.user.availPos + COUNT  # 预期币量
        expect_uplRatio = (self.market.close -
                           expect_avgPx)/expect_avgPx  # 预期收益率

        # 操作
        self.user.user_trading(
            type=BUY, price=self.market.close, count=COUNT)
        # 检查
        self.assertTrue(expr=self.user.availBal ==
                        expect_availBal, msg='用户购买后资产更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availBal, truly=expect_availBal))
        self.assertTrue(expr=self.user.availPos ==
                        expect_availPos, msg='用户购买后持仓更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availPos, truly=expect_availPos))
        self.assertTrue(expr=self.user.avgPx ==
                        expect_avgPx, msg='用户购买后持仓均价更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.avgPx, truly=expect_avgPx))
        self.assertTrue(expr=self.user.uplRatio ==
                        expect_uplRatio, msg='用户购买后收益率更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.uplRatio, truly=expect_uplRatio))

    # 用户出售
    def test_user_sell(self):

        total_price = self.market.close * self.user.availPos * \
            SELL * (1+self.config['eatOrder']) * \
            (1-self.config['slippage'])  # 总价

        expect_avgPx = 0.0  # 预期持仓均价 (旧持仓均价 + 买入时价格) / 2
        expect_availBal = total_price + self.user.availBal  # 预期可用资产
        expect_availPos = 0.0  # 预期币量
        expect_uplRatio = 0.0  # 预期收益率

        # 操作
        self.user.user_trading(
            type=SELL, price=self.market.close)
        # 检查
        self.assertTrue(expr=self.user.availBal ==
                        expect_availBal, msg='用户购买后资产更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availBal, truly=expect_availBal))
        self.assertTrue(expr=self.user.availPos ==
                        expect_availPos, msg='用户购买后持仓更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.availPos, truly=expect_availPos))
        self.assertTrue(expr=self.user.avgPx ==
                        expect_avgPx, msg='用户购买后持仓均价更新异常当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.avgPx, truly=expect_avgPx))
        self.assertTrue(expr=self.user.uplRatio ==
                        expect_uplRatio, msg='用户购买后收益率更新异常, 当前数据为:{error}, 正确数据为:{truly}'.format(error=self.user.uplRatio, truly=expect_uplRatio))
