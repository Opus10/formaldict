"""
Tests for the formaldict.core module
"""
import datetime as dt
from unittest import mock

import kmatch
import prompt_toolkit.formatted_text
import prompt_toolkit.validation
import pytest

from formaldict import core
from formaldict import exceptions


@pytest.fixture()
def basic_schema():
    yield core.Schema(
        [
            {'type': 'string', 'label': 'name'},
            {'type': 'string', 'label': 'description'},
        ]
    )


@pytest.mark.parametrize(
    'input_text',
    [
        'valid_text',
        pytest.param(  # No input will result in error since field is required
            '',
            marks=pytest.mark.xfail(
                raises=prompt_toolkit.validation.ValidationError
            ),
        ),
    ],
)
def test_value_validator_validate(mocker, basic_schema, input_text):
    """
    Tests core._ValueValidator.validate by validating the "name"
    attribute of the basic_schema fixture
    """
    validator = core._ValueValidator(schema=basic_schema, label='name')
    validator.validate(mocker.Mock(text=input_text))


def test_errors():
    """
    Tests core methods of the Errors class
    """
    errors = core.Errors()
    errors.add('Non-field error.')
    errors.add(ValueError('Name error.'), label='name')
    errors.add(ValueError('Description error.'), label='description')

    assert len(errors) == 3
    assert errors['__all__'] == ['Non-field error.']
    assert list(errors) == ['__all__', 'name', 'description']
    assert str(errors) == (
        'Non-field error. name: Name error. description: Description error.'
    )


@pytest.mark.parametrize(
    'data, parsed, errors, expected_is_valid',
    [
        ({'my': 'data'}, {'parsed': 'data', 'my': 'data'}, {}, True),
        ({'my': 'data'}, {'parsed': 'data'}, {'some': 'errors'}, False),
    ],
)
def test_formaldict(data, parsed, errors, expected_is_valid, basic_schema):
    """
    Tests core methods of the FormalDict class
    """
    errors_obj = core.Errors()
    for key, value in errors.items():
        errors_obj.add(value, label=key)

    formal_d = core.FormalDict(
        data=data, parsed=parsed, errors=errors_obj, schema=basic_schema
    )

    assert formal_d == parsed
    assert formal_d.parsed == parsed
    assert formal_d.data == data
    assert formal_d.errors == errors_obj
    assert len(formal_d) == len(parsed)
    assert list(formal_d) == list(parsed)
    for key in parsed:  # Verify __getitem__
        assert parsed[key] == formal_d[key]
    assert formal_d.is_valid == expected_is_valid


def test_schema_magic_methods():
    """
    Tests primary magic methods on Schema that make it behave like a dict
    """
    s = core.Schema([{'label': 'hello'}, {'label': 'world'}])
    assert 'hello' in s
    assert s[0]['label'] == 'hello'
    assert s['hello']['label'] == 'hello'
    assert len(s) == 2


@pytest.mark.parametrize(
    'schema, clean_schema',
    [
        pytest.param(  # Schema must have labels for each element
            [{}], None, marks=pytest.mark.xfail(raises=ValueError)
        ),
        pytest.param(  # Cannot have duplicate labels
            [{'label': 'hi'}, {'label': 'hi'}],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # Cannot have both "matches" and "choices"
            [{'label': 'hi', 'matches': 'pattern', 'choices': ['a']}],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # Conditions must match labels in schema
            [{'label': 'hi', 'condition': ['==', 'invalid_label', 'value']}],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # Conditions can only reference labels from prev steps
            [
                {'label': 'hi', 'condition': ['==', 'future_step', 'value']},
                {'label': 'future_step'},
            ],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # Create a valid condition pattern
            [
                {'label': 'first_step'},
                {'label': 'hi', 'condition': ['==', 'first_step', 'value']},
            ],
            [
                {
                    'choices': None,
                    'condition': None,
                    'default': '',
                    'help': '',
                    'label': 'first_step',
                    'matches': None,
                    'multiline': False,
                    'name': 'First Step',
                    'required': True,
                    'type': 'string',
                },
                {
                    'choices': None,
                    'condition': mock.ANY,  # Kmatch object is asserted in test
                    'default': '',
                    'help': '',
                    'label': 'hi',
                    'matches': None,
                    'multiline': False,
                    'name': 'Hi',
                    'required': True,
                    'type': 'string',
                },
            ],
        ),
        pytest.param(  # Test filling in all defaults for strings
            [{'label': 'a_nice_label'}],
            [
                {
                    'choices': None,
                    'condition': None,
                    'default': '',
                    'help': '',
                    'label': 'a_nice_label',
                    'matches': None,
                    'multiline': False,
                    'name': 'A Nice Label',
                    'required': True,
                    'type': 'string',
                }
            ],
        ),
        pytest.param(  # Test filling in all defaults for non-strings
            [{'label': 'a_nice_label', 'type': 'datetime'}],
            [
                {
                    'condition': None,
                    'default': None,
                    'help': '',
                    'label': 'a_nice_label',
                    'multiline': False,
                    'name': 'A Nice Label',
                    'required': True,
                    'type': 'datetime',
                }
            ],
        ),
        pytest.param(  # Ensure defaults don't override custom values
            [
                {
                    'choices': ['a', 'b', 'c'],
                    'condition': None,
                    'default': 'default',
                    'help': 'help',
                    'label': 'a',
                    'matches': None,
                    'multiline': True,
                    'name': 'A name',
                    'required': False,
                    'type': 'string',
                }
            ],
            [
                {
                    'choices': ['a', 'b', 'c'],
                    'condition': None,
                    'default': 'default',
                    'help': 'help',
                    'label': 'a',
                    'matches': None,
                    'multiline': True,
                    'name': 'A name',
                    'required': False,
                    'type': 'string',
                }
            ],
        ),
    ],
)
def test_schema_init(schema, clean_schema):
    """
    Verifies initializing a schema
    """
    s = core.Schema(schema)
    assert s._schema == clean_schema

    for schema_entry in s:
        if schema_entry['condition']:
            assert isinstance(schema_entry['condition'], kmatch.K)


@pytest.mark.parametrize(
    'schema, input, expected_output',
    [
        ([{'label': 'hello'}], '1', '1'),
        ([{'label': 'hello'}], 1, '1'),
        ([{'label': 'hello'}], dt.datetime(2019, 1, 1), '2019-01-01 00:00:00'),
        (
            [{'label': 'hello', 'matches': 'pattern.*'}],
            'pattern_match',
            'pattern_match',
        ),
        pytest.param(
            [{'label': 'hello', 'matches': 'pattern'}],
            'invalid',
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
        pytest.param(
            [{'label': 'hello', 'matches': r'\d{4}'}],
            '55555',
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
        ([{'label': 'hello', 'choices': ['a', 'b']}], 'a', 'a'),
        pytest.param(
            [{'label': 'hello', 'choices': ['a', 'b']}],
            'invalid_choice',
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
    ],
)
def test_parse_string(schema, input, expected_output):
    """
    Tests Schema.parse_string()
    """
    s = core.Schema(schema)
    assert s.parse_string('hello', input) == expected_output


@pytest.mark.parametrize(
    'input, expected_output',
    [
        (1578019337, dt.datetime(2020, 1, 3, 2, 42, 17)),
        pytest.param(
            157801933700000,
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
        ('2019-01-01 12:00:00', dt.datetime(2019, 1, 1, 12)),
        (dt.datetime(2019, 1, 1), dt.datetime(2019, 1, 1)),
        pytest.param(
            'invalid',
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
        pytest.param(
            1.1,
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
    ],
)
def test_parse_datetime(input, expected_output):
    """
    Tests Schema.parse_string()
    """
    s = core.Schema([{'type': 'datetime', 'label': 'hello'}])
    assert s.parse_datetime('hello', input) == expected_output


@pytest.mark.parametrize(
    'schema, input, expected_output',
    [
        ([{'label': 'hello'}], ' 1 ', '1'),  # Strings are stripped
        ([{'label': 'hello'}], 1, '1'),  # Ensure non-strings aren't stripped
        pytest.param(  # Fields are required by default
            [{'label': 'hello'}],
            '',
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
        (  # Ensure defaults are returned on empty input
            [{'label': 'hello', 'default': 'd'}],
            ' ',
            'd',
        ),
        (  # Ensure empty non-required fields are returned
            [{'label': 'hello', 'required': False}],
            ' ',
            '',
        ),
        (  # Empty non-strings return None
            [{'label': 'hello', 'type': 'datetime', 'required': False}],
            ' ',
            None,
        ),
        (
            [{'label': 'hello', 'type': 'datetime'}],
            ' 2019-01-01',
            dt.datetime(2019, 1, 1),
        ),
        pytest.param(  # Try an unsupported type
            [{'label': 'hello', 'type': 'invalid'}],
            ' 2019-01-01 ',
            None,
            marks=pytest.mark.xfail(raises=exceptions.ValidationError),
        ),
    ],
)
def test_parse_entry(schema, input, expected_output):
    """
    Tests Schema.parse_string()
    """
    s = core.Schema(schema)
    assert s._parse_entry('hello', input) == expected_output


@pytest.mark.parametrize(
    'schema, strict, data, expected_output, expected_errors',
    [
        pytest.param(  # Valid parsing of simple schema without strict mode
            [{'label': 'a_nice_label'}],
            False,
            {'a_nice_label': 'my_data', 'additonal_label': 'additonal'},
            {'a_nice_label': 'my_data'},
            '',
        ),
        pytest.param(  # Invalid parsing of simple schema with strict mode
            [{'label': 'a_nice_label'}],
            True,
            {'a_nice_label': 'my_data', 'additonal_label': 'additonal'},
            {'a_nice_label': 'my_data'},
            'Labels "additonal_label" not present in schema.',
        ),
        pytest.param(  # Valid parsing of simple schema with strict mode
            [{'label': 'a_nice_label'}],
            True,
            {'a_nice_label': 'my_data'},
            {'a_nice_label': 'my_data'},
            '',
        ),
        pytest.param(  # Invalid parsing of data
            [{'label': 'label', 'choices': ['a']}],
            False,
            {'label': 'd'},
            {},
            'label: Value "d" not a valid choice. Possible choices: "[\'a\']".',
        ),
        pytest.param(  # Valid parsing with passing condition
            [
                {'label': 'l1', 'choices': ['a']},
                {'label': 'l2', 'condition': ['==', 'l1', 'a']},
            ],
            True,
            {'l1': 'a', 'l2': 1},
            {'l1': 'a', 'l2': '1'},
            '',
        ),
        pytest.param(  # Valid parsing with failing condition
            [
                {'label': 'l1', 'choices': ['a', 'b']},
                {'label': 'l2', 'condition': ['==', 'l1', 'a']},
            ],
            False,
            {'l1': 'b', 'l2': 1},
            {'l1': 'b'},
            '',
        ),
        pytest.param(  # Invalid parsing with strict failing condition
            [
                {'label': 'l1', 'choices': ['a', 'b']},
                {'label': 'l2', 'condition': ['==', 'l1', 'a']},
            ],
            True,
            {'l1': 'b', 'l2': 1},
            {'l1': 'b'},
            'Labels "l2" failed conditions in schema.',
        ),
    ],
)
def test_parse(schema, strict, data, expected_output, expected_errors):
    """
    Tests Schema.parse()
    """
    s = core.Schema(schema)
    parsed = s.parse(data, strict=strict)
    assert parsed.parsed == expected_output
    assert str(parsed.errors) == expected_errors


@pytest.mark.parametrize(
    'schema, expected_help_text',
    [
        ([{'label': 'a'}], ''),  # No help text
        ([{'label': 'a', 'required': False}], '<i>Optional.</i>'),
        ([{'label': 'a', 'matches': 'p'}], '<i>Matches: p.</i>'),
        (
            [{'label': 'a', 'choices': ['a', 'b']}],
            "<i>Choices: ['a', 'b'].</i>",
        ),
        (
            [{'label': 'a', 'choices': ['a', 'b'], 'multiline': True}],
            "<i>Choices: ['a', 'b'].</i> "
            '<i>Hit ESC and Enter to finish input.</i>',
        ),
    ],
)
def test_get_help_text(schema, expected_help_text):
    """Tests Schema._get_help_text"""
    s = core.Schema(schema)
    assert s._get_help_text('a') == expected_help_text


@pytest.mark.parametrize(
    'schema, expected_prompt_text',
    [
        ([{'label': 'a', 'name': 'NAME'}], 'NAME: '),  # Default prompt text
        ([{'label': 'a', 'multiline': True}], 'A: \n> '),
    ],
)
def test_get_prompt_text(schema, expected_prompt_text):
    """Tests Schema._get_prompt_text"""
    s = core.Schema(schema)
    assert s._get_prompt_text('a') == expected_prompt_text


@pytest.mark.parametrize(
    'schema, defaults, prompt_return, expected_prompts',
    [
        pytest.param(  # Simple schema where valid data is entered
            [{'label': 'a'}],
            {},
            ['input_for_a'],
            [
                mock.call(
                    'A: ',
                    bottom_toolbar=mock.ANY,
                    completer=None,
                    default='',
                    multiline=False,
                    prompt_continuation='> ',
                    validate_while_typing=False,
                    validator=mock.ANY,
                )
            ],
        ),
        pytest.param(  # Simple schema where defaults are used
            [{'label': 'a', 'default': 'b'}],
            {},
            ['input_for_a'],
            [
                mock.call(
                    'A: ',
                    bottom_toolbar=mock.ANY,
                    completer=None,
                    default='b',
                    multiline=False,
                    prompt_continuation='> ',
                    validate_while_typing=False,
                    validator=mock.ANY,
                )
            ],
        ),
        pytest.param(  # Simple schema where defaults are overridden
            [{'label': 'a', 'default': 'b'}],
            {'a': 'new_default'},
            ['input_for_a'],
            [
                mock.call(
                    'A: ',
                    bottom_toolbar=mock.ANY,
                    completer=None,
                    default='new_default',
                    multiline=False,
                    prompt_continuation='> ',
                    validate_while_typing=False,
                    validator=mock.ANY,
                )
            ],
        ),
        pytest.param(  # Unrequired input
            [{'label': 'a', 'required': False}],
            {},
            [''],
            [
                mock.call(
                    'A: ',
                    bottom_toolbar=mock.ANY,
                    completer=None,
                    default='',
                    multiline=False,
                    prompt_continuation='> ',
                    validate_while_typing=False,
                    validator=mock.ANY,
                )
            ],
        ),
        pytest.param(  # When a condition passes
            [{'label': 'a'}, {'label': 'b', 'condition': ['==', 'a', '3']}],
            {},
            ['3', 'b'],
            [
                mock.call(
                    'A: ',
                    bottom_toolbar=mock.ANY,
                    completer=None,
                    default='',
                    multiline=False,
                    prompt_continuation='> ',
                    validate_while_typing=False,
                    validator=mock.ANY,
                ),
                mock.call(
                    'B: ',
                    bottom_toolbar=mock.ANY,
                    completer=None,
                    default='',
                    multiline=False,
                    prompt_continuation='> ',
                    validate_while_typing=False,
                    validator=mock.ANY,
                ),
            ],
        ),
        pytest.param(  # When a condition doesn't pass
            [{'label': 'a'}, {'label': 'b', 'condition': ['==', 'a', '3']}],
            {},
            ['input_for_a'],
            [
                mock.call(
                    'A: ',
                    bottom_toolbar=mock.ANY,
                    completer=None,
                    default='',
                    multiline=False,
                    prompt_continuation='> ',
                    validate_while_typing=False,
                    validator=mock.ANY,
                )
            ],
        ),
    ],
)
def test_prompt(schema, defaults, prompt_return, expected_prompts, mocker):
    """
    Tests Schema.prompt().

    NOTE (@wesleykendall) - It is very difficult to patch out user input
    and also run prompt toolkit's prompting within pytest. We test that
    python prompt toolkit is being called correctly and assume prompt
    toolkit is working as intended.
    """
    mocked_prompt = mocker.patch(
        'prompt_toolkit.prompt', autospec=True, side_effect=prompt_return
    )
    s = core.Schema(schema)
    s.prompt(defaults=defaults)

    assert mocked_prompt.call_args_list == expected_prompts
