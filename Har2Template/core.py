# coding=utf-8
import base64
import json
import logging
import os
import sys

import utils
from compat import urlparse

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

IGNORE_REQUEST_HEADERS = [
    "host",
    "accept",
    "content-length",
    "connection",
    "accept-encoding",
    "accept-language",
    "origin",
    "referer",
    "cache-control",
    "pragma",
    "cookie",
    "upgrade-insecure-requests",
    ":authority",
    ":method",
    ":scheme",
    ":path"
]


class HarParser(object):

    def __init__(self, har_file_path, dest_file_path, filter_str=None, exclude_str=None):
        self.har_file_path = har_file_path
        self.dest_file_path = dest_file_path
        self.filter_str = filter_str
        self.exclude_str = exclude_str or ""

    def __make_request_url(self, path, requst_dict, entry_json):
        """ parse HAR entry request url and queryString, and make requst url and params

        Args:
            entry_json (dict):
                {
                    "request": {
                        "url": "https://httprunner.top/home?v=1&w=2",
                        "queryString": [
                            {"name": "v", "value": "1"},
                            {"name": "w", "value": "2"}
                        ],
                    },
                    "response": {}
                }

        Returns:
            {
                "name: "/home",
                "/home": {
                    url: "https://httprunner.top/home",
                    params: {"v": "1", "w": "2"}
                }
            }

        """
        request_params = utils.convert_list_to_dict(
            entry_json["request"].get("queryString", [])
        )
        requst_dict[path]["path"] = path
        full_url = entry_json["request"].get("url")
        if not full_url:
            logging.exception("url missed in request.")
            sys.exit(1)

        parsed_object = urlparse.urlparse(full_url)
        if request_params:
            parsed_object = parsed_object._replace(query='')
            url = parsed_object.geturl()
            requst_dict[path]["params"] = request_params
        else:
            url = full_url
        requst_dict[path]["host"] = url.replace(path, "")


    def __make_request_method(self, path, requst_dict, entry_json):
        """ parse HAR entry request method, and make requst method.
        """
        method = entry_json["request"].get("method")
        if not method:
            logging.exception("method missed in request.")
            sys.exit(1)

        requst_dict[path]["method"] = method

    def __make_request_headers(self, path, requst_dict, entry_json):
        """ parse HAR entry request headers, and make requst headers.
            header in IGNORE_REQUEST_HEADERS will be ignored.
        """
        requst_headers = {}
        for header in entry_json["request"].get("headers", []):
            if header["name"].lower() in IGNORE_REQUEST_HEADERS:
                continue

            requst_headers[header["name"]] = header["value"]

        if requst_headers:
            requst_dict[path]["headers"] = requst_headers

    def _make_request_data(self, path, requst_dict, entry_json):
        """ parse HAR entry request data, and make requst request data
        """
        method = entry_json["request"].get("method")
        if method in ["POST", "PUT", "PATCH"]:
            postData = entry_json["request"].get("postData", {})
            mimeType = postData.get("mimeType")

            # Note that text and params fields are mutually exclusive.
            if "text" in postData:
                post_data = postData.get("text")
            else:
                params = postData.get("params", [])
                post_data = utils.convert_list_to_dict(params)

            request_data_key = "data"
            if not mimeType:
                pass
            elif mimeType.startswith("application/json"):
                try:
                    post_data = json.loads(post_data)
                    request_data_key = "json"
                except JSONDecodeError:
                    pass
            elif mimeType.startswith("application/x-www-form-urlencoded"):
                post_data = utils.convert_x_www_form_urlencoded_to_dict(post_data)
            else:
                # TODO: make compatible with more mimeType
                pass

            requst_dict[path][request_data_key] = post_data

    def _prepare_requst(self, entry_json):
        """ extract info from entry dict and make requst
        """
        url = entry_json["request"].get("url")
        if not url:
            logging.exception("url missed in request.")
            sys.exit(1)

        parsed_object = urlparse.urlparse(url)
        path = parsed_object.path
        requst_dict = {
            path: {},
        }
        self.__make_request_url(path, requst_dict, entry_json)
        self.__make_request_method(path, requst_dict, entry_json)
        self.__make_request_headers(path, requst_dict, entry_json)
        self._make_request_data(path, requst_dict, entry_json)

        return requst_dict

    def _prepare_requst_info(self, fmt_version):
        """ make requst list.
            requst_info list are parsed from HAR log entries list.

        """

        requst_info = {}
        log_entries = utils.load_har_log_entries(self.har_file_path)
        for entry_json in log_entries:
            requst_info.update(
                self._prepare_requst(entry_json)
            )

        return requst_info

    def _make_template(self, fmt_version):
        """ Extract info from HAR file and prepare for template
        """
        logging.debug("Extract info from HAR file and prepare for template.")

        requst_info = self._prepare_requst_info(fmt_version)

        return requst_info

    def gen_template(self, file_type="JSON", fmt_version="v1"):
        harfile = os.path.splitext(self.har_file_path)[0]
        output_template_file = os.path.join(self.dest_file_path, "{}.{}".format(harfile, file_type.lower()))

        logging.info("Start to generate template.")
        template = self._make_template(fmt_version)
        logging.debug("prepared template: {}".format(template))

        if file_type == "JSON":
            utils.dump_json(template, output_template_file)
