#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2016,2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Deletes unneeded DLLs and checks DLL dependencies.

Execute with the build python, will figure out the rest.
"""

import logging
import os
import subprocess
import sys
from functools import cache
from multiprocessing import Process, Queue

import gi  # isort:skip

girepository_version = 0
try:
    gi.require_version("GIRepository", "3.0")  # isort:skip
    girepository_version = 3
except ValueError as e:
    try:
        gi.require_version("GIRepository", "2.0")  # isort:skip
        girepository_version = 2
    except ValueError as e:
        # let it crash
        raise Exception("GIRepository version is not 3 or 2")

from gi.repository import GIRepository  # isort:skip


def _get_shared_libraries(q, namespace, version, loglevel=logging.WARNING):
    """put a list of libraries into q, regardless of girepository_version."""
    import multiprocessing
    logger = multiprocessing.log_to_stderr(level=loglevel)

    repo = GIRepository.Repository()
    try:
        repo.require(namespace, version, 0)
        if girepository_version == 3:
            libs = repo.get_shared_libraries(namespace)
            logger.debug("repo.get_share_libraries(%s) returned: %s", namespace, libs)
        elif girepository_version == 2:
            ret = repo.get_shared_library(namespace)
            logger.debug("repo.get_share_library(%s) returned: %s", namespace, ret)
            if ret:
                libs = ret.split(',')
            else:
                libs = []

        q.put(libs)
    except Exception as e:
        logger.exception(e)
        q.put([])


@cache
def get_shared_libraries(namespace, version):
    """Return a list of libraries."""
    # we have to start a new process because multiple versions can't be loaded
    # in the same process
    loglevel = logging.getLogger().getEffectiveLevel()
    q = Queue()
    p = Process(target=_get_shared_libraries, args=(q, namespace, version, loglevel))
    p.start()
    result = q.get()
    p.join()
    return result


def get_required_by_typelibs():
    deps = set()
    repo = GIRepository.Repository()
    for tl in os.listdir(repo.get_search_path()[0]):
        namespace, version = os.path.splitext(tl)[0].split("-", 1)
        logging.debug(f"get_require_by_typelibs(): calling get_shared_libraries({namespace}, {version})")
        libs = get_shared_libraries(namespace, version)
        for lib in libs:
            deps.add((namespace, version, lib.lower()))
    return deps


@cache
def get_dependencies(filename):
    deps = []
    try:
        data = subprocess.check_output(["objdump", "-p", filename],
                                       stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        # can happen with wrong arch binaries
        return []
    data = data.decode("utf-8")
    for line in data.splitlines():
        line = line.strip()
        if line.startswith("DLL Name:"):
            deps.append(line.split(":", 1)[-1].strip().lower())
    logging.debug(f"get_dependencies({filename}): returning: {deps}")
    return deps


def find_lib(root, name):
    system_search_path = os.path.join("C:", os.sep, "Windows", "System32")
    if get_lib_path(root, name):
        return True
    elif os.path.exists(os.path.join(system_search_path, name)):
        return True
    elif name in ["gdiplus.dll"]:
        return True
    elif name.startswith("msvcr"):
        return True
    elif name.startswith("api-ms-win-"):
        return True
    return False


def get_lib_path(root, name):
    search_path = os.path.join(root, "bin")
    if os.path.exists(os.path.join(search_path, name)):
        return os.path.join(search_path, name)


def get_things_to_delete(root):
    logging.debug(f"get_things_to_delete(root):\n root: {root}")
    extensions = [".exe", ".pyd", ".dll"]

    all_libs = set()
    needed = set()
    for base, dirs, files in os.walk(root):
        for f in files:
            lib = f.lower()
            path = os.path.join(base, f)
            ext_lower = os.path.splitext(f)[-1].lower()
            if ext_lower in extensions:
                if ext_lower == ".exe":
                    # we use .exe as dependency root
                    needed.add(lib)
                    logging.debug(f"{lib} added to needed set")
                all_libs.add(f.lower())
                logging.debug(f"{f.lower()} added to all_libs set")
                for lib in get_dependencies(path):
                    all_libs.add(lib)
                    logging.debug(f"{lib} added to all_libs set")
                    needed.add(lib)
                    logging.debug(f"{lib} added to needed set")
                    if not find_lib(root, lib):
                        print("MISSING:", path, lib)

    for namespace, version, lib in get_required_by_typelibs():
        all_libs.add(lib)
        needed.add(lib)
        if not find_lib(root, lib):
            print("MISSING:", namespace, version, lib)

    to_delete = []
    for not_depended_on in (all_libs - needed):
        path = get_lib_path(root, not_depended_on)
        if path:
            to_delete.append(path)

    logging.debug(f"returning to_delete: {to_delete}")
    return to_delete


def main(argv):
    if "--debug" in argv[1:]:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.debug("GIRepository being used: %s", girepository_version)
    libs = get_things_to_delete(sys.prefix)

    if "--delete" in argv[1:]:
        while libs:
            for lib in libs:
                print("DELETE:", lib)
                os.unlink(lib)
            libs = get_things_to_delete(sys.prefix)


if __name__ == "__main__":
    main(sys.argv)
