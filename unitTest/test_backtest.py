from backtest.exchange import UserInfo
from backtest.constants import BUY, SELL, Market
from backtest.config import ConfigEngine
from backtest.analysis import AnalysisEngine
from events.engine import EventEngine
import unittest
from backtest.config import BASE_CONFIG, VAR_CONFIG, BAR_CONFIG, CHECK_SURPLUS_SCOPE, STOP_LOSS_SCOPE

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
        self.market = Market()
        self.market.update_tick(M1)
        self.analysis = AnalysisEngine()

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

        # print('总权益', self.market.close*expect_availPos, '预期保证金', expect_margin_lever, '预期总负债',
        #       expect_liability, '预期收益率', expect_uplRatio)

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

    # 获得回测数据
    def test_get_market_data(self):
        # 获取数据
        def get_list_type(list, type):
            res = []
            for item in list:
                res.append(item[type])
            return res

        def get_length(scope):
            _len = 0
            cursor = scope['min']
            while cursor <= scope['max']:
                _len += 1
                cursor += scope['up']
            return _len

        bar_config = ['1H', '2H']
        cs_scope = {'min': 1, 'max': 2, 'up': 1}
        sl_scope = {'min': 0.5, 'max': 1, 'up': 0.5}
        base_config = {**VAR_CONFIG, **BASE_CONFIG}

        config_group: list = self.analysis.get_test_config(
            bar_config=bar_config, cs_scope=cs_scope, sl_scope=sl_scope, base_config=base_config)

        expect_length = get_length(
            cs_scope)*len(bar_config) + len(bar_config) * get_length(sl_scope)

        expect_check_surplus = [1, 1, 2, 2, 1, 1, 2, 2]
        check_surplus_list = get_list_type(config_group, 'checkSurplus')
        expect_stop_loss = [0.5, 1.0, 0.5, 1.0, 0.5, 1.0, 0.5, 1.0]
        stop_loss_list = get_list_type(config_group, 'stopLoss')

        self.assertTrue(len(config_group) == expect_length, msg="回测配置数据错误：{error}, 预期数据为{expect}".format(
            error=len(config_group), expect=expect_length))

        self.assertTrue(expect_check_surplus == check_surplus_list,
                        msg="回测配置止盈率增速错误：{error}, 预期数据为{expect}".format(
                            error=check_surplus_list, expect=expect_check_surplus))

        self.assertTrue(expect_stop_loss == stop_loss_list,
                        msg="回测配置止损率增速错误：{error}, 预期数据为{expect}".format(
                            error=stop_loss_list, expect=expect_stop_loss))

    # 导出excel
    def test_write_excel(self):
        columns = ['总资产', '收益率']
        col1 = ['1000', '0.1']
        col2 = ['2000', '0.2']
        file_name = 'test.xlsx'
        self.analysis._write_excel(
            file_name=file_name, columns=columns, cols_data=[col1, col2])

        data = self.analysis._read_from_excel(
            file_name=file_name, dtype={'总资产': 'str', '收益率': 'str'})
        columns = data.columns.to_list()
        analysis_list = data.to_numpy().tolist()

        expect_columns = ['总资产', '收益率']
        expect_list = [['1000', '0.1'], ['2000', '0.2']]
        expect_length = 2

        self.assertTrue(expr=columns == expect_columns, msg="excel列名写入错误, 错误数据: {err}, 预期数据: {exp}".format(
            err=columns, exp=expect_columns))
        self.assertTrue(expr=analysis_list == expect_list, msg="excel数据写入错误, 错误数据: {err}, 预期数据: {exp}".format(
            err=analysis_list, exp=expect_list))
        self.assertTrue(expr=len(analysis_list) == expect_length, msg="excel写入条目数量错误,错误数据 {err}, 预期数据: {exp}".format(
            err=len(columns), exp=expect_length))
