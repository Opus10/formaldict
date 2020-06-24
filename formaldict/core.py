"""
The ``formaldict`` module contains objects for parsing
and validating structured dictionaries from a schema.

This module contains the `Schema`, the parsed
`FormalDict`, and the `Errors` from any parsing/validation failures

.. note::

    The ``formaldict`` module will eventually be its own library.
"""
import collections.abc
import copy
import datetime as dt
import re

import dateutil.parser
import kmatch
import prompt_toolkit
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
import prompt_toolkit.validation

from . import exceptions


class _ValueValidator(prompt_toolkit.validation.Validator):
    """
    Custom validator class for prompt_toolkit. Performs validation
    on input in the same way schemas are validated
    """

    def __init__(self, *args, schema=None, label=None, **kwargs):
        self._schema = schema
        self._label = label
        super().__init__(*args, **kwargs)

    def validate(self, document):
        text = document.text
        try:
            self._schema._parse_entry(self._label, text)
        except exceptions.ValidationError as exc:
            raise prompt_toolkit.validation.ValidationError(
                message=str(exc), cursor_position=len(text)
            )


class Errors(collections.abc.Mapping):
    """
    Collects errors found when validating a `Schema`
    """

    def __init__(self):
        self._errors = collections.defaultdict(list)

    def add(self, exc, label='__all__'):
        self._errors[label].append(exc)

    def __getitem__(self, label):
        return self._errors[label]

    def __len__(self):
        return len(self._errors)

    def __iter__(self):
        return iter(self._errors)

    def __str__(self):
        return (
            ' '.join(str(error) for error in self._errors['__all__'])
            + ' '
            + ' '.join(
                f'{label}: {error}'
                for label, errors in self._errors.items()
                if label != '__all__'
                for error in errors
            )
        ).strip()


class FormalDict(collections.abc.Mapping):
    """
    A formal dictionary of data associated with a `Schema`.

    Formal dictionaries can be created two ways::

        1. Schema(...).parse(data)
        2. Schema(...).prompt()

    After creation, attributes from the `Schema` can be accessed as
    attributes on the dictionary.
    """

    def __init__(self, *, schema, parsed, data, errors):
        assert isinstance(parsed, dict)
        assert isinstance(schema, Schema)
        assert isinstance(errors, Errors)

        self._schema = schema
        self._data = data
        self._parsed = parsed
        self._errors = errors

    def __getitem__(self, label):
        return self._parsed[label]

    def __len__(self):
        return len(self._parsed)

    def __iter__(self):
        return iter(self._parsed)

    @property
    def data(self):
        """The raw data used when constructing the formal dictionary"""
        return self._data

    @property
    def parsed(self):
        """The parsed "formal" data.

        Accessing the dictionary (i.e. data[key]) returns parsed data
        """
        return self._parsed

    @property
    def errors(self):
        """
        Returns an Errors class if any errors happened during parsing
        """
        return self._errors

    @property
    def is_valid(self):
        """
        True if the dictionary is valid and all attributes are present
        from the schema
        """
        return not self.errors


class Schema(collections.abc.Sequence):
    """
    The `Schema` object provides a definition of structured data
    and associated methods to parse and validate structured data.

    Below is an example of a schema that represents a "name" and a
    "description"::

        schema = Schema([{
            'label': 'description'
        }, {
            'label': 'name'
        }])

    Each schema entry requires the "label", a unique ID for the attribute
    being parsed, and a "type" that specifies the type of data being parsed.

    After declaring the schema, one can parse dictionaries with
    ``Schema.parse()``. For example::

        data = schema.parse({'description': 'My Description', 'name': 'John'})

    In the above, ``data`` is a `FormalDict` object, which can be accessed
    as a dictionary. If ``data.is_valid`` is ``True``, it means that the data
    passed schema validation and was successfully parsed. ``data.errors``
    will contain all of the schema errors that were found.

    The `Schema` object directly integrates with
    `python-prompt-toolkit <https://github.com/prompt-toolkit/python-prompt-toolkit>`_,
    allowing one to prompt for information based on the schema.

    For example::

        data = schema.prompt()

    The above will result in the user being prompted for all attributes in
    the schema in the order in which they were defined. Any data that passes
    the prompt will also pass the schema validation, ensuring that valid
    data is always returned from prompting.

    The `Schema` object provides the ability to configure prompt help text,
    multi-line input, and parsing other types of data. See more examples
    below, which provide more information on schema attributes.

    Examples:

        The schema below obtains a formal dictionary with information about a
        person - a name, address, marital status, and date of birth::

            schema = Schema([{
                # The label is required and is the resulting key in the formal
                # dictionary
                'label': 'name',

                # The name is a human-readable description of the label. It is used
                # when prompting the user for the information. It defaults to
                # a title-ized version of the label.
                'name': 'Full Name',

                # The help is displayed when prompting the user.
                'help': 'Your full name (first, middle, and last).'

                # The type defaults to string. Currently formaldict supports
                # string and datetime types.
                'type': 'string'
            }, {
                'label': 'address',
                'help': 'Enter your street, city, state, and zipcode',

                # The multiline attribute turns on multi-line mode when
                # prompting the user.
                'multiline': True
            }, {
                'label': 'marital_status',
                'help': 'Your current marital status.',

                # The user is only allowed to enter the provided choices.
                'choices': [
                    'single', 'separated', 'widowed', 'divorced', 'married'
                ],
            }, {
                'label': 'dob',
                'name': 'Date of Birth',
                'help': 'Your birthday (YYYY/MM/DD)',

                # datetime types are parsed either as integers (unix timestamps)
                # or by any format accepted by dateutil
                # (https://dateutil.readthedocs.io/en/stable/)
                'type': 'datetime',

                # Everything is required by default.
                'required': False,
            }])

        .. note::

            When declaring a schema, the order of entries will be the order
            in which the user is prompted for information.

        Schemas allow conditional collection of information. For example,
        say that you want to create a schema where the user enters Jira
        ticket numbers and extended descriptions for all non-trivial types of
        changes to a project::

            schema = Schema([
                'label': 'type',
                'help': 'The type of change being committed',
                'choices': ['bug', 'feature', 'trivial'],
            }, {
                'label': 'description',
                'multiline': True,
                'help': 'An extended description of the change.',

                # Conditions are kmatch patterns
                # (https://github.com/ambitioninc/kmatch)
                # that must validate against the labels in previous steps.
                # This kmatch pattern asserts that we only collect
                # the description if the "type" entered by the user
                # is not the "trivial" choice.
                'condition': ['!=', 'type', 'trivial']
            }, {
                'label': 'jira',
                'help': 'The Jira ticket number',
                'condition': ['!=', 'type', 'trivial'],

                # Use a regex for validating input.
                'matches': 'PROJ-\\d+'
            }])

        In the above, the user would not be prompted for the "description" and
        "jira" steps if they entered "trivial" as the type of change.
        Similarly, one must enter a proper Jira ticket in order to pass
        the parsing of information. Here are some examples of parsing payloads
        that fail the schema::

            # The jira ticket is not required for trivial changes. Remember,
            # the "strict" flag verifies that all keys in the payload
            # match keys that are required (or conditionally required) by
            # the schema.
            schema.parse({
                'type': 'trivial',
                'jira': 'PROJ-111'
            }, strict=True)

            # The jira ticket is required, but it does not match the pattern.
            schema.parse({
                'type': 'bug',
                'description': 'Description of bug'
                'jira': 'invalid-ticket'
            })
    """

    def __init__(self, schema):
        """
        Initialize the schema object

        Args:
            schema (dict): Schema rules
        """
        assert isinstance(schema, (list, tuple))

        # Keep a copy of the original raw schema given by the user
        self._raw_schema = copy.deepcopy(schema)

        # Instantiate the cleaned schema (i.e. self._schema)
        self._clean()

    def __contains__(self, label):
        return label in self._entry_schemas

    def __getitem__(self, index):
        if isinstance(index, int):
            return self._schema[index]
        else:
            return self._entry_schemas[index]

    def __len__(self):
        return len(self._schema)

    def __iter__(self):
        return iter(self._schema)

    def _fill_defaults(self):
        """
        Fill out the entire schema with defaults (e.g. ``required``, ``name``,
        and other attributes in the schema).
        """
        schema_with_defaults = []
        for entry_schema in self._schema:
            default_entry_schema = {
                'label': '',
                'condition': None,
                'required': True,
                'name': (
                    entry_schema.get('label', '').replace('_', ' ').title()
                ),
                'help': '',
                'type': 'string',
                'multiline': False,
            }

            if entry_schema.get('type', 'string') == 'string':
                default_entry_schema = {
                    **{'matches': None, 'choices': None, 'default': ''},
                    **default_entry_schema,
                }
            else:
                default_entry_schema = {
                    **{'default': None},
                    **default_entry_schema,
                }

            schema_with_defaults.append(
                {**default_entry_schema, **entry_schema}
            )

        self._schema = schema_with_defaults

    def _clean(self):
        """Cleans the schema and ensures it is valid"""
        self._schema = copy.deepcopy(self._raw_schema)
        self._entry_schemas = {}

        self._fill_defaults()

        for entry_schema in self:
            label = entry_schema.get('label')

            if not label:
                raise ValueError(
                    f'Label not supplied for schema element {entry_schema}'
                )

            if label in self._entry_schemas:
                raise ValueError(
                    f'Multiple declarations for label "{label}" in schema'
                )

            if (
                entry_schema['type'] == 'string'
                and entry_schema['matches']
                and entry_schema['choices']
            ):
                raise ValueError(
                    'Cannot have both "matches" and "choices" for a string'
                )

            if entry_schema['condition'] is not None:
                condition = kmatch.K(
                    entry_schema['condition'], suppress_key_errors=True
                )
                for condition_label in condition.get_field_keys():
                    if condition_label not in self._entry_schemas:
                        raise ValueError(
                            f'Invalid label "{condition_label}" in condition'
                            f' for "{label}". Labels in conditions'
                            ' can only reference labels declared'
                            ' in previous steps.'
                        )

                entry_schema['condition'] = condition

            # Keep a running list of entries that have been seen. This
            # helps us validate if conditions only reference previous steps
            self._entry_schemas[label] = entry_schema

    def parse_string(self, label, value):
        value = str(value)

        if self[label]['matches'] and not re.fullmatch(
            self[label]['matches'], value
        ):
            raise exceptions.ValidationError(
                f'Value "{value}" does not match'
                f' pattern "{self[label]["matches"]}".'
            )
        elif self[label]['choices'] and value not in self[label]['choices']:
            raise exceptions.ValidationError(
                f'Value "{value}" not a valid'
                f' choice. Possible choices: "{self[label]["choices"]}".'
            )

        return value

    def parse_datetime(self, label, value):
        if not isinstance(value, dt.datetime):
            if isinstance(value, int):
                try:
                    value = dt.datetime.utcfromtimestamp(value)
                except Exception as exc:
                    raise exceptions.ValidationError(
                        f'Cannot parse datetime integer "{value}"'
                    ) from exc
            elif isinstance(value, str):
                try:
                    value = dateutil.parser.parse(value)
                except dateutil.parser.ParserError as exc:
                    raise exceptions.ValidationError(
                        f'Cannot automatically parse datetime string "{value}"'
                    ) from exc
            else:
                raise exceptions.ValidationError(
                    f'Cannot parse type "{type(value)}" into datetime'
                )

        return value

    def _parse_entry(self, label, value):
        """
        Parse the value based on the schema. Raise a ValidationError if any
        validation error occurs.
        """
        if isinstance(value, str):
            value = value.strip()

        if not value:
            value = self[label]['default']

        if self[label]['required'] and not value:
            raise exceptions.ValidationError('This field is required.')
        elif not self[label]['required'] and not value:
            return value

        if self[label]['type'] == 'string':
            value = self.parse_string(label, value)
        elif self[label]['type'] == 'datetime':
            value = self.parse_datetime(label, value)
        else:
            raise exceptions.ValidationError(
                f'Schema type "{self[label]["type"]}" not supported.'
            )

        return value

    def passes_condition(self, entry_schema, data):
        if entry_schema['condition'] is None:
            return True
        elif isinstance(entry_schema['condition'], bool):
            return entry_schema['condition']
        else:
            return entry_schema['condition'].match(data)

    def parse(self, data, strict=False):
        """
        Parse data based on the schema.

        Args:
            strict (boolean, default=False): If True, add a
                ValidationError to self.errors if any keys in the entry
                are not present in the schema.

        Returns:
            dict: The parsed data

        Todo:
            Allow passing in default values to override any defaults in the
            schema.
        """
        parsed = {}
        errors = Errors()
        condition_failed_labels = set()
        for entry_schema in self:
            try:
                label = entry_schema['label']
                if not self.passes_condition(entry_schema, parsed):
                    condition_failed_labels.add(label)
                    continue

                parsed[label] = self._parse_entry(label, data.get(label))
            except exceptions.ValidationError as exc:
                errors.add(exc, label=label)

        non_extant_labels = set(data.keys()) - set(self._entry_schemas.keys())
        if strict and non_extant_labels:
            err_msg = (
                f'Labels "'
                + ', '.join(non_extant_labels)
                + '" not present in schema.'
            )
            errors.add(exceptions.ValidationError(err_msg))

        condition_failed_labels = set(data.keys()) & condition_failed_labels
        if strict and condition_failed_labels:
            err_msg = (
                f'Labels "'
                + ', '.join(condition_failed_labels)
                + '" failed conditions in schema.'
            )
            errors.add(exceptions.ValidationError(err_msg))

        return FormalDict(schema=self, parsed=parsed, data=data, errors=errors)

    def _get_help_text(self, label):
        """
        Get the help text for prompted input
        """
        entry_schema = self[label]
        provided_help = entry_schema["help"]
        help_text = f'<b>{provided_help}</b> ' if provided_help else ''

        if not entry_schema['required']:
            help_text += f'<i>Optional.</i> '

        if entry_schema['choices']:
            help_text += f'<i>Choices: {entry_schema["choices"]}.</i> '
        elif entry_schema['matches']:
            help_text += f'<i>Matches: {entry_schema["matches"]}.</i> '

        if entry_schema['multiline']:
            help_text += '<i>Hit ESC and Enter to finish input.</i> '

        return help_text.strip()

    def _get_prompt_text(self, label):
        """
        Get the prompt text
        """
        entry_schema = self[label]
        prompt_text = f'{entry_schema["name"]}: '
        if entry_schema['multiline']:
            prompt_text += '\n> '

        return prompt_text

    def prompt(self, defaults=None):
        """
        Prompt for input of all entries in the schema

        Args:
            defaults (dict, default=None): Default values for the schema
                that should be used in place of any other declared defaults

        Returns:
            dict: The parsed information, which also validates against the
            `Schema`.
        """
        defaults = defaults or {}
        data = {}

        for entry_schema in self:
            if not self.passes_condition(entry_schema, data):
                continue

            label = entry_schema['label']
            choices = entry_schema.get('choices')
            help_text = self._get_help_text(entry_schema['label'])
            prompt_text = self._get_prompt_text(entry_schema['label'])
            validator = _ValueValidator(schema=self, label=label)

            value = prompt_toolkit.prompt(
                prompt_text,
                bottom_toolbar=HTML(help_text) if help_text else None,
                completer=WordCompleter(choices) if choices else None,
                default=defaults.get(label, entry_schema['default']),
                validator=validator,
                validate_while_typing=False,
                prompt_continuation='> ',
                multiline=entry_schema['multiline'],
            )
            if value.strip():
                data[label] = value

        return self.parse(data)
