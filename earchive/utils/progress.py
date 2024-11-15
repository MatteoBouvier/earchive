import sys
import time
from collections.abc import Generator, Iterable
from itertools import cycle
from typing import Any, Self, override


class Bar[T]:
    def __init__(
        self,
        iterable: Iterable[T] | None = None,
        *,
        description: str = "",
        total: int | None = None,
        multiplier: int = 1,
        percent: bool = False,
        miniters: int = 10,
        mininterval: float = 0.2,
    ) -> None:
        self.iterable: Iterable[T] | None = iterable
        self.counter: int = 0

        self.description: str = description
        self.total: int | None = total
        self.multiplier: int = multiplier
        self.percent: bool = percent
        if self.percent and not self.total:
            raise ValueError("Cannot use percentage if total is not given")

        self.miniters: int = miniters
        self.mininterval: float = mininterval
        self.last_len: int = 0

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

        if self.total is None:
            counter_post = ""
        elif self.percent:
            counter_post = "%"
        else:
            counter_post = f"/{self.total}"

        try:
            for item in self.iterable:
                yield item

                self.counter += 1

                if self.counter - last_update_count >= self.miniters:
                    cur_t = time.time()
                    dt = cur_t - last_update_time

                    if dt >= self.mininterval:
                        if self.total is not None and self.percent:
                            counter_pre = f"{self.counter * self.multiplier / self.total * 100:.2f}"
                        else:
                            counter_pre = self.counter * self.multiplier

                        self.update(f"{next(animation_frames)} {counter_pre}{counter_post} {self.description}")
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


class _NoBar[T](Bar[T]):
    @override
    def __iter__(self) -> Generator[T, None, None]:
        if self.iterable is None:
            raise ValueError("No iterable was passed")

        yield from self.iterable


NoBar: _NoBar[Any] = _NoBar()
