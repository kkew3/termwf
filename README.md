# A simplified Alfred-like command line workflow

## Features

- Common [data format](https://www.alfredapp.com/help/workflows/inputs/script-filter/json).
- Similar processing flow: one or more `script filter`s followed by `action`.

## Requirements

- [`coreutils`](https://wiki.debian.org/coreutils): `find`, `fold`
- [`fzf`](https://github.com/junegunn/fzf)

Recommended but optional:

- [`conda`](https://docs.conda.io/en/latest/miniconda.html) (`miniconda` is enough)

## Setup

Download `wf.py` to `/path/to/workflow/basedir`.
Within `wf.py`, set variables before `main()` as you'd like.
Create a [iTerm2](https://iterm2.com) [dedicated hotkey window](https://iterm2.com/documentation-hotkey.html).

### with `conda`

```bash
conda create -n termwf  # or other name
conda env config vars set -n termwf PYTHONPATH=/path/to/workflow/basedir
```

Configure the profile setting `General > Command > Send text at start` of the hotkey window as `conda activate termwf && python3 -m wf`.

### without `conda`

```bash
export PYTHONPATH=/path/to/workflow/basedir
```

Configure the profile setting `General > Command > Send text at start` of the hotkey window as `python3 -m wf`.

## Create the first workflow

Make a directory `workflow_name` under `/path/to/workflow/basedir`.
Within `/path/to/workflow/basedir/workflow_name`, create executables `list` and `action`, and optionally an empty file `NOARG`.
The presence of `NOARG` indicates that `list` requires no argument to run.
`list` should print json response as per [this spec](https://www.alfredapp.com/help/workflows/inputs/script-filter/json).
`action` may do anything, e.g. writing to files, copying text to clipboard.
If there are `list1`, `list2`, etc., they will be called sequentially after `list` and before `action`, with the `arg` property selected in `list` passed to `list1`, property selected in `list1` passed to `list2`, etc.

If any `list` file produces empty response, it will be seen as an error.
For `list` without `NOARG` present, the user will be prompted to input argument again;
otherwise, current workflow session will be aborted.

If any `list` file produces response containing only one item, it will be automatically selected and passed to next `list` file or `action` file as arguments.
