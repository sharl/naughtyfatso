# -*- coding: utf-8 -*-
from psutil import process_iter, NoSuchProcess, AccessDenied, ZombieProcess


def get_proc_mems() -> list:
    procs = {}

    for proc in process_iter(['name', 'memory_info']):
        try:
            name = proc.name().lower()
            mem = proc.memory_info().rss
            if name not in procs:
                procs[name] = 0
            procs[name] += mem
        except (NoSuchProcess, AccessDenied, ZombieProcess):
            pass

    return procs
