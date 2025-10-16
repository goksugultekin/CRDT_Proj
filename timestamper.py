# timestamper.py

class Timestamper:
   

    def __init__(self, start: int = 1) -> None:
        self._next = start

    def __call__(self) -> int:
        
        v = self._next
        self._next += 1
        return v

    def peek(self) -> int:
        
        return self._next

    def bump_to(self, at_least: int) -> None:
        
        if self._next <= at_least:
            self._next = at_least + 1

    def manual(self, ts_value: int) -> int:
        
        self.bump_to(ts_value)
        return ts_value
