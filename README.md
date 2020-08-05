
# More Logs - Structured Logging and Exception Handling


|Branch      |Status   |
|------------|---------|
|master      | [![Build Status](https://travis-ci.org/klahnakoski/mo-logs.svg?branch=master)](https://travis-ci.org/klahnakoski/mo-logs) |
|dev         | [![Build Status](https://travis-ci.org/klahnakoski/mo-logs.svg?branch=dev)](https://travis-ci.org/klahnakoski/mo-logs)  [![Coverage Status](https://coveralls.io/repos/github/klahnakoski/mo-logs/badge.svg?branch=dev)](https://coveralls.io/github/klahnakoski/mo-logs?branch=dev)  |


This library provides two main features

* **Structured logging** - output is all JSON (with options to serialize to text for humans)
* **Exception handling weaved in** - Good logs must represent what happened,
and that can only be done if the logging library is intimately familiar with
the (exceptional) code paths taken.

## Motivation

Exception handling and logging are undeniably linked. There are many instances
where exceptions are raised and must be logged, and others where the subsuming 
system can fully handle the exception, and no log should be emitted. Exception 
handling semantics are great because they decouple the cause from the solution, 
but this can be at odds with clean logging - which couples raising and catching 
to make appropriate decisions about what to emit to the log.  

This logging module is additionally responsible for raising exceptions,
collecting the trace and context, and then deducing if it must be logged, or
if it can be ignored because something can handle it.


## Basic Usage

### Use `Log.note()` for all logging

```python
    Log.note("Hello, World!")
```

There is no need to create logger objects. The `Log` module will keep track of
what, where and when of every call.

### Using named parameters

All logging calls accept a string template with named parameters. Keyword arguments
can be added to the call to provide values. The template and arguments are not 
combined at call time, rather they are held in a JSON-izable data structure for 
structured logging. The template is only expanded *if* the log is serialized for humans.  

```python
    Log.note("Hello, {{name}}!", name="World!")
```

**Do not use Python's string formatting features:**
 
* [string formatting operator (`%`)](http://python-reference.readthedocs.io/en/latest/docs/str/formatting.html), 
* [the `format()` function](https://docs.python.org/3/library/stdtypes.html#str.format) 
* [literal string intrpolation](https://www.python.org/dev/peps/pep-0498/).

Using any of these will expand the string template at call time, which is a parsing
nightmare for log analysis tools.


### Parametric parameters

All the `Log` functions accept a `default_params` as a second parameter, like so:

```python
    Log.note("Hello, {{name}}!", {"name": "World!"})
```

this is meant for the situation your code already has a bundled structure you
wish to use as a source of parameters. If keyword parameters are used, they
will override the default values. Be careful when sending whole data
structures, they will be logged!

### Formatting parameters

There are a variety of formatters, and they can be applied by using the 
pipe (`|`) symbol.  

In this example we cast the `name` to uppercase

```python
    Log.note("Hello, {{name|upper}}!", name="World!")
```

Some formatters accept arguments:

```python
    Log.note("pi is {{pi|round(places=3)}}!", pi=3.14159265)
```

You can look at the [`strings` module](https://github.com/klahnakoski/mo-logs/blob/dev/mo_logs/strings.py#L56) to see the formatters available.

### Please, never use locals()

```python
    def worker(value):
        name = "tout le monde!"
        password = "123"
        Log.note("Hello, {{name}}", locals())      # DO NOT DO THIS!
```

Despite the fact using `locals()` is a wonderful shortcut for logging it is
dangerous because it also picks up sensitive local variables. Even if
`{{name}}` is the only value in the template, the whole `locals()` dict will
be sent to the structured loggers for recording. 

### Destination: Database!

All logs are structured logs; the parameters will be included, unchanged, in
the log structure. This library also expects all parameter values to be JSON-
serializable so they can be stored/processed by downstream JSON tools.

**Example structured log** 
```json
    {
        "template": "Hello, {{name}}!",
        "params": {"name": "World!"},
        "context": "NOTE",
        "format": "{{machine.name}} (pid {{machine.pid}}) - {{timestamp|datetime}} - {{thread.name}} - \"{{location.file}}:{{location.line}}\" - ({{location.method}}) - Hello, {{params.name}}!",
        "location": {
            "file": "/home/kyle/code/example.py",
            "line": 10,
            "method": "worker"
        },
        "machine": {
            "name": "klahnakoski-39477",
            "os": "Windows10",
            "pid": 18060,
            "python": "CPython"
        },
        "thread": {
            "id": 14352,
            "name": "Main Thread"
        },
        "timestamp": 1578673471
    }
```

## Exception Handling

### Instead of `raise` use `Log.error()`

```python
    Log.error("This will throw an error")
```

The actual call will always raise an exception, and it manipulates the stack
trace to ensure the caller is appropriately blamed. Feel free to use the
`raise` keyword (as in `raise Log.error("")`), if that looks nicer to you. 

### Always chain your exceptions

The `cause` parameter accepts an `Exception`, or a list of exceptions.
Chaining is generally good practice that helps you find the root cause of
a failure. 

```python
    try:
        # Do something that might raise exception
    except Exception as cause:
        Log.error("Describe what you were trying to do", cause=cause)
```

### Use `raise from`?

Python3 attaches the full stacktrace to exceptions and allows chaining with `raise from`.  We can replace 

```python
    from mo_logs import Log 
    Log.error("description", cause=cause)
```

with 

```python
    from mo_logs.exceptions import ERROR, Except 
    raise Except(ERROR, "description") from cause
```

which is a bit more clunky, especially when passing dynamic parameters. Plus it breaks the `Log.<type>()` calling pattern; switching between an `error` and a `warning` is more than a name change.


### Use named parameters in your error descriptions too

Error logging accepts keyword parameters just like `Log.note()` does

```python
    def worker(value):
        try:
            Log.note("Start working with {{key1}}", key1=value1)
            # Do something that might raise exception
        except Exception as cause:
            Log.error("Failure to work with {{key2}}", key2=value2, cause=cause)
```

### No need to formally type your exceptions

An exception can be uniquely identified by the message template
it is given; exceptions raised with the same template are the same type. You
should have no need to create new exception types.

### Testing for exception "types"

This library advocates chaining exceptions early and often, and this hides
important exception types in a long causal chain. `mo-logs` allows you to easily
test if a type (or string, or template) can be found in the causal chain by using
the `in` keyword:   

```python
    def worker(value):
        try:
            # Do something that might raise exception
        except Exception as cause:
            if "Failure to work with {{key2}}" in cause:
                # Deal with exception thrown in above code, no matter
                # how many other exception handlers were in the chain
```

For those who may abhor the use of magic strings, feel free to use constants instead:

```python
    KEY_ERROR = "Failure to work with {{key}}"

    try:
        Log.error(KEY_ERROR, key=42)        
    except Exception as cause:
        if KEY_ERROR in cause:
            Log.note("dealt with key error")
```




### If you can deal with an exception, then it will never be logged

When a caller catches an exception from a callee, it is the caller's
responsibility to handle that exception, or re-raise it. There are many
situations a caller can be expected to handle exceptions; and in those cases
logging an error would be deceptive. 

```python
    def worker(value):
        try:
            Log.error("Failure to work with {{key3}}", key3=value3)
        except Exception as cause:
            # Try something else
```

### Use `Log.warning()` if your code can deal with an exception, but you still want to log it as an issue

```python
    def worker(value):
        try:
            Log.note("Start working with {{key4}}", key4=value4)
            # Do something that might raise exception
        except Exception as cause:
            Log.warning("Failure to work with {{key4}}", key4=value4, cause=cause)
```
### Don't loose your stack trace!

Be aware your `except` clause can also throw exceptions: In the event you
catch a vanilla Python Exception, you run the risk of loosing its stack trace.
To prevent this, wrap your exception in an `Except` object, which will capture
your trace for later use. Exceptions thrown from this `Log` library need not
be wrapped because they already captured their trace. If you wrap an `Except`
object, you simply get back the object you passed.


```python
    try:
        # DO SOME WORK        
    except Exception as cause:
        cause = Except.wrap(cause)
        # DO SOME FANCY ERROR RECOVERY
 ```

### Always catch all `Exceptions`

Catching all exceptions is preferred over the *only-catch-what-you-can-handle*
strategy. First, exceptions are not lost because we are chaining. Second,
we catch unexpected `Exceptions` early and we annotate them with a
description of what the local code was intending to do. This annotation
effectively groups the possible errors (known, or not) into a class, which
can be used by callers to decide on appropriate mitigation.  

To repeat: When using dependency injection, callers can not reasonably be
expected to know about the types of failures that can happen deep down the
call chain. This makes it vitally important that methods summarize all
exceptions, both known and unknown, so their callers have the information to
make better decisions on appropriate action.  

For example: An abstract document container, implemented on top of a SQL 
database, should not emit SQLExceptions of any kind: A caller that uses a 
document container should not need to know how to handle SQLExceptions (or any 
other implementation-specific exceptions). Rather, in this example, the 
caller should be told it "can not add a document", or "can not remove a 
document". This allows the caller to make reasonable decisions when they do 
occur. The original cause (the SQLException) is in the causal chain.

Another example, involves *nested exceptions*: If you catch a particular type 
of exception, you may inadvertently catch the same type of exception 
from deeper in the call chain. Narrow exception handling is an illusion. 
Broad exception handling will force you to consider a variety of failures 
early; force you to consider what it means when a block of code fails; and 
force you to describe it for others.

### Don't make methods you do not need

There is an argument that suggests you should break your code into logical methods, rather than catching exceptions: The method name will describe action that failed, and the stack trace can be inspected to make mitigation decisions. Additional methods is a poor solution:

* More methods means more complexity; the programmer must find the method, remember the method, and wonder if the method is used elsewhere.
* Methods can be removed while refactoring; exceptions make it clear the error is important
* Compiler optimizations can interfere with the call stack
* The method name is not an appropriate description of the problem: Many words may be required for clarity.
* Code that inspects its own stack trace is messy code.
* A stack trace does not include runtime values that are vital for describing the problem.


## Log 'Levels'

The `mo-logs` module has no concept of logging "levels". It's expected you use debug
variables: Variables prefixed with `DEBUG_` are used to control the logging
output.


```python
    # simple.py
    DEBUG_SHOW_DETAIL = True

    def worker():
        if DEBUG_SHOW_DETAIL:
            Log.note("Starting")

        # DO WORK HERE

        if DEBUG_SHOW_DETAIL:
            Log.note("Done")

    def main():
        try:
            settings = startup.read_settings()
            Log.start(settings.debug)

            # DO WORK HERE

        except Exception as cause:
            Log.error("Complain, or not", cause)
        finally:
            Log.stop()
```

This pattern of using explict debug variables allows the programmer to switch logging on and off on individual subsystems that share that variable: Either multiple debug variables in a single module, or multiple modules sharing a single debug variable.

These debug variables can be switched on/off by configuration file:

```javascript
    // settings.json
    {
        "debug":{
            "constants":{"simple.DEBUG_SHOW_DETAILS":false}
        }
    }
```

To keep logging to a single line, you may consider this pattern:

    DEBUG and Log.note("error: {{value}}", value=expensive_function()) 

Notice the `expensive_function()` is not run when `DEBUG` is false.

## Log Configuration

The `mo-logs` library will log to the console by default. ```Log.start(settings)```
will redirect the logging to other streams, as defined by the settings:

 *  **logs** - List of all log-streams and their parameters
 *  **trace** - Show more details in every log line (default False)
 *  **cprofile** - Used to enable the builtin python c-profiler, ensuring the cprofiler is turned on for all spawned threads. (default False)
 *  **constants** - Map absolute path of module constants to the values that will be assigned. Used mostly to set debugging constants in modules.

Of course, logging should be the first thing to be setup (aside from digesting
settings of course). For this reason, applications should have the following
structure:

```python
    def main():
        try:
            settings = startup.read_settings()
            Log.start(settings.debug)

            # DO WORK HERE

        except Exception as cause:
            Log.error("Complain, or not", cause)
        finally:
            Log.stop()
```

Example configuration file

```json
{"debug":{
    "trace":true,
    "log":[
        {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "examples/logs/examples_etl.log",
            "maxBytes": 10000000,
            "backupCount": 100,
            "encoding": "utf8"
        },
        {
            "log_type": "email",
            "from_address": "klahnakoski@mozilla.com",
            "to_address": "klahnakoski@mozilla.com",
            "subject": "[ALERT][DEV] Problem in ETL Spot",
            "$ref": "file://~/private.json#email"
        },
        {
            "log_type": "console"
        }
    ]
}}
```

## Capturing logs

You can capture all the logging message and send them to your own logging with 

    Log.set_logger(myLogger)
    
where `myLogger` is an instance that can accept a calls to `write(template, parameters)`. If your logging library can only handle strings, then use `message = expand_template(template, params)`.


## Problems with Python Logging

[Python's default `logging` module](https://docs.python.org/2/library/logging.html#logging.debug)
comes close to doing the right thing, but fails:  

  * It has keyword parameters, but they are expanded at call time so the values are lost in a string.  
  * It has `extra` parameters, but they are lost if not used by the matching `Formatter`.  
  * It even has stack trace with `exc_info` parameter, but only if an exception is being handled.
  * Python 2.x has no builtin exception chaining, but [Python 3 does](https://www.python.org/dev/peps/pep-3134/)

### More Reading

* **Structured Logging is Good** - https://sites.google.com/site/steveyegge2/the-emacs-problem

