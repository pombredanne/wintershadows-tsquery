import codecs
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
import tree_sitter as ts

from tsquery.parser_registry import ParserRegistry, ParserUnavailable


def extract_node(node: ts.Node, source: bytes) -> bytes:
    return source[node.start_byte : node.end_byte]


def war(msg: str) -> None:
    click.echo(msg, err=True)


def die(status: int, msg: str) -> None:
    war(msg)
    sys.exit(status)


# TODO:
#   * Read from query file with '-f/--query-file' instead of requiring it
#     to be provided on stdin:
#       tsquery -l cpp -f query.scm < src/foo.cpp

@click.command('tsquery')
@click.option('-l', '--language', default=None)
@click.option('-e', '--encoding', default='utf-8')
@click.option('--list-parsers', is_flag=True, default=False)
@click.argument('query_text')
@click.argument('input_files', nargs=-1, type=click.Path(exists=True, dir_okay=False))
def cli(language: str, encoding: str, query_text: str, list_parsers: bool, input_files: Tuple[Optional[str]]) -> None:
    if list_parsers:
        for f in registry.iter_available():
            click.echo(str(f))
        sys.exit()

    registry = ParserRegistry()

    # When looping over input filenames, `None` means "read from stdin"
    if len(input_files) == 0:
        input_files = (None,)

    for input_file in input_files:
        if language is None:
            if input_file is None:
                die(3, '-l/--language option is required when reading from stdin.')
            language = Path(input_file).suffix[1:].lower()

        if input_file is None:
            source_bytes = click.get_binary_stream('stdin').read()
        else:
            with open(input_file, 'rb') as fp:
                source_bytes = fp.read()

        try:
            captures = registry.query(language, query_text, source_bytes)
        except ParserUnavailable as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)
        except SyntaxError as exc:
            click.echo(f'Invalid query syntax: {exc!s}', err=True)
            sys.exit(2)
        else:
            input_file_for_display = input_file or '(standard input)'
            for i, (node, name) in enumerate(captures):
                node_source = codecs.decode(extract_node(node, source_bytes), encoding=encoding, errors='surrogateescape')
                if i > 0:
                    click.echo('')
                click.echo(f'{input_file_for_display}:{name}\n{node_source}')