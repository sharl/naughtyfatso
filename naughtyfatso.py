# -*- coding: utf-8 -*-
from dataclasses import asdict, dataclass
import ctypes
import gc
import threading
import time

from PIL import Image, ImageEnhance
from psutil import virtual_memory
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
        self.monitor_thread = None
        self.config = Config(APP_NAME)
        self.interval = DEFAULT_SETTINGS['interval']
        self.threshold = DEFAULT_SETTINGS['threshold']
        exclude_defaults = [
            APP_NAME.lower() + '.exe',
            'memcompression',
            'svchost.exe'
        ]
        self.exclude_manager = ExcludeList(APP_NAME, default_list=exclude_defaults)
        self.excludes: list = self.exclude_manager.load()

        self.stop_naughty_event = threading.Event()
        self.lock = threading.Lock()

        # トップ3キャッシュ用のリスト（(プロセス名, メモリMB) のタプルを保持）
        self.top_3_cache = []

        self.icon_image = Image.open(resource_path('Assets/sample.ico'))
        self.dimm_image = ImageEnhance.Brightness(self.icon_image).enhance(0.5).convert('L')

        self.load_config()

        self.version = get_version()
        self.title = f'{APP_NAME} {self.version}'
        menu = Menu(*self.build_menu())
        self.app = Icon(
            name=APP_NAME,
            title=self.title,
            icon=self.icon_image,
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
            MenuItem(self.title, self.on_icon_clicked, default=True, visible=True),
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
        items.append(MenuItem('Exit', self.stopApp))
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

    def on_icon_clicked(self):
        if self.lock.acquire(blocking=False):
            threading.Thread(target=self.beNaughty, daemon=True).start()
        else:
            self.stop_naughty_event.set()

    def beNaughty(self):
        self.stop_naughty_event.clear()

        # 16GB未満は 300MB
        MAX_CHUNK_SIZE = 300 * 1024 * 1024
        max_chunk_size = MAX_CHUNK_SIZE
        # 上限の決定
        t = virtual_memory().total
        if t > 31 * 1024 * 1024 * 1024:                 # 31GB以上
            max_chunk_size = 1.5 * 1024 * 1024 * 1024   # 上限1.5GB
        elif t > 15 * 1024 * 1024 * 1024:               # 15GB以上
            max_chunk_size = 700 * 1024 * 1024          # 上限700MB

        hog = []
        try:
            while not self.stop_naughty_event.is_set():
                m = virtual_memory()
                t = m.total
                u = m.used
                p = 100 * u / t
                if p >= 98.0:
                    break

                chunk_size = min(max_chunk_size, (t - u) / 2)
                chunk_size = max(chunk_size, MAX_CHUNK_SIZE)

                print(f'{p:.2f} {int(chunk_size / 1024 / 1024)} MB')
                hog.append(b'x' * int(chunk_size))

                if self.stop_naughty_event.wait(timeout=0.01):
                    break

            # induce swap out safely
            if not self.stop_naughty_event.is_set():
                self.stop_naughty_event.wait(timeout=3.0)

        finally:
            hog.clear()
            del hog
            gc.collect()
            self.lock.release()

        self.restart_monitor('gobbled up')

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
            if self.top_3_cache:
                self.app.icon = self.icon_image
            else:
                self.app.icon = self.dimm_image
            self.app.menu = Menu(*self.build_menu())

            elapsed = time.time() - begin
            sleep_time = max(0, self.interval - elapsed)
            if self.stop_monitor_event.wait(sleep_time):
                break

    def _start_monitor(self):
        self.stop_monitor_event.clear()
        self.monitor_thread = threading.Thread(target=self.doMonitor, daemon=True)
        self.monitor_thread.start()

    def _stop_monitor(self):
        self.stop_monitor_event.set()
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            self.monitor_thread.join()

    def restart_monitor(self, reason=None):
        if reason:
            print(reason)
        self._stop_monitor()
        self._start_monitor()

    def stopApp(self):
        self._stop_monitor()
        self.app.stop()

    def runApp(self):
        self._start_monitor()
        self.app.run()


if __name__ == '__main__':
    TaskTray().runApp()
