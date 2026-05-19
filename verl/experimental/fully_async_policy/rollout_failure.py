# Copyright 2025 Meituan Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import traceback as traceback_lib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RolloutErrorSignal:
    """Serializable queue signal for abnormal rollout shutdown."""

    error_type: str
    message: str
    traceback: str

    @classmethod
    def from_exception(cls, exc: BaseException) -> "RolloutErrorSignal":
        return cls(
            error_type=type(exc).__name__,
            message=str(exc),
            traceback="".join(traceback_lib.format_exception(type(exc), exc, exc.__traceback__)),
        )


def first_unexpected_asyncio_exception(results) -> BaseException | None:
    for result in results:
        if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
            return result
    return None


def first_unexpected_task_exception(tasks) -> BaseException | None:
    for task in tasks:
        if task.cancelled():
            continue
        exception = task.exception()
        if exception is not None and not isinstance(exception, asyncio.CancelledError):
            return exception
    return None


async def wait_for_task_failure_or_completion(tasks) -> BaseException | None:
    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    return first_unexpected_task_exception(done)


def raise_for_rollout_error_signal(sample: Any):
    if not isinstance(sample, RolloutErrorSignal):
        return

    message = f"Rollout generation failed: {sample.error_type}: {sample.message}"
    if sample.traceback:
        message = f"{message}\n{sample.traceback}"
    raise RuntimeError(message)
