pygi-gio-coroutines
===================

This is a prototype for a single-file library that allows you to integrate
python coroutines with Gio's asynchronous operations. Gio provides a lot of
asynchronous I/O support, but they're a bit clunky to use and this makes it
a little easier to chain I/O operations together.

This implementation was developed for the `Exaile audio player <http://www.exaile.org>`_
to help us as we move to GTK3. I'm still feeling this out to see what bugs
come up, so please provide feedback!

There's a lot of features that could be added to such a project. I've added
things that are useful for me now, feel free to add your own. Some ideas:

* Transparent support for cancellation

  * Cancellation of I/O
  * Cancellation of the coroutine
  
Usage
=====

.. code:: python

  from gio_coroutines import gio_coroutine, async, idle, Return
  
  @gio_coroutine
  def lots_of_io():
  
    ..
    
    # Async write operation
    result = yield async(f, 'write', bytes, 0, None)
    
    .. 
    
    # Delay execution via GLib.idle_add
    yield idle
    
    # return some value
    raise Return('val')
    
  def on_done(r):
    try:
      retval = r.result()
    except:
      logger.exception("Some bad thing happened")
  
  lots_of_io(on_done=on_done)
  
Requirements
============

* PyGObject + Gio

Installation
============

This project is easily installed via pip:

  pip install pygi-gio-coroutines

Author
======

Dustin Spicuzza (dustin@virtualroadside.com)

Portions of the code were inspired by Tornado's coroutine + futures
implementation.

License
=======

LGPL 2.1+ (Same as PyGI)
