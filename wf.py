#!/usr/bin/env python3
import contextlib
import json
import os
from pathlib import Path
import readline  # pylint: disable=unused-import
import shlex
import subprocess


def u(path):
    return str(Path(path).expanduser())


basedir = os.path.dirname(__file__)
workdir = u('~/.config/termwf')
listfile = os.path.join(workdir, 'list')
resp_timeout = 10


def main():
    os.makedirs(workdir, exist_ok=True)
    try:
        while True:
            wf_name = prompt_wf()
            os.chdir(wf_name)
            with contextlib.suppress(NextWorkflowRequest):
                if os.path.isfile('NOARG'):
                    resp = list_no_arg()
                else:
                    resp = list_requesting_arg()
                selected_resp = present_list(resp)
                next_listscript, next_listid = get_next_listscript('list')
                while next_listscript:
                    resp = list_subsequent(next_listscript, selected_resp)
                    selected_resp = present_list(resp, next_listid)
                    next_listscript, next_listid = get_next_listscript(
                        next_listscript)
                action(selected_resp)
    except AbortWorkflowRequestLoop:
        errprint('Aborted')


class NextWorkflowRequest(Exception):
    pass


class AbortWorkflowRequestLoop(Exception):
    pass


def prompt_wf():
    os.chdir(basedir)
    find_args = [
        'find', '.', '-mindepth', '1', '-maxdepth', '1', '-type', 'd', '-not',
        '-name', '__pycache__'
    ]
    with subprocess.Popen(
            find_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True) as fd:
        try:
            fd_out, _ = fd.communicate(timeout=5)
        except subprocess.TimeoutExpired as err:
            errprint('Failed to query workflows')
            raise AbortWorkflowRequestLoop from err
    fd_out = get_list_of_output(fd_out)
    fd_out = [x[:-1] if x.endswith('/') else x for x in fd_out]
    fd_out = [x[2:] if x.startswith('./') else x for x in fd_out]

    try:
        fzf_out = subprocess.run(['fzf', '--prompt', 'wf> '],
                                 text=True,
                                 input=''.join(x + '\n' for x in fd_out),
                                 stdout=subprocess.PIPE,
                                 check=True).stdout
    except subprocess.CalledProcessError as err:
        raise AbortWorkflowRequestLoop from err
    fzf_out = get_list_of_output(fzf_out)
    if not fzf_out:
        raise AbortWorkflowRequestLoop
    return fzf_out[0]


def list_requesting_arg():
    resp = []
    while not resp:
        try:
            arg = input('arg> ').strip()
        except (EOFError, KeyboardInterrupt) as err:
            raise NextWorkflowRequest from err
        with subprocess.Popen(['./list', arg],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True) as ls:
            try:
                ls_out, _ = ls.communicate(timeout=resp_timeout)
            except subprocess.TimeoutExpired as err:
                errprint('Failed to give response within timeout')
                raise NextWorkflowRequest from err
        try:
            resp.extend(json.loads(ls_out)['items'])
        except json.JSONDecodeError as err:
            errprint('response is not valid json')
            raise NextWorkflowRequest from err
        except KeyError as err:
            errprint('response is not valid Alfred json')
            raise NextWorkflowRequest from err
        if not resp:
            errprint('No response is generated')

    resp = list(filter(type_filter, resp))
    dump_resp(resp)
    return resp


def list_no_arg():
    resp = []
    with subprocess.Popen(['./list'],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          text=True) as ls:
        try:
            ls_out, _ = ls.communicate(timeout=resp_timeout)
        except subprocess.TimeoutExpired as err:
            errprint('Failed to give response within timeout')
            raise NextWorkflowRequest from err
    try:
        resp.extend(json.loads(ls_out)['items'])
    except json.JSONDecodeError as err:
        errprint('response is not valid json')
        raise NextWorkflowRequest from err
    except KeyError as err:
        errprint('response is not valid Alfred json')
        raise NextWorkflowRequest from err
    if not resp:
        errprint('No response is generated')
        raise NextWorkflowRequest

    resp = list(filter(type_filter, resp))
    dump_resp(resp)
    return resp


def list_subsequent(curr_listscript, selected_resp):
    args = ['./' + curr_listscript]
    if selected_resp is not None:
        if isinstance(selected_resp, list):
            args.extend(selected_resp)
        else:
            args.append(selected_resp)
    resp = []
    with subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True) as ls:
        try:
            ls_out, _ = ls.communicate(timeout=resp_timeout)
        except subprocess.TimeoutExpired as err:
            errprint('Failed to give response within timeout')
            raise NextWorkflowRequest from err
    try:
        resp.extend(json.loads(ls_out)['items'])
    except json.JSONDecodeError as err:
        errprint('response is not valid json')
        raise NextWorkflowRequest from err
    except KeyError as err:
        errprint('response is not valid Alfred json')
        raise NextWorkflowRequest from err
    if not resp:
        errprint('No response is generated')
        raise NextWorkflowRequest

    resp = list(filter(type_filter, resp))
    dump_resp(resp)
    return resp


def type_filter(item):
    try:
        if item.get('type', None) == 'file':
            return os.path.exists(item.get('match', item['title']))
    except KeyError as err:
        errprint('response is not valid Alfred json')
        raise NextWorkflowRequest from err
    return True


def dump_resp(resp):
    with open(listfile, 'w', encoding='utf-8') as outfile:
        json.dump(resp, outfile)


def get_next_listscript(name):
    assert name.startswith('list')
    listid = name[4:]
    if not listid:
        next_listid = 1
    else:
        next_listid = int(listid) + 1
    next_listid = str(next_listid)
    next_name = 'list' + next_listid
    return next_name if os.path.isfile(next_name) else None, next_listid


def present_list(items, listid: str = None):
    try:
        with open(listfile, encoding='utf-8') as infile:
            items = json.load(infile)
    except FileNotFoundError as err:
        errprint('Response cache of current session not found')
        raise NextWorkflowRequest from err
    try:
        titles = [x['title'] for x in items]
    except KeyError as err:
        errprint('response is not valid Alfred json')
        raise NextWorkflowRequest from err

    fzf_args = ['fzf', '--prompt']
    fzf_args.append('resp{}> '.format(listid) if listid else 'resp> ')
    fzf_args.extend([
        '--select-1',  # conditional skip certain steps
        '--preview',
        ('jq --arg title {{}} -r '
         '".[] | select(.title == \\$title).subtitle // empty" {} '
         '| fold -w $FZF_PREVIEW_COLUMNS -s').format(shlex.quote(listfile)),
    ])
    try:
        fzf_out = subprocess.run(
            fzf_args,
            text=True,
            input=''.join(x + '\n' for x in titles),
            stdout=subprocess.PIPE,
            check=True).stdout
    except subprocess.CalledProcessError as err:
        raise NextWorkflowRequest from err
    fzf_out = get_list_of_output(fzf_out)
    if not fzf_out:
        raise NextWorkflowRequest
    return items[titles.index(fzf_out[0])].get('arg', None)


def action(selected_resp):
    args = ['./action']
    if selected_resp is not None:
        if isinstance(selected_resp, list):
            args.extend(selected_resp)
        else:
            args.append(selected_resp)
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as err:
        errprint('Action returns nonzero code:', err.returncode)


def errprint(*args, **kwargs):
    print('***', *args, **kwargs)


def get_list_of_output(output: str):
    return list(filter(None, map(str.strip, output.split('\n'))))


if __name__ == '__main__':
    main()
