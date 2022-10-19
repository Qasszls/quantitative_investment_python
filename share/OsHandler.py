# -*- coding:UTF-8 -*-
import pexpect


class OsHandler:
    #命令行 关机
    def close_mac(self):
        child = pexpect.spawn('sudo shutdown -h now')
        child.expect('Password:')
        child.sendline('1874')
        child.interact()

    #命令行 清屏
    def clear_tem(self):
        child = pexpect.spawn('clear')
        child.interact()