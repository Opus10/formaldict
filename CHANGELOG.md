# Changelog
## 1.0.5 (2022-08-20)
### Trivial
  - Fix release note rendering and code formatting changes [Wes Kendall, cff4576]

## 1.0.4 (2022-07-31)
### Trivial
  - Updated with the latest Python template, fixing doc builds [Wes Kendall, d293ae0]

## 1.0.3 (2022-01-31)
### Trivial
  - Updates with the latest version of the template [Wes Kendall, 309ca1d]

## 1.0.2 (2021-05-26)
### Trivial
  - Updated to the latest Python library template [Wes Kendall, 24317a0]

## 1.0.1 (2020-06-29)
### Trivial
  - Added more docs to the README [Wes Kendall, ed322b2]

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

