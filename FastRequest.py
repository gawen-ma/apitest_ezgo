# coding:utf-8
"""
@date: 2023/2/9
@author: mawengang
"""

import logging
import os
import json
import requests
import jsonpath_ng
from jsonpath import jsonpath
from requests.adapters import HTTPAdapter


def update_req_info(replace_dict, req_info):
    """
    需要更新请求参数，传入对应jpath 和 值，如果需要将某个参数从请求中删除，将值更新为{REMOVE}
    例如{"$.headers.User-Agent": "new agent", "$..sec-ch-ua": '{REMOVE}'}

    @replace_dict: 需要变更的组装字典，KEY为jsonpath，value为需要替换的新值，如{"$.headers.User-Agent": "new agent"}
    @req_info: 原始请求参数
    """
    if not isinstance(replace_dict, dict):
        logging.error("jsonpath 格式输入不合法")
        raise "jsonpath 格式输入不合法: %s" % replace_dict

    # 更新请求参数
    for k, v in replace_dict.items():
        parser = jsonpath_ng.parse(k)
        parser.update_or_create(req_info, v)
    print ("after update %s" % json.dumps(req_info))

    # 删除请求参数为{REMOVE}的
    parser = jsonpath_ng.parse("$..*")
    parser.filter(lambda x: x == '{REMOVE}', req_info)


def load_req_info(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


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

    def fast_request(self, file_path, request_name, resp_jpath=None, session=None, replace_dict=None):
        """
        支持各类请求方式各类content-type的请求入口
        @param file_path: json文件路径，可为相对于template_path的相对路径
        @param request_name: json文件中请求的名称，即字典名称
        @param resp_jpath: 需要提取响应数据的jsonpath
        @param session: 支持临时session请求，不传默认使用实例session
        @param replace_dict:需要更新请求参数，传入对应jpath 和 值，如果需要将某个参数从请求中删除，将值更新为{REMOVE}
                            例如{"$.headers.User-Agent": "new agent", "$..sec-ch-ua": '{REMOVE}'}
        @return: 传入resp_jpath取对应数据，默认返回响应对象
        """
        path = os.path.join(self.template_path, file_path) if self.template_path else file_path
        req_info = load_req_info(path).get(request_name)
        replace_dict = replace_dict if replace_dict else {}
        if self.base_url:
            replace_dict.update({"$.host": self.base_url})
        update_req_info(replace_dict, req_info)
        url = req_info.get("host") + req_info.get("path")
        req_info.pop("host")
        req_info.pop("path")
        # 支持临时session请求，默认使用实例session
        if session:
            resp = session.request(url=url, **req_info)
        else:
            resp = self.session.request(url=url, **req_info)
        return jsonpath(resp.json(), resp_jpath)[0] if resp_jpath else resp


