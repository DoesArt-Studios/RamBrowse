import os

from django.conf import settings as s

from django_webdriver.message import Message
from django_webdriver.webdriver import LocalWebdriver, RemoteWebdriver


class Environment(object):

    webdrivers_errors = []

    @staticmethod
    def _get_capabilities(provider, settings):
        if(settings.get('remote_capabilities')):
            all_capabilities = settings['remote_capabilities']
            capabilitie_name = provider['capabilities'] if provider.get('capabilities') else 'default'
            if(all_capabilities.get(capabilitie_name)):
                return all_capabilities[capabilitie_name]
            else:
                print(Message.build_error("The value '{value}' that is defined"\
                     " in the settings.py to select the capabilities of"\
                     " the provider '{name}' doesn't"\
                     " exist in your remote capabilities.").format(
                                    value=capabilitie_name,
                                    name=os.environ['DJANGO_NOSE_REMOTE']
                                    )
                )
                exit(1)
        else:
            print(Message.build_error("You have to define capabilities in"\
                                " the settings.py file to use remote mode."))
            exit(1)

    @staticmethod
    def _get_provider(settings):
        providers = settings['remote_providers']
        provider_name = os.environ['DJANGO_NOSE_REMOTE']
        if settings['remote_providers'].get(provider_name):
            providers = settings['remote_providers']
            return providers[provider_name]
        else:
            print(Message.build_error("The name {name} is not defined in"\
                                    " your remote_providers in the"
                                    " settings.py".format(name=provider_name)))
            exit(1)

    @classmethod
    def _get_url_provider(cls):
        provider = cls._get_provider()
        if provider.get('url'):
            return provider['url']
        else:
            print(Message.build_error("You have to define an url to request"\
                        " this provider."))
            exit(1)

    @staticmethod
    def _get_remote_drivers(capabilities):
        webdrivers = []
        for capabilitie in capabilities:
            webdriver = RemoteWebdriver.serialize_capabilitie(capabilitie)
            webdrivers.append(webdriver)

        return webdrivers

    @staticmethod
    def _get_local_drivers():
        wds = os.environ['DJANGO_NOSE_WEBDRIVER'].split(',')
        webdrivers = []
        for wd in wds:
            if wd not in Environment.webdrivers_errors:
                if LocalWebdriver.check_webdriver_exist(wd):
                    webdrivers.append(wd)
                else:
                    Environment.webdrivers_errors.append(wd)
        return webdrivers

    @classmethod
    def get_webdrivers(cls, *args, **kwargs):
        '''
            This method is used to build a list with the webdrivers.
            If one webdriver is not supported by Selenium an error message
            is displayed.
        '''

        webdrivers = []
        if os.environ.get('DJANGO_NOSE_REMOTE'):
            settings =  s.DJANGO_WEBDRIVER_SETTINGS
            provider = cls._get_provider(settings)
            capabilities = cls._get_capabilities(provider, settings)
            webdrivers = cls._get_remote_drivers(capabilities)
        else:
            webdrivers = cls._get_local_drivers()

        return webdrivers

    @classmethod
    def init_webdriver(cls, webdriver, *args, **kwargs):
        '''
            This method init one webdriver that will be used in one test method.
        '''
        wd = None
        if os.environ.get('DJANGO_NOSE_REMOTE'):
            url = cls._get_url_provider()
            wd = RemoteWebdriver.create(webdriver, url, *args, **kwargs)
        else: 
            wd = LocalWebdriver.create(webdriver, *args, **kwargs)
        return wd
