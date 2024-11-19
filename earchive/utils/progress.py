import sys
import time
from collections.abc import Generator, Iterable, Iterator
from itertools import cycle
from types import TracebackType
from typing import Self, override


class Bar:
    def __init__(
        self,
        description: str = "",
        total: int | None = None,
        multiplier: int = 1,
        percent: bool = False,
        miniters: int = 10,
        mininterval: float = 0.2,
        maxiters: int | bool = False,
    ) -> None:
        self.description: str = description
        self.total: int | None = total
        self.multiplier: int = multiplier
        self.percent: bool = percent
        if self.percent and not self.total:
            raise ValueError("Cannot use percentage if total is not given")

        self.miniters: int = miniters
        self.mininterval: float = mininterval
        self.maxiters: int = maxiters

        self.counter: int = 0
        self.last_len: int = 0
        self.last_update_count: int = 0
        self.last_update_time: float = 0.0

        self.animation_frames: Iterator[str] = cycle(
            ["[   ]", "[=  ]", "[== ]", "[ ==]", "[  =]", "[   ]", "[  =]", "[ ==]", "[== ]", "[=  ]"]
        )

        if self.total is None:
            self.counter_post: str = ""
        elif self.percent:
            self.counter_post = "%"
        else:
            self.counter_post = f"/{self.total}"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException], exc_value: BaseException, traceback: TracebackType) -> None:
        self.clear()

    def __call__[T](self, iterable: Iterable[T]) -> Generator[T, None, None]:
        try:
            yield from self.iter(iterable)
        finally:
            self.clear()

    def iter[T](self, iterable: Iterable[T]) -> Generator[T, None, None]:
        if self.has_reached_maxiters:
            return

        for item in iterable:
            if self.has_reached_maxiters:
                return

            yield item
            self.counter += 1

            if self.counter - self.last_update_count >= self.miniters:
                cur_t = time.time()
                dt = cur_t - self.last_update_time

                if dt >= self.mininterval:
                    self.update()
                    self.last_update_count = self.counter
                    self.last_update_time = cur_t

    @property
    def has_reached_maxiters(self) -> bool:
        return bool(self.maxiters) and self.counter >= self.maxiters

    def update(self) -> None:
        if self.total is not None and self.percent:
            counter_pre = f"{self.counter * self.multiplier / self.total * 100:.2f}"
        else:
            counter_pre = self.counter * self.multiplier

        s = f"{next(self.animation_frames)} {counter_pre}{self.counter_post} {self.description}"

        sys.stderr.write("\r" + s + (" " * max(self.last_len - len(s), 0)))
        sys.stderr.flush()

        self.last_len = len(s)

    def clear(self) -> None:
        sys.stderr.write("\r" + (" " * self.last_len) + "\r")
        sys.stderr.flush()


class _NoBar(Bar):
    @override
    def iter[T](self, iterable: Iterable[T]) -> Generator[T, None, None]:
        yield from iterable


NoBar: _NoBar = _NoBar()
