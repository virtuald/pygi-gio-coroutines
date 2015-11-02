
from os.path import abspath

import logging
logging.basicConfig()

from gi.repository import Gio
from gi.repository import GLib

from gio_coroutines import gio_coroutine, async, idle, Return

from helper import CoroTestCase, coro

class TestCoroutines(CoroTestCase):

    @coro
    def test_idle_1(self):
        yield idle
        
    @coro
    def test_idle_2(self):
        yield idle
        yield idle
    
    @coro
    def test_idle_3(self):
        
        def _inner():
            yield idle
        
        yield idle
        
        for i in _inner():
            yield i
    
    @coro(fail=ValueError)
    def test_yield_none_1(self):
        yield None
            
    @coro(fail=ValueError)
    def test_yield_none_2(self):
        yield idle
        yield
        
    def test_exc_1(self):
        
        @gio_coroutine
        def _inner():
            raise ValueError()
        
        self.coro_raises(ValueError, _inner)
            
    def test_exc_2(self):
        
        @gio_coroutine
        def _inner():
            yield idle
            raise ValueError()
        
        self.coro_raises(ValueError, _inner)
    
    def test_not_generator(self):
        
        success = self.require('Inner not called')
        
        @gio_coroutine
        def _inner():
            success()
            
        _inner()
        
    def test_returns(self):
        
        @gio_coroutine
        def _inner():
            yield idle
            raise Return('val')
        
        self.coro_returns('val', _inner)
        
    @coro
    def test_gio_ops(self):
        
        success = self.require("Did not reach the end")
        
        f = Gio.File.new_for_path('/path/that/does/not/exist')
        yield idle
        
        with self.assertRaises(GLib.Error):
            yield async(f, 'read', 0, None)
            
        success()
    
    @coro
    def test_gio_ok(self):
        
        success = self.require("Did not reach the end")
        
        fpath = abspath(__file__)
        with open(fpath, 'r') as fp:
            flen = len(fp.read())
            
        # add this for coverage' sake
        f = Gio.File.new_for_path('/path/that/does/not/exist')
        with self.assertRaises(GLib.Error):
            yield async(f, 'read', 0, None)
        
        yield idle
            
        f = Gio.File.new_for_path(fpath)
        
        stream = yield async(f, 'read', 0, None)
        
        bytes_read = (yield async(stream, 'read_bytes', flen, 0, None)).get_data()
        assert flen == len(bytes_read)
        
        # Shouldn't be anything left
        bytes_read = (yield async(stream, 'read_bytes', flen, 0, None)).get_data()
        assert len(bytes_read) == 0
        
        yield async(stream, 'close', 0, None)
        
        success()
        