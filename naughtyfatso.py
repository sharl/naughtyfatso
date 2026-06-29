# -*- coding: utf-8 -*-
import ctypes
import threading
import time

from PIL import Image, ImageDraw
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
        self.stop_event = threading.Event()

        self.config_manager = Config(APP_NAME)
        self.exclude_manager = ExcludeList(APP_NAME, default_list=['memcompression', 'svchost.exe'])

        image = Image.new('RGB', (64, 64), (45, 45, 45))
        dc = ImageDraw.Draw(image)
        dc.ellipse([2, 2, 62, 62], fill=(255, 127, 0))

        version = get_version()
        title = f'{APP_NAME} {version}'
        main_menu = Menu(
            MenuItem(f'Exit {title}', self.stopApp),
        )
        self.app = Icon(name=APP_NAME, title=title, icon=image, menu=main_menu)

    def doMonitor(self):
        while not self.stop_event.is_set():
            begin = time.time()

            settings = self.config_manager.load()
            if not settings:
                settings = DEFAULT_SETTINGS.copy()
                self.config_manager.save(settings)

            try:
                monitor_interval = float(settings.get('interval', DEFAULT_SETTINGS['interval']))
            except (ValueError, TypeError):
                monitor_interval = float(DEFAULT_SETTINGS['interval'])

            try:
                threshold = float(settings.get('threshold', DEFAULT_SETTINGS['threshold']))
            except (ValueError, TypeError):
                threshold = float(DEFAULT_SETTINGS['threshold'])

            ign_list = self.exclude_manager.load()

            prcs = get_proc_mems()

            lines = []
            for name in sorted(prcs, key=lambda n: prcs[n], reverse=True):
                if name not in ign_list:
                    rss = prcs[name] / (1024 * 1024)
                    if rss >= threshold:
                        lines.append(f'{rss:>8.2f} {name}')

            print('\033[2J\033[H', end='')
            print('\n'.join(lines))

            elapsed = time.time() - begin
            sleep_time = max(0, monitor_interval - elapsed)
            if self.stop_event.wait(sleep_time):
                break

    def stopApp(self):
        self.stop_event.set()
        self.app.stop()

    def runApp(self):
        self.stop_event.clear()

        threading.Thread(target=self.doMonitor).start()

        self.app.run()


if __name__ == '__main__':
    TaskTray().runApp()
