# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import os
import sys

from mo_dots import (
    _set_attr as mo_dots_set_attr,
    _get_attr as mo_dots_get_attr,
    split_field, to_data, startswith_field, relative_field, join_field, NullType, SLOT, KEY)
from mo_imports import delay_import

logger = delay_import("mo_logs.logger")


DEBUG = False


def set(constants):
    """
    REACH INTO THE MODULES AND OBJECTS TO SET CONSTANTS.
    THINK OF THIS AS PRIMITIVE DEPENDENCY INJECTION FOR MODULES.
    USEFUL FOR SETTING DEBUG FLAGS.
    """
    for full_path, new_value in to_data(constants).leaves():
        _set_one(full_path, new_value)


def _set_one(full_path, new_value):
    k_path = split_field(full_path)
    if len(k_path) < 2:
        logger.error("expecting <module>.<constant> format, not {path|quote}", path=k_path)
    candidate = ""
    main_module = None
    for module_path, module in (*sys.modules.items(), get_main_module()):
        if startswith_field(full_path, module_path):
            if len(module_path) > len(candidate):
                candidate = module_path
                main_module = module
    if not candidate:
        logger.error(
            "no module starting with {module|quote}",
            module=full_path,
            stack_depth=2
        )

    # '...AppData.Local.Programs.PyCharm Community.plugins.python-ce.helpers.pycharm._jb_unittest_runner'
    # 'no_exist.VALUE'

    if startswith_field(full_path, candidate):
        k_path = split_field(relative_field(full_path, candidate))
        current_value = mo_dots_get_attr(main_module, k_path)
        if isinstance(current_value, NullType) and not _slot_exists(current_value):
            logger.error(
                "property {path|quote} not found in {module|quote}",
                path=join_field(k_path),
                module=main_module,
                stack_depth=2
            )
        mo_dots_set_attr(main_module, k_path, new_value)


def _slot_exists(null):
    obj = object.__getattribute__(null, SLOT)
    key = object.__getattribute__(null, KEY)
    return hasattr(obj, key)


def get_main_module():
    curr_dir = file_path_as_field(abs_path(os.getcwd()))
    main_module = sys.modules["__main__"]
    if not main_module.__file__.endswith(".py"):
        raise Exception("do not know how to handle non-python main")
    module_path = relative_field(file_path_as_field(abs_path(main_module.__file__)[:-3]), curr_dir)
    if module_path.startswith(".."):
        module_path = "*"  # hopefully no file has this name, todo remove this if block when new mo-dots available
    return module_path, main_module


def abs_path(path):
    return os.path.abspath(path).replace(os.sep, "/").lstrip("/")


def file_path_as_field(file_path):
    return join_field(file_path.split("/"))
