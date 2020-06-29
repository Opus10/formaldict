formaldict
###########

``formaldict`` provides the constructs for parsing structured dictionaries
that adhere to a schema. Along with a simple and flexible schema definition
to parse and validate dictionaries, ``formaldict`` is integrated with
`python-prompt-toolkit <https://github.com/prompt-toolkit/python-prompt-toolkit>`__.
This integration allows users to easily construct flows for command line
interfaces (CLIs) when parsing structured user input.

Below is an example user input flow constructed with a ``formaldict``
schema used by `git-tidy <https://github.com/jyveapp/git-tidy>`__:

.. image:: https://raw.githubusercontent.com/jyveapp/formaldict/master/docs/_static/prompt.gif
   :width: 600

Check out the `docs <https://formaldict.readthedocs.io/>`__ for a
tutorial on how to use ``formaldict`` as the backbone for parsing
structured input in your library.

Documentation
=============

`View the formaldict docs here
<https://formaldict.readthedocs.io/>`_.

Installation
============

Install formaldict with::

    pip3 install formaldict


Contributing Guide
==================

For information on setting up formaldict for development and
contributing changes, view `CONTRIBUTING.rst <CONTRIBUTING.rst>`_.


Primary Authors
===============

- @wesleykendall (Wes Kendall)
