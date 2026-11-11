def pytest_unwrap(fn):
    # pytest < 8.4 stores the original function in __pytest_wrapped__,
    # pytest >= 8.4 wraps fixtures in FixtureFunctionDefinition (__wrapped__)
    wrapped = getattr(fn, "__pytest_wrapped__", None)
    if wrapped is not None:
        return wrapped.obj
    return fn.__wrapped__
