# Changelog
## 1.0.0 (2020-06-25)
### Api-Break
  - Official V1 release bump [Wes Kendall, 3c37007]

    Bump the version to 1.0.0.

## 0.2.1 (2020-06-24)
### Trivial
  - Add git-tidy integration and update package metadata. [Wes Kendall, 56eaff8]

## 0.2.0 (2020-06-24)
### Feature
  - Added ReadTheDocs integration. [Wes Kendall, c5907ba]

    Fixed a few more lingering issues with ReadTheDocs builds related to
    poetry.
### Trivial
  - Trying other configuration methods for failing readthedocs builds. [Wes Kendall, a7b9e78]

## 0.1.2 (2020-06-23)
### Trivial
  - Adds a .readthedocs.yml file for additional readthedocs.org configuration. [Wes Kendall, a1c449b]

## 0.1.1 (2020-06-23)
### Trivial
  - Add an auto-generated requirements.txt for readthedocs.org compilation [Wes Kendall, adbd801]

## 0.1.0 (2020-06-23)
### Feature
  - V1 of formaldict [Wes Kendall, 2b121fb]

    V1 of formaldict provides the following constructs:
    1. Schema - For specifying a structure for dictionaries.
    2. FormalDict - The dictionary object that is parsed from a schema.

    Schemas can parse existing dictionaries and verify that they match
    the schema. Schemas are also integrated with python prompt toolkit
    for prompting for user input that matches the schema.

