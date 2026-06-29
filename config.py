# -*- coding: utf-8 -*-
from pathlib import Path
import json
import os
import sys


class Config:
    def __init__(self, APP_NAME: str, name: str = 'config.json'):
        base_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        self.path = base_dir / APP_NAME / name

    def load(self) -> dict:
        try:
            with open(self.path, mode='r', encoding='utf-8') as fd:
                return json.load(fd)
        except Exception:
            return {}

    def save(self, data: dict) -> int:
        """
        return
        0: success
        -1: error
        """
        dirname = os.path.dirname(self.path)
        os.makedirs(dirname, exist_ok=True)

        try:
            with open(self.path, mode='w', encoding='utf-8') as fd:
                fd.write(json.dumps(data, ensure_ascii=False))
                return 0
        except Exception as e:
            print(e, file=sys.stderr)
        return -1


class ExcludeList:
    def __init__(self, APP_NAME: str, name: str = 'list.txt', default_list: list[str] = None):
        base_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        self.path = base_dir / APP_NAME / name
        self.default_list = default_list if default_list is not None else ['memcompression', 'svchost.exe']

    def load(self) -> list[str]:
        if not self.path.exists():
            dirname = os.path.dirname(self.path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            try:
                with open(self.path, mode='w', encoding='utf-8') as fd:
                    fd.write("# デフォルトの除外プロセス一覧\n")
                    for item in self.default_list:
                        fd.write(f"{item}\n")
            except Exception as e:
                print(f"Failed to create default exclude list: {e}", file=sys.stderr)
                return self.default_list.copy()

        try:
            excludes = []
            with open(self.path, mode='r', encoding='utf-8') as fd:
                for line in fd:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    excludes.append(line)
            return excludes
        except Exception as e:
            print(f"Failed to load exclude list: {e}", file=sys.stderr)
            return self.default_list.copy()

    def add(self, process_name: str) -> int:
        process_name = process_name.lower().strip()
        if not process_name:
            return -1

        current_excludes = self.load()
        if process_name in current_excludes:
            return 0  # すでに登録されていれば何もしない

        dirname = os.path.dirname(self.path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        try:
            with open(self.path, mode='a', encoding='utf-8') as fd:
                fd.write(f"{process_name}\n")
            return 0
        except Exception as e:
            print(f"Failed to add process to exclude list: {e}", file=sys.stderr)
        return -1
