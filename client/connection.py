"""Run network work away from the pygame event loop."""
from concurrent.futures import Future
from threading import Thread
from typing import Callable, TypeVar

from gameplay.netgame import NetClient

Client = TypeVar("Client", bound=NetClient)
Result = TypeVar("Result")


def run_network_task(work: Callable[[], Result]) -> Future[Result]:
    attempt: Future[Result] = Future()

    def run() -> None:
        try:
            result = work()
        except Exception as exc:
            attempt.set_exception(exc)
        else:
            attempt.set_result(result)

    Thread(target=run, name="val2d-network", daemon=True).start()
    return attempt


def discard_connection(attempt: Future[Client]) -> Future[None]:
    cleanup: Future[None] = Future()

    def discard(result: Future[Client]) -> None:
        try:
            if result.exception() is None:
                result.result().close()
        finally:
            cleanup.set_result(None)

    Thread(target=lambda: attempt.add_done_callback(discard), daemon=True).start()
    return cleanup
