
# Benchmark

Times a zero-argument function with warmup and `timeit`.

```python
Benchmark(logger=None)
```

## `measure_time`

```python
measure_time(func, warmup_times=3, run_times=5, repeat_times=1, suppress_output=True) -> float
```

| Parameter | Description |
|---|---|
| `func` | Callable taking no arguments. Bind arguments with `lambda` or `functools.partial`. |
| `warmup_times` | Untimed warmup calls (`0` skips warmup). |
| `run_times` | Calls per timed batch (`>= 1`). |
| `repeat_times` | Number of batches (`>= 1`). |
| `suppress_output` | Silence stdout, stderr and logging while running. |

**Returns** seconds **per call** from the *fastest* batch: `min(batches) / run_times`. This is the standard `timeit` approach: slower batches mostly reflect noise from other processes, not your code.

```python
bench = Benchmark()

def parse():
    return sum(range(1_000_000))

print(f"{bench.measure_time(parse, run_times=10, repeat_times=3):.4f}s per call")
```

### Choosing counts

| Goal | Suggestion |
|---|---|
| Quick sanity check | defaults |
| Stable number for a fast function | `run_times=100+`, `repeat_times=5` |
| Slow function (seconds) | `warmup_times=1, run_times=1, repeat_times=3` |

### Errors

| Exception | When |
|---|---|
| `ValueError` | `run_times < 1`, `repeat_times < 1` or `warmup_times < 0` |
| `InvalidFunctionError` | `func` isn't callable |
| `BenchmarkError` | `func` raised while being measured (original chained as `__cause__`) |

## Output suppression

With `suppress_output=True`, stdout and stderr are redirected to `os.devnull` and `logging.disable(CRITICAL)` is set for the duration. The **previous** `logging.disable` level is restored afterwards, even if you had set your own.

This is **process-wide**: other threads that print or log during the run are silenced too. Don't use it in multi-threaded programs; pass `suppress_output=False`.

## Async

`haashi.aio.Benchmark.measure_time` awaits coroutine functions, times batches with `time.perf_counter()` and reports the fastest. Plain functions work but run on the event loop and block it. `suppress_output` defaults to **`False`** in the async version because silencing output is process-wide and would mute every other request in a running server. See [Async API](async.md#benchmark).
