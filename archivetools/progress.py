import time
import sys
from typing import Generator, Iterable
from itertools import cycle


class Bar[T]:
    def __init__(self, iterable: Iterable[T], miniters: int = 10, mininterval: float = 0.2) -> None:
        self.iterable = iterable

        self.miniters = miniters
        self.mininterval = mininterval
        self.last_len = 0

    def __iter__(self) -> Generator[T, None, None]:
        counter = 0
        last_update_count = 0
        last_update_time = 0

        animation_frames = cycle(
            ["[   ]", "[=  ]", "[== ]", "[ ==]", "[  =]", "[   ]", "[  =]", "[ ==]", "[== ]", "[=  ]"]
        )

        try:
            for item in self.iterable:
                yield item

                counter += 1

                if counter - last_update_count >= self.miniters:
                    cur_t = time.time()
                    dt = cur_t - last_update_time
                    if dt >= self.mininterval:
                        self.update(f"{next(animation_frames)} processed {counter} files")
                        last_update_count = counter
                        last_update_time = cur_t

        finally:
            self.clear()

    def update(self, s: str) -> None:
        len_s = len(s)
        sys.stdout.write("\r" + s + (" " * max(self.last_len - len_s, 0)))
        sys.stdout.flush()

        self.last_len = len_s

    def clear(self) -> None:
        sys.stdout.write("\r" + (" " * self.last_len) + "\r")
        sys.stdout.flush()
