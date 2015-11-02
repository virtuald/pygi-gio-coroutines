#
# Copyright (C) 2015 Dustin Spicuzza <dustin@virtualroadside.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
# USA

'''
    Proof of concept coroutine implementation for Gio asynchronous
    operations. Coroutines inspired by tornado's implementation.
    
    This implementation probably reinvents too many wheels, it would probably
    be better if you used asyncio or some other framework to do some of the
    tricker bits and use proper futures et al.
    
    But... this works.
'''


from functools import wraps
import sys

from types import GeneratorType

from gi.repository import GLib

import logging
logger = logging.getLogger(__name__)


def gio_coroutine(f):
    '''
        If you pass a keyword argument to the wrapped function called
        'on_done', then when the function has completed you will be
        called with a single argument. If you call result(), it will
        either return the result of the function, or will throw an
        exception if the function threw an exception.
        
        Because of python's generator rules in 2.7, wrapped functions
        cannot actually return values, instead they must
        'raise gio_coroutines.Return'
    '''
    
    @wraps(f)
    def wrapper(*args, **kwargs):
        
        on_done = kwargs.get('on_done')
        if on_done is None:
            on_done = _default_on_done
        else:
            del kwargs['on_done']
        
        try:
            gen = f(*args, **kwargs)
        except Exception:
            runner = _Runner(None, on_done)
            runner.on_error()
        else:
            runner = _Runner(gen, on_done)
            
            if isinstance(gen, GeneratorType):
                runner.run(None)
            else:
                runner.on_done(gen)

    return wrapper

def async(obj, name, *args, **kwargs):
    '''
        Calls a gio.*_async function and continues execution of the function
        after the async callback is called.
        
        :param obj: Gio object
        :param name: Name of async function to call (without _async)
        :type name: str
        
        ::
        
            f = Gio.File.new_from_uri(uri)
            stream = yield async(f, 'create', arg .. )
    '''
    
    async_fn = getattr(obj, '%s_async' % name)
    finish_fn = getattr(obj, '%s_finish' % name)
    
    yielded = _Yielded()
    yielded.finish = finish_fn

    # Actually call the async function
    async_fn(callback=_on_done,
             user_data=yielded,
             *args, **kwargs)

    return yielded

#: If you yield this, then will pause to allow the loop to process things
idle = object()

class Return(Exception):
    '''
        If a gio coroutine raises this value, the on_done callback
        can receive the value passed to the constructor
    '''
    
    def __init__(self, value):
        self.value = value

#
# Private API
#


def _default_on_done(r):
    try:
        r.result()
    except: # pragma: no cover
        logger.exception("Unhandled exception in coroutine")

class _Yielded(object):
    pass

class _Result(object):
    
    def __init__(self, r, e):
        self._result = r
        self._exc_info = e
        
    def result(self):
        if self._exc_info is not None:
            _raise_exc_info(self._exc_info)
        return self._result
    
class _Runner(object):
    
    def __init__(self, gen, on_done):
        self._gen = gen
        self._on_done = on_done
        
    def run(self, last_result):
        try:
            yielded = self._gen.send(last_result)
        except (StopIteration, Return) as e:
            self.on_done(getattr(e, 'value', None))
        except:
            self.on_error()
        else:
            self.do_yield(yielded)
    
    def run_err(self):
        try:
            yielded = self._gen.throw(*sys.exc_info())
        except (StopIteration, Return) as e:
            self.on_done(getattr(e, 'value', None))
        except:
            self.on_error()
        else:
            self.do_yield(yielded)
    
    def do_yield(self, yielded):
        if yielded is idle:
            GLib.idle_add(self.run, None)
        elif not isinstance(yielded, _Yielded):
            try:
                raise ValueError("Can only yield the result of async()")
            except:
                self.run_err()
        else:
            yielded.runner = self
    
    def on_done(self, value):
        try:
            self._on_done(_Result(value, None))
        except:  # pragma: no cover
            logger.exception("Unhandled exception in on_done callback")
        finally:
            self._on_done = None
            self._gen = None
        
    def on_error(self):
        try:
            self._on_done(_Result(None, sys.exc_info()))
        except:  # pragma: no cover
            logger.exception("Unhandled exception in on_error callback")
        finally:
            self._on_done = None
            self._gen = None
            

def _on_done(obj, result, yielded):
    try:
        result = yielded.finish(result)
    except Exception:
        yielded.runner.run_err()
    else:
        yielded.runner.run(result)
    finally:
        yielded.runner = None


# Stolen from tornado; covered by Apache 2.0 license

if sys.version_info > (3,):  # pragma: no cover
    exec("""
def _raise_exc_info(exc_info):
    raise exc_info[1].with_traceback(exc_info[2])
""")
else: # pragma: no cover
    exec("""
def _raise_exc_info(exc_info):
    raise exc_info[0], exc_info[1], exc_info[2]
""")
    
