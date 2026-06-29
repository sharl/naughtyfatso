# -*- coding: utf-8 -*-
from psutil import process_iter, NoSuchProcess, AccessDenied, ZombieProcess


def get_proc_mems() -> dict[str, int]:
    procs = {}

    for proc in process_iter(['name', 'memory_info']):
        try:
            name = proc.info['name']
            if name is None:
                continue
            name = name.lower()

            mem_info = proc.info['memory_info']
            if mem_info is None:
                continue
            mem = mem_info.rss

            if name not in procs:
                procs[name] = 0
            procs[name] += mem
        except (NoSuchProcess, AccessDenied, ZombieProcess):
            pass

    return procs
