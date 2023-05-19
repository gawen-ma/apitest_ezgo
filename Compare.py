# coding=utf-8
import json
import logging
import jsonpath
from apitest_ezgo.compat import str, builtin_str
from datetime import datetime, date
from deepdiff import DeepDiff
from tabulate import tabulate


def compare_json(json1, json2, exclude_paths=None, significant_digits=4, format_value=True, **kwargs):
    """
        对比组件
    :param json1: 实际结果
    :param json2: 期望结果
    :param exclude_paths: 不进行比对，需要排除的字段jsonpath，多个自动使用列表或者 英文逗号分割的字符串。例如： $.data.result /  ["$.data.result", "$.data.msg"]
    :param significant_digits: 数字对比保留小数位数，默认为4
    :param format_value: 是否需要格式化处理字典value，如自动将Unicode字符str化，数值统一保留小数，保留小数依赖significant_digits参数
    :param kwargs: 其他参数
    """
    if format_value:
        values_format(json1, significant_digits)
        values_format(json2, significant_digits)
    exclude_paths = set(jpath2path(json1, exclude_paths) + jpath2path(json2, exclude_paths)) if exclude_paths else set()
    res = DeepDiff(json1, json2,
                   significant_digits=significant_digits,
                   exclude_paths=exclude_paths,
                   verbose_level=1,
                   view='tree', **kwargs)
    table_log_result(res)


def jpath2path(json_obj, japths):
    """
    将jsonpath转化为path，例如： $.data.result---> root['data']['result']
    @param json_obj:
    @param japths:
    @return: path
    """
    if isinstance(japths, str):
        japths = japths.split(",")
    elif isinstance(japths, set):
        japths = list(japths)
    elif not isinstance(japths, (list, tuple)):
        logging.warning(u"jsonpath 参数格式不正确，多个使用列表，元组，或可使用英文逗号分割的字符串")
    paths = []
    for jpath in japths:
        _paths = jsonpath.jsonpath(json_obj, jpath.strip(), result_type='PATH')
        if not _paths:
            # logging.warning(u"使用jsonpath: {jpath} 无法中获取到值，请检查jsonpath是否正确! json对象: {json_obj} ".
            #                 format(jpath=jpath, json_obj=json.dumps(json_obj, ensure_ascii=False)))
            continue
        paths.extend([path.replace("$", "root") for path in _paths])
    return paths


def table_log_result(diff_res):
    """
    以表格形式打印对比结果
    @param diff_res: deepdiff结果
    @return: 无
    """
    if diff_res:
        header = ["type", "old", "new", "details"]
        diff_values = []
        for item in diff_res.items():
            for i in item:
                if not isinstance(i, str):
                    for ele in list(i):
                        diff_values.append([ele.report_type, ele.t1, ele.t2, ele])
        logging.warning(tabulate(diff_values, headers=header, tablefmt='grid'))
        raise ValueError("结果比对失败")


def values_format(obj, significant_digits):
    if isinstance(obj, (list, set)):
        for item in obj:
            values_format(item, significant_digits)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if v in ("", None):
                obj[k] = ""
            elif isinstance(v, str):
                try:
                    v = json.loads(v)
                    obj[k] = values_format(v, significant_digits)
                except Exception:
                    obj[k] = builtin_str(v)
            elif isinstance(v, (int, float)):
                obj[k] = round(v, significant_digits)
            elif isinstance(v, (datetime, date)):
                obj[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            else:
                obj[k] = values_format(v, significant_digits)
    return obj


if __name__ == '__main__':
    json1 = {
        "url": "https://miao.baidu.com/abdr",
        "headers": {
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "User-Agent": "new agent",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-ch-ua-mobile": "?0",
            "Content-Type": u"text/plain;charset=UTF-8",
            "Sec-Fetch-Dest": "empty"
        },
        "params": {
            "_o": "https%3A%2F%2Ffanyi.baidu.com"
        },
        "method": "POST",
        "data": {"a": 3.14159, "b": {"c": "2"}, "d": 1234, "e": []}
    }

    json2 = {
        "url": "https://miao.baidu.com/abdr",
        "headers": {
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "User-Agent": "new agent",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-ch-ua-mobile": "?0",
            "Content-Type": u"text/plain;charset=UTF-8",
            "sec-ch-ua": None,
            "Sec-Fetch-Dest": "empty"
        },
        "params": {
            "_o": "https%3A%2F%2Ffanyi.baidu.com"
        },
        "method": "POST",
        "data": {"a": 3.141592, "b": {"c": [2, 3]}, "d": "1234"},
        "test1": """{"aa":11, "bb":22}"""
    }
    compare_json(json1, json2, exclude_paths="$.data.b.c")
    # values_format(json2, 2)
    # print json.dumps(json2)
