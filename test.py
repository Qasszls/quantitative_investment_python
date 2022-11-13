"""单元测试页面

    Returns:
        _type_: _description_
    """
import unittest
from unittestreport import TestRunner


def create_suit():
    discover = unittest.defaultTestLoader.discover(
        "unitTest", pattern="test*.py", top_level_dir=None)
    return discover


if __name__ == "__main__":
    suit = create_suit()
    runner = TestRunner(suit, title='量化交易策略-交易系统单元测试',
                        desc='测试交易后，用户资产、收益率、持币数量和持仓均价计算结果')
    runner.run()
