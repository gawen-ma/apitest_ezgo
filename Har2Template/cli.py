# coding=utf-8
""" Convert HAR (HTTP Archive) to YAML/JSON template for HttpRunner.

"""
import argparse
import logging
import sys

from apitest_ezgo.__about__ import __description__, __version__

from apitest_ezgo.Har2Template.core import HarParser


def get_version():
    return __version__


def main():
    """ HAR converter: parse command line options and run commands.
    """
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument('-v', '--version', action='version', version=get_version(), help='show version')

    subparsers = parser.add_subparsers(help="")
    sub_parser = subparsers.add_parser("new", help=u"""usage: NSFastHttp  [-s] har_source_file  [-d] dest_file_path
                                            egg: NSFastHttp new demo.har .
                                            har_source_file： har文件所在路径,当前路径下的demo.har;
                                            dest_file_path: 目的文件路径，.表示当前路径""")
    sub_parser.add_argument("-s", "--source", dest="har_source_file", help=u"har_source_file： har文件所在路径")
    sub_parser.add_argument("-d", "--dest", dest="dest_file_path", default=".",
                            help=u"dest_file_path： 目的文件路径，默认har所在路径")

    args = parser.parse_args()
    # print (args)

    har_source_file = args.har_source_file
    if not har_source_file or not har_source_file.endswith(".har"):
        logging.error("HAR file not specified.")
        sys.exit(1)
    print args

    HarParser(
        har_source_file, args.dest_file_path
    ).gen_template()
    return 0

def test(har_source_file, dest_file_path):
    HarParser(
        har_source_file, dest_file_path
    ).gen_template()


if __name__ == '__main__':
    test(r"C:\Users\nsfocus\Desktop\units.har", ".")