from __future__ import annotations

import threading
import time
from queue import Queue
from typing import Callable, List, Tuple
import socket, glob, time

from .log import exception


class _TTS:

    _end_time = None

    def __init__(self, wait_delay_per_character):
        self.o = None
        self._wait_delay_per_character = wait_delay_per_character
        self.initializeOutput()
    def initializeOutput(self):
        self.closeConnection()
        try:
            socketFile = glob.glob('/tmp/orca-*.sock')[0]
            self.o = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.o.connect(socketFile)
            time.sleep(0.01)
        except Exception as e:
            self.o = None
    def closeConnection(self):
        try:
            if self.o:
                self.o.close()
        except Exception as e:
            pass
        self.o = None
    def IsSpeaking(self):
        if self._end_time is None:
            return False
        else:
            return self._end_time > time.time()
    def Speak(self, text, interrupt=True):
        if not self.o:
            self.initializeOutput()
        try:
            if interrupt:
                self.Stop()
            text = '<#APPEND#>' + text
            self.o.send(text.encode('utf-8'))
            time.sleep(0.01)
        except Exception as e:
            self.closeConnection()
        self._end_time = time.time() + len(text) * self._wait_delay_per_character

    def Stop(self):
        if not self.o:
            self.initializeOutput()
        try:
            self.o.send(''.encode('utf-8'))
            time.sleep(0.01)
        except Exception as e:
            self.closeConnection()



_tts = None
_is_speaking = False

_queue: Queue[Tuple[Callable, List]] = Queue()


def is_speaking():
    return _is_speaking


def _speak(text):
    with _lock:
        try:
            _tts.Speak(text)
        except:
            exception("error during _tts.Speak('%s')", text)


def speak(text: str):
    global _is_speaking
    assert isinstance(text, str)
    _queue.put((_speak, [text]))
    _is_speaking = True


def _stop():
    with _lock:
        if _is_speaking:
            try:
                _tts.Stop()
            except:
                pass  # speak() will have a similar error and fall back to sounds


def stop():
    global _is_speaking
    _queue.put((_stop, []))
    _is_speaking = False


def _loop():
    while True:
        cmd, args = _queue.get()
        if not _queue.empty():
            # print("skipped!", cmd, args)
            continue
        try:
            cmd(*args)
        except:
            exception("")


def _loop2():
    global _is_speaking
    while True:
        if _is_speaking:
            time.sleep(0.1)
            with _lock:
                if not _tts.IsSpeaking():
                    _is_speaking = False
        time.sleep(0.1)


def init(wait_delay_per_character):
    global _tts, _lock
    _lock = threading.Lock()
    _tts = _TTS(wait_delay_per_character)
    t = threading.Thread(target=_loop)
    t.daemon = True
    t.start()
    t = threading.Thread(target=_loop2)
    t.daemon = True
    t.start()
