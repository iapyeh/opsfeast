"""Bounded, process-local browser readiness notifications; no durable user tracking."""
from collections import deque
from datetime import datetime,timezone
import threading
import time


class BrowserEvents:
    def __init__(self,limit=256):
        self.events=deque(maxlen=limit)
        self.seq=0
        self.condition=threading.Condition()

    def publish(self, *, session_id, view, block_id, seen_seq):
        with self.condition:
            self.seq+=1
            event=dict(seq=self.seq,type='reader.opened',session_id=session_id,
                       view=view,block_id=block_id,seen_seq=seen_seq,
                       received_at=datetime.now(timezone.utc).isoformat(timespec='milliseconds'))
            self.events.append(event)
            self.condition.notify_all()
            return dict(event)

    def read(self,after=0,wait=0):
        if type(after) is not int or after<0 or type(wait) not in (int,float) or not 0<=wait<=15:
            raise ValueError('invalid_event_cursor')
        deadline=time.monotonic()+wait
        with self.condition:
            if after>self.seq:raise ValueError('future_event_cursor')
            while self.seq<=after and time.monotonic()<deadline:
                self.condition.wait(deadline-time.monotonic())
            oldest=self.events[0]['seq'] if self.events else self.seq+1
            return dict(events=[dict(e) for e in self.events if e['seq']>after],
                        next_seq=self.seq,gap=after<oldest-1)
