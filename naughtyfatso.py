# -*- coding: utf-8 -*-
from dataclasses import asdict, dataclass
import ctypes
import threading
import time

from PIL import Image
from pystray import Icon, Menu, MenuItem
import darkdetect as dd

from config import Config, ExcludeList
from get_proc_mems import get_proc_mems
from utils import resource_path

APP_NAME = 'NaughtyFatso'

DEFAULT_SETTINGS = {
    'interval': 30,
    'threshold': 256
}

PreferredAppMode = {
    'Light': 0,
    'Dark': 1,
}
# https://github.com/moses-palmer/pystray/issues/130
ctypes.windll['uxtheme.dll'][135](PreferredAppMode[dd.theme()])


@dataclass
class Setting:
    interval: int
    threshold: int


def get_version():
    v = 'test'
    try:
        with open(resource_path('Assets/version.txt')) as fd:
            v = fd.read().strip().removeprefix('v')
    except Exception:
        pass
    return v


class TaskTray:
    def __init__(self):
        self.stop_monitor_event = threading.Event()
        self.config = Config(APP_NAME)
        self.interval = DEFAULT_SETTINGS['interval']
        self.threshold = DEFAULT_SETTINGS['threshold']
        self.exclude_manager = ExcludeList(APP_NAME, default_list=['memcompression', 'svchost.exe'])
        self.excludes: list = self.exclude_manager.load()

        # トップ3キャッシュ用のリスト（(プロセス名, メモリMB) のタプルを保持）
        self.top_3_cache = []

        image = Image.open(resource_path('Assets/sample.ico'))

        self.load_config()

        self.version = get_version()
        self.title = f'{APP_NAME} {self.version}'
        menu = Menu(*self.build_menu())
        self.app = Icon(
            name=APP_NAME,
            title=self.title,
            icon=image,
            menu=menu,
        )

    def load_config(self):
        try:
            setting = Setting(**self.config.load())
            self.interval = setting.interval
            self.threshold = setting.threshold
        except Exception:
            pass

    def save_config(self):
        setting = Setting(
            interval=self.interval,
            threshold=self.threshold,
        )
        self.config.save(asdict(setting))

    def build_menu(self):
        interval_submenu = []
        for interval in [5, 30, 60]:
            interval_submenu.append(
                MenuItem(
                    f'{interval}',
                    self.set_interval,
                    checked=lambda x: self.interval == int(str(x))
                ),
            )
        threshold_submenu = []
        for th in range(256, 2048 + 1, 256):
            threshold_submenu.append(
                MenuItem(
                    f'{th} MB',
                    self.set_threshold,
                    checked=lambda x: self.threshold == int(str(x).split()[0])
                ),
            )
        items = [
            MenuItem('Interval', Menu(*interval_submenu)),
            MenuItem('Threshold', Menu(*threshold_submenu)),
            Menu.SEPARATOR,
        ]

        # lambdaを使わず、明示的な関数を作成してクロージャの罠を回避する
        def make_exclude_action(process_name):
            def action(icon, item):
                self.exclude_manager.add(process_name)
            return action

        # キャッシュからトップ3プロセスを追加。クリックで除外リストに追加するアクションを設定
        for name, rss in self.top_3_cache:
            items.append(MenuItem(f"Exclude {name} ({rss:.1f} MB)", make_exclude_action(name)))

        if items:
            items.append(Menu.SEPARATOR)
        items.append(MenuItem(f'Exit {self.title}', self.stopApp))
        return items

    def set_interval(self, _, item):
        # item: MenuItem('30')
        interval = int(str(item))
        self.interval = interval
        self.save_config()
        self.restart_monitor(f'set interval to {interval}')

    def set_threshold(self, _, item):
        # item: MenuItem('256 MB')
        threshold = int(str(item).split()[0])
        self.threshold = threshold
        self.save_config()
        self.restart_monitor(f'set threshold to {threshold}')

    def doMonitor(self):
        while not self.stop_monitor_event.is_set():
            begin = time.time()

            self.load_config()
            ign_list = self.exclude_manager.load()

            prcs = get_proc_mems()

            lines = []
            top_3 = []

            # メモリ使用量順にソートして、除外されていない上位3つをキャッシュ用に抽出
            sorted_prcs = sorted(prcs.items(), key=lambda item: item[1], reverse=True)
            for name, mem in sorted_prcs:
                if name not in ign_list:
                    rss = mem / (1024 * 1024)
                    if rss >= self.threshold:
                        lines.append(f'{rss:>8.2f} {name}')

                        if len(top_3) < 3:
                            top_3.append((name, rss))

            print('\033[2J\033[H', end='')
            print('\n'.join(lines))

            self.top_3_cache = top_3
            self.app.menu = Menu(*self.build_menu())

            elapsed = time.time() - begin
            sleep_time = max(0, self.interval - elapsed)
            if self.stop_monitor_event.wait(sleep_time):
                break

    def restart_monitor(self, reason=None):
        if reason:
            print(reason)
        self.stop_monitor_event.set()
        time.sleep(1)
        self.stop_monitor_event.clear()
        threading.Thread(target=self.doMonitor).start()

    def stopApp(self):
        self.stop_monitor_event.set()
        self.app.stop()

    def runApp(self):
        self.stop_monitor_event.clear()
        self.restart_monitor()
        self.app.run()


if __name__ == '__main__':
    TaskTray().runApp()
