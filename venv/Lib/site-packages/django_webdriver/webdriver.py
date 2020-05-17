import os
import types 
import sys
import urllib2 

from abc import ABCMeta, abstractmethod

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from django_webdriver.message import Message


class WebdriverError(object):
    @staticmethod
    def exception_error_exist(name):
        msg = "\r The browser {name} is not correctly installed"\
                " in this computer \r".format(name=name)
        return Message.build_error(msg)

    @staticmethod
    def message_not_supported(name):
        msg = "\r The webdriver {name} is not supported."\
                    " Respect the case of the name."\
                    " (Chrome, Ie ...) \r".format(name=name)
        return Message.build_error(msg)



class RemoteWebdriver(object):

    separator = "_"

    @classmethod
    def create(cls, webdriver_serialize, url_provider, *args, **kwargs):
        capabilitie = cls._deserialize_webdriver_datas(webdriver_serialize)
        try:
            wd = webdriver.Remote(command_executor=url_provider,
                        desired_capabilities=capabilitie)
        except (urllib2.URLError,WebDriverException), e:
            raise Exception(Message.build_error(e))
        return wd

    @staticmethod
    def serialize_capabilitie(capabilitie, *args, **kwargs):
        if capabilitie.get('browser'):
            name = capabilitie['browser']
            if capabilitie.get('platform'):
                name += "{separator}{platform}".format(
                                platform=capabilitie['platform'],
                                separator=RemoteWebdriver.separator)
            if capabilitie.get('version'):
                name += "{separator}V{version}".format(
                                version=capabilitie['version'],
                                separator=RemoteWebdriver.separator
                                )
            return name
        else:
            print Message.build_error("You have to define the "\
                    " browser_name in all the capabilities of the set.")
            exit(1)

    @staticmethod
    def _deserialize_webdriver_datas(str, *args, **kwargs):
        datas = str.split(RemoteWebdriver.separator)
        response = {}
        response['browserName'] = datas[0]

        if len(datas) > 1:
            if not datas[1].startswith('V'):
                response['os'] = datas[1]
                if len(datas)>2:
                    response['version'] = datas[2][1:]
            else:
                response['version'] = datas[1][1:]

        return response


class LocalWebdriver(object):
    @staticmethod
    def _init_local_webdriver(wd, name, *args, **kwargs):
        try:
            return wd()
        except Exception:
            raise AssertionError(WebdriverError.exception_error_exist(name))

    @staticmethod
    def check_webdriver_exist(name, *args, **kwargs):
        res = True
        wd = None
        if(hasattr(webdriver, name)):
            wd = getattr(webdriver,  name)
        
        if type(wd) != types.TypeType:
            print(WebdriverError.message_not_supported(name))
            res = False

        return res
            

    @classmethod
    def create(cls, name, *args, **kwargs):
        wd = getattr(webdriver,  name)
        return cls._init_local_webdriver(wd, name)