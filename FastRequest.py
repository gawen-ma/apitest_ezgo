# coding:utf-8
"""
@date: 2023/2/9
@author: mawengang
"""

import logging
import os
import json
import random
import requests
import jsonpath_ng
from apitest_ezgo.compat import *
from jsonpath import jsonpath
from requests.adapters import HTTPAdapter
from requests_toolbelt import MultipartEncoder


def update_req_info(replace_dict, req_info):
    """
    需要更新请求参数，传入对应jpath 和 值，如果需要将某个参数从请求中删除，将值更新为{REMOVE}
    例如{"$.headers.User-Agent": "new agent", "$..sec-ch-ua": '{REMOVE}'}

    @replace_dict: 需要变更的组装字典，KEY为jsonpath，value为需要替换的新值，如{"$.headers.User-Agent": "new agent"}
    @req_info: 原始请求参数
    """
    if not isinstance(replace_dict, dict):
        logging.error(u"jsonpath 格式输入不合法")
        raise u"jsonpath 格式输入不合法: %s" % replace_dict

    # 更新请求参数
    for k, v in replace_dict.items():
        parser = jsonpath_ng.parse(k)
        parser.update_or_create(req_info, v)

    # 删除请求参数为{REMOVE}的
    parser = jsonpath_ng.parse("$..*")
    parser.filter(lambda x: x == '{REMOVE}', req_info)


def load_req_info(file_path):
    if is_py3:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if is_py2:
        with open(file_path, "r") as f:
            return json.load(f)

def get_multipart_data(data):
    """
    处理multipart/form-data参数
    :param data:请求内容 data格式：{"param1": "param1_value", # 其他非文件参数
                                "param2": "param2_value",
                                "file":("文件名称", 文件内容,用open读出来, "文件类型") # 这是要上传的文件信息，key必须为"file",value为元组
                                }
                                示例:
                                {"id": 2, "name": "auto_test",
                                "file": ("standard_2_7228.xlsx", open(r"standard_2_7228.xlsx", "rb"),
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    :return: 处理好的请求体和content_type
    """
    form_data = MultipartEncoder(data)  # 格式转换
    return form_data, form_data.content_type


class FastRequest(object):
    def __init__(self, template_path="", base_url="", session=None):
        """
        Http对象
        @param template_path: json请求模板文件根目录
        @param base_url：服务基础路径，例如： https:www.baidu.com/
        @param session: http session
        """
        self.session = session if session else requests.session()
        self.template_path = template_path
        self.base_url = base_url

        # http适配器，自动重试次数3
        adapter = HTTPAdapter(max_retries=3, pool_connections=3, pool_maxsize=5)
        # http和https都适用适配器
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        # @TODO session管理器

    def fast_request(self, request_name, file_path='', resp_jpath=None, session=None, index=0, **replace_dict):
        """
        支持各类请求方式各类content-type的请求入口
        @param file_path: json文件路径，可为相对于template_path的相对路径，不传时template_path需要到文件
        @param request_name: json文件中请求的名称，即字典名称
        @param resp_jpath: 需要提取响应数据的jsonpath
        @param session: 支持临时session请求，不传默认使用实例session
        @param index: 返回数据的索引，默认为0， 只能传入数字、random 或None； random表示从列表中随机抽取一个，None表示返回完整列表
        @param replace_dict:需要更新请求参数，传入对应jpath 和 值，如果需要将某个参数从请求中删除，将值更新为{REMOVE}
                            例如{"$.headers.User-Agent": "new agent", "$..sec-ch-ua": '{REMOVE}'}
        @return: 传入resp_jpath取对应数据，默认返回响应对象
        """
        path = os.path.join(self.template_path, file_path) if (self.template_path and file_path) \
            else (file_path if file_path else self.template_path)
        req_info = load_req_info(path).get(request_name)
        replace_dict = replace_dict if replace_dict else {}
        if self.base_url:
            if self.base_url.endswith("/"):
                self.base_url = self.base_url[:-1]
            replace_dict.update({"$.host": self.base_url})
        update_req_info(replace_dict, req_info)
        url = req_info.get("host") + req_info.get("path")
        req_info.pop("host")
        req_info.pop("path")
        if "multipart/form-data; boundary=" in req_info['headers']['Content-Type']:
            data, content_type = get_multipart_data(req_info['data'])
            multipart_data = {
                "$.data": data,
                "$.headers.Content-Type": content_type
            }
            update_req_info(multipart_data, req_info)
        # 支持临时session请求，默认使用实例session
        logging.info(u"请求信息：\n %s" % req_info)
        if session:
            resp = session.request(url=url, **req_info)
        else:
            resp = self.session.request(url=url, **req_info)
        msg = u"请求status_code： %s" % resp.status_code
        logging.info(msg) if resp.status_code == 200 else logging.warning(msg)
        if resp_jpath:
            if index is None:
                return jsonpath(resp.json(), resp_jpath)
            elif str(index).lower() == 'random':
                return random.choice(jsonpath(resp.json(), resp_jpath))
            elif isinstance(index, int):
                return jsonpath(resp.json(), resp_jpath)[index]
            else:
                raise ValueError("index 参数只能为 None、 random 或 整数数字")
        else:
            return resp
