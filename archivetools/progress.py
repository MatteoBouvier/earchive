import time
import sys
from typing import Generator, Iterable, Self
from itertools import cycle


class Bar[T]:
    def __init__(self, iterable: Iterable[T] | None = None, miniters: int = 10, mininterval: float = 0.2) -> None:
        self.iterable = iterable
        self.counter = 0

        self.miniters = miniters
        self.mininterval = mininterval
        self.last_len = 0

    def __call__(self, iterable: Iterable[T]) -> Self:
        self.iterable = iterable
        self.counter = 0

        return self

    def __iter__(self) -> Generator[T, None, None]:
        if self.iterable is None:
            raise ValueError("No iterable was passed")

        last_update_count = 0
        last_update_time = 0.0

        animation_frames = cycle(
            ["[   ]", "[=  ]", "[== ]", "[ ==]", "[  =]", "[   ]", "[  =]", "[ ==]", "[== ]", "[=  ]"]
        )

        try:
            for item in self.iterable:
                yield item

                self.counter += 1

                if self.counter - last_update_count >= self.miniters:
                    cur_t = time.time()
                    dt = cur_t - last_update_time
                    if dt >= self.mininterval:
                        self.update(f"{next(animation_frames)} processed {self.counter} files")
                        last_update_count = self.counter
                        last_update_time = cur_t

        finally:
            self.clear()

    def update(self, s: str) -> None:
        len_s = len(s)
        sys.stderr.write("\r" + s + (" " * max(self.last_len - len_s, 0)))
        sys.stderr.flush()

        self.last_len = len_s

    def clear(self) -> None:
        sys.stderr.write("\r" + (" " * self.last_len) + "\r")
        sys.stderr.flush()
