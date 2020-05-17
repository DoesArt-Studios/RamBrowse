import os
import types
import time

from functools import wraps

from django.test import LiveServerTestCase

from django_webdriver.environment import Environment


class MetaSelenium(type):

    def __init__(cls, name, parents, dict):
        '''
            We custom only the childen classes of DjSelBaseCase, so if the parent
            is LiveServerTestCase we are in DjSelBaseCase.
        '''
        if cls.__base__ != LiveServerTestCase:
            MetaSelenium._custom_cls(cls)
            dict = {k: v for k, v in cls.__dict__.items()}
        type.__init__(cls, name, parents, dict)

    @staticmethod
    def _custom_cls(cls):
        '''
            This method reads all the test methods of the class to custom them.
            It takes the original method and it clone it for each webdriver.
            Exemple: if you have a class with a method named test and you want to run
            it with Chrome and firefox this method will build two news methods that will be
            named test_on_Chrome and test_on_Firefox.
            It also set a decorator on each the tests method to init the webdriver before
            the runing of the method.
        '''

        def _build_new_method(function, name, webdriver, setup, teardown):
            '''
                Decorator to init a webdriver before the running of the method.
            '''
            @wraps(function)
            def wrapper(self, *args, **kwargs):
                self.webdriver =  Environment.init_webdriver(webdriver)
                if self.webdriver:
                    try:
                        if setup:
                            setup(self)
                    except:
                        self.webdriver.quit()
                        raise
                    else:
                        try:
                            result = function(self, *args, **kwargs)
                        except:
                            raise
                        finally:
                            teardown(self)
                            self.webdriver.quit()
                    return result

            wrapper.__name__= name
            return wrapper

        functions = [func for func in list(cls.__dict__.items()) if type(func[1]) == types.FunctionType]
        setup = getattr(cls, 'setUp') if hasattr(cls, 'setUp') else None
        teardown = getattr(cls, 'tearDown') if hasattr(cls, 'tearDown') else None
        for name, function in list(functions):
            if name.startswith("test"):
                for webdriver in Environment.get_webdrivers():
                    new_name = "{name}_on_{webdriver}".format(name=name,
                                webdriver=webdriver)
                    setattr(cls, new_name, _build_new_method(function, new_name,
                                            webdriver, setup, teardown))
                delattr(cls, name)

        def dummy(self):
            pass

        if setup:
            cls.setUp = dummy
        if teardown:
            cls.tearDown = dummy
        return cls


class DjangoWebdriverTestCase(LiveServerTestCase):
    '''
        It is the parent class of all selenium test.
        The metaclass is overloaded to create the methods for each webdriver before the 
        building of the selenium class test.
        You have not to init the webdriver in your test class because the metaclass 
        do that for you.
    '''
    __metaclass__ = MetaSelenium
