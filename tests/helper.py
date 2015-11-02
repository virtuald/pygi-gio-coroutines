
import unittest

from gi.repository import GLib
from functools import wraps, partial

from gio_coroutines import gio_coroutine

import logging
logger = logging.getLogger(__name__)

class _Success(object):
    
    def __init__(self, msg):
        self.ok = False
        self.msg = msg
    
    def __call__(self):
        self.ok = True

def coro(f=None, fail=None):
    '''
        Test coroutine wrapper which adds a timeout and will
        quit the loop when the function is complete.
    '''
    
    if f is None:
        return partial(coro, fail=fail)
    
    fc = gio_coroutine(f)
    
    @wraps(fc)
    def wrapper(self, *args, **kwargs):
        
        def _on_done(r):
            try:
                r.result()
            except Exception as e:
                if fail is not None:
                    if not isinstance(e, fail):
                        self.error = "Did not fail with correct type"
                    else:
                        success()
                else:
                    logger.exception("Unhandled exception")
                    self.error = "Unhandled exception"
                
            else:
                if fail is not None:
                    self.error = "Did not fail"
                else:
                    success()
            
            self.quit()
        
        success = self.require('Coro result not properly set')
        fc(self, on_done=_on_done, *args, **kwargs)
        
        self.glib_run()
    
    return wrapper

class CoroTestCase(unittest.TestCase):

    def setUp(self):
        self.loop = GLib.MainLoop()
        self._error = []
        self._success = []
        
    @property
    def error(self):
        return self._error
    
    @error.setter
    def error(self, val):
        self.error.append(val) 

    def tearDown(self):
        assert not self.error, self.error
        for s in self._success:
            assert s.ok,  s.msg
        self.quit()
        
    def glib_run(self):
        
        data = [None]
        
        def _fail():
            data[0] = None
            self.error = 'Timeout occurred'
            self.quit()
            
        data[0] = GLib.timeout_add(5000, _fail)
        
        if self.loop is not None:
            self.loop.run()
        
        if data[0] is not None:
            GLib.source_remove(data[0])
    
      
    def quit(self):
        if self.loop is not None:
            self.loop.quit()
            self.loop = None

    def require(self, val):
        s = _Success(val)
        self._success.append(s)
        return s
        
    def success(self):
        self._require_success = False

    def coro_raises(self, e, f, *args, **kwargs):
        
        def _on_done(r):
            try:
                r.result()
                self.error = 'Did not raise'
            except Exception as ex:
                if not isinstance(ex, e):
                    self.error = "Wrong type raised"
                else:
                    success()
                    
            self.quit()
        
        success = self.require('Did not raise')
        
        f(on_done=_on_done, *args, **kwargs)
        self.glib_run()
        
    def coro_returns(self, v, f, *args, **kwargs):
        
        def _on_done(r):
            try:
                if v is not r.result():
                    self.error = '%s is not %s' % (v, r.result())
                else:
                    success()
            except:
                self.error = "Should not raise"
                
            self.quit()
        
        success = self.require('Returns %s' % v)
        
        f(on_done=_on_done, *args, **kwargs)
        self.glib_run()
