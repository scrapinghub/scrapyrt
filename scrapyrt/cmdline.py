# -*- coding: utf-8 -*-
from six.moves.configparser import (
    SafeConfigParser, NoOptionError, NoSectionError
)
import argparse
import os
import sys

from scrapy.utils.conf import closest_scrapy_cfg
from scrapy.utils.misc import load_object
from twisted.application import app
from twisted.application.internet import TCPServer
from twisted.application.service import Application
from twisted.internet import reactor
from twisted.web.server import Site

from .log import setup_logging
from .conf import settings


def parse_arguments():

    def valid_setting(string):
        key, sep, value = string.partition('=')
        if not key or not sep:
            raise argparse.ArgumentTypeError(
                u'expected name=value: {}'.format(repr(string)))
        return key, value

    parser = argparse.ArgumentParser(
        description='HTTP API server for Scrapy project.')
    parser.add_argument('-p', '--port', dest='port',
                        type=int,
                        default=9080,
                        help='port number to listen on')
    parser.add_argument('-i', '--ip', dest='ip',
                        default='localhost',
                        help='IP address the server will listen on')
    parser.add_argument('--project', dest='project',
                        default='default',
                        help='project name from scrapy.cfg')
    parser.add_argument('-s', '--set', dest='set',
                        type=valid_setting,
                        action='append',
                        default=[],
                        metavar='name=value',
                        help='set/override setting (may be repeated)')
    parser.add_argument('-S', '--settings', dest='settings',
                        metavar='project.settings',
                        help='custom project settings module path')
    return parser.parse_args()


def get_application(arguments):
    ServiceRoot = load_object(settings.SERVICE_ROOT)
    site = Site(ServiceRoot())
    application = Application('scrapyrt')
    server = TCPServer(arguments.port, site, interface=arguments.ip)
    server.setServiceParent(application)
    return application


def find_scrapy_project(project):
    project_config_path = closest_scrapy_cfg()
    if not project_config_path:
        raise RuntimeError('Cannot find scrapy.cfg file')
    project_config = SafeConfigParser()
    project_config.read(project_config_path)
    try:
        project_settings = project_config.get('settings', project)
    except (NoSectionError, NoOptionError) as e:
        raise RuntimeError(e.message)
    if not project_settings:
        raise RuntimeError('Cannot find scrapy project settings')
    project_location = os.path.dirname(project_config_path)
    sys.path.append(project_location)
    return project_settings


def execute():
    sys.path.insert(0, os.getcwd())
    arguments = parse_arguments()
    if arguments.settings:
        settings.setmodule(arguments.settings)
    if arguments.set:
        for name, value in arguments.set:
            settings.set(name.upper(), value)
    settings.set('PROJECT_SETTINGS', find_scrapy_project(arguments.project))
    settings.freeze()
    setup_logging()
    application = get_application(arguments)
    app.startApplication(application, save=False)
    reactor.run()


if __name__ == '__main__':
    execute()
