# Security

## Trust model

A φyrx program can read and write files (`brøtjt`, `mɴyrx`), include other files (`bukð`) and exit the process (`qab'`). Running an untrusted program is as risky as running untrusted Python.

The runtime limits stop runaway programs. They are not a sandbox. A program can still read, write, and include any path the host allows, and it can still choose its exit code.

- Recursion depth. `PHYX_RECURSION` is the host recursion ceiling (decimal, default `16384`). Passing it is the fault `the abilities called each other too deeply`. See [docs/reference.md](docs/reference.md#execution) and [docs/toolchain.md](docs/toolchain.md).
- Range size. `tøwp` on text or a list stops at `100000` items, a φyrx hexadecimal numeral (1,048,576 in decimal) ([docs/reference.md](docs/reference.md#arithmetic)). `ronɣ` stops at `100000` numbers, a φyrx hexadecimal numeral (1,048,576 in decimal) ([docs/reference.md](docs/reference.md#collections)). A longer result is a runtime fault ([docs/spec.md](docs/spec.md#5-evaluation)).
- Memory. A host `MemoryError` is the runtime fault `the program ran out of memory`. See [docs/reference.md](docs/reference.md#execution).

An included file runs in the same session and can call the same verbs.

## Verbs

The list below is the verb table in [docs/reference.md](docs/reference.md#standard-verbs). Each of these touches the file system, the process, or the environment. The other verbs in that table do arithmetic, logic, conversion, or collections, or they only direct control flow inside the program.

Search paths for `bukð` and `brøtjt`, and the write rule for `mɴyrx`, are also specified in [docs/spec.md](docs/spec.md#6-modules-command-notes-on-disk). Implementations are in [phyx/builtins.py](phyx/builtins.py).

### File system

| Verb | Reference | What it does |
| --- | --- | --- |
| `brøtjt` | [Control, modules, process](docs/reference.md#control-modules-process) | Research. Read UTF-8 text. A relative path is sought in the file's directory, the working directory, and `PHYX_PATH`. The shipped library `phyx/lib/` is not searched. An absolute path is used as written. |
| `mɴyrx` | [Control, modules, process](docs/reference.md#control-modules-process) | Spread. Write UTF-8 text and yield the text. A relative path is resolved next to the program and is not searched for. An absolute path is used as written. The implementation also creates missing parent directories ([phyx/builtins.py](phyx/builtins.py)). |
| `bukð` | [Control, modules, process](docs/reference.md#control-modules-process) | Play/cast. Read and run another `.phyx` or `.vphyx` file in this session. A relative path is sought in the file's directory, the working directory, `PHYX_PATH`, then `phyx/lib/`. An absolute path is used as written. |

### Process

| Verb | Reference | What it does |
| --- | --- | --- |
| `qab'` | [Control, modules, process](docs/reference.md#control-modules-process) | Kill the process with the given exit code. |
| `'uxq` | [Control, modules, process](docs/reference.md#control-modules-process) | Command. The list of program arguments, as text. |
| `pihš` | [Speak, convert](docs/reference.md#speak-convert) | Speak. Print the value and yield it. |
| `krepg` | [Speak, convert](docs/reference.md#speak-convert) | Reveal in source form. The implementation writes that form as a line on the same output as `pihš` ([phyx/builtins.py](phyx/builtins.py)). |
| `'ətsxn` | [Speak, convert](docs/reference.md#speak-convert) | Ask a line of input. |

### Environment

`brøtjt` and `bukð` read the `PHYX_PATH` environment variable as a search path. The verb table has no verb that reads or sets any other environment variable.

`PHYX_TREEWALK`, `PHYX_RECURSION`, `PHYX_DUMP`, and `PHYX_ASSETS` are host settings of the toolchain. They are not verbs.

## Reporting

GitHub private vulnerability reporting is enabled for this repository. Use the Security tab, "Report a vulnerability":

https://github.com/Brage1025/phyrexianscript/security/advisories/new

## Supported versions

The latest release only.
