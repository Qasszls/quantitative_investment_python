import logging
from logging import Logger, INFO
from .setting import SETTINGS
from events.event import EVENT_LOG, EVENT_DING
from datetime import datetime
from dingtalkchatbot.chatbot import DingtalkChatbot


class LogEngine:
    """
    Processes log event and output with logging module.
    """

    def __init__(self) -> None:

        self.level: int = SETTINGS["log.level"]
        self.logger: Logger = logging.getLogger()
        self.logger.setLevel(self.level)
        self.formatter: logging.Formatter = logging.Formatter(
            "\n%(asctime)s  %(levelname)s: %(message)s"
        )
        self.add_console_handler()

    def add_console_handler(self) -> None:
        """
        Add console output of log.
        """
        console_handler: logging.StreamHandler = logging.StreamHandler()
        console_handler.setLevel(INFO)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

    def process_log_event(self, event) -> None:
        """
        Process log event.
        """
        log = event.data
        level = INFO
        msg = log['msg']
        if log['level']:
            level = log['level']
        self.logger.log(level, msg)


class DingDingEngine:
    def __init__(self, event_engine):
        self.event_engine = event_engine
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=cb4b89ef41c8008bc4526bc33d2733a8c830f1c10dd6701a58c3ad149d35c8cc'
        self.ding = DingtalkChatbot(webhook)
        self.register_event()

    def emit(self, event):
        text = event.data + '  作业时间：' + str(datetime.now()) + ' :525'
        self.ding.send_text(msg=text, is_at_all=False)

    def register_event(self):
        self.event_engine.register(EVENT_DING, self.emit)
