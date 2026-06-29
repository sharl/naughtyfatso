# -*- coding: utf-8 -*-
import ctypes
import threading
import time

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import darkdetect as dd

from get_proc_mems import get_proc_mems
from utils import resource_path

APP_NAME = 'NaughtyFatso'

INTERVAL = 30
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

        self.monitor_interval = INTERVAL
        self.threshold = 256
        self.IGN_LIST = [
            'memcompression',
            'svchost.exe',
        ]

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

            prcs = get_proc_mems()

            lines = []
            for name in sorted(prcs, key=lambda n: prcs[n], reverse=True):
                if name not in self.IGN_LIST:
                    rss = prcs[name] / (1024 * 1024)
                    if rss >= self.threshold:
                        lines.append(f'{rss:>8.2f} {name}')

            print('\033[2J\033[H', end='')
            print('\n'.join(lines))

            elapsed = time.time() - begin
            sleep_time = max(0, self.monitor_interval - elapsed)
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
