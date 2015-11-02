#!/usr/bin/env python

from __future__ import print_function

# This is only required to make the example with without requiring installation
# - Most of the time, you shouldn't use this hack
import sys
from os.path import join, dirname
sys.path.insert(0, join(dirname(__file__), '..'))


from gi.repository import Gio
from gi.repository import GLib

from gio_coroutines import gio_coroutine, async, idle, Return

import logging
logger = logging.getLogger(__name__)

writing = True

def timer_callback():
    logging.info('Called while writing?')
    return writing

@gio_coroutine
def write_large_file():

    # Create a file
    f = Gio.File.new_for_commandline_arg('random.data')
    
    
    stream = yield async(f, 'replace',
                         None, False,
                         Gio.FileCreateFlags.REPLACE_DESTINATION,
                         0) 

    # Write 20 chunks of gibberish to it
    zeroes = '0'*4096
    
    for _ in range(100):
        bytes_written = yield async(stream, 'write',
                                    zeroes, 0, None)
        
        print('Wrote', bytes_written, 'bytes') 
    
    
    # Close it
    result = yield async(stream, 'close', 0, None)
    print('Closed:', result)
    
    # Causes the loop to be paused until idle_add decides that it
    # should be resumed
    yield idle
    
    global writing
    writing = False
    
    raise Return("I'm done")


def on_done(r):
    try:
        retval = r.result()
    except:
        logger.exception("Error in coroutine")
    else:
        logger.info("Return value: %s", retval)
        
    global loop
    loop.quit()


if __name__ == '__main__':
    
    logging.basicConfig(level=logging.INFO)
    
    write_large_file(on_done=on_done)
    GLib.timeout_add(5, timer_callback)
    
    loop = GLib.MainLoop()
    loop.run()
    
    