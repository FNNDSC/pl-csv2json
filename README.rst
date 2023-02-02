pl-csv2json
================================

.. image:: https://img.shields.io/docker/v/fnndsc/pl-csv2json?sort=semver
    :target: https://hub.docker.com/r/fnndsc/pl-csv2json

.. image:: https://img.shields.io/github/license/fnndsc/pl-csv2json
    :target: https://github.com/FNNDSC/pl-csv2json/blob/master/LICENSE

.. image:: https://github.com/FNNDSC/pl-csv2json/workflows/ci/badge.svg
    :target: https://github.com/FNNDSC/pl-csv2json/actions


.. contents:: Table of Contents


Abstract
--------

An app to convert CSV predition file generated from `pl-lld_inference` into a more meaningful JSON representation.


Description
-----------


``csv2json`` is a *ChRIS ds-type* application processes an upstream CSV formatted predition file and generates a more friendly JSON representation. This JSON output is used in many downstream plugins and is interpreted to determine where to place drawing and measurement markers on an image.


Usage
-----

.. code::

    docker run --rm fnndsc/pl-csv2json csv2json

        [-f| --inputFileFilter <inputFileFilter>]
        [-t|--tagFileFilter <tagFileFilter>]
        [-o| --outputFileStem <outputFileStem>]
        [-a|--addTags <commaSeparatedTags>]
        [-h|--help]
        [--json] [--man] [--meta]
        [--savejson <DIR>]
        [-v|--verbosity <level>]
        [--version]
        <inputDir> <outputDir>


Arguments
~~~~~~~~~

.. code::

    [-f| --inputFileFilter <inputFileFilter>]
    A glob pattern string, default is "**/*.csv", representing the input
    file pattern to analyze.

    [-t|--tagFileFilter <tagFileFilter>]
    A glob pattern string, default is "**/*.dcm", representing the input tag
    file pattern to analyze.

    [-t|--tagFileFilter <tagFileFilter>]
    A glob pattern string, default is "**/*.dcm", representing the input
    dicom file pattern to analyze.

    [-o| --outputFileStem <outputFileStem>]
    The name of the output JSON file to be created (without the extension).

    [-a|--addTags <commaSeparatedTags>]
    A comma separated string conatining the list of tags to add in the info section
    of the output JSON. The default included tag is 'PatientID'.

    [-h] [--help]
    If specified, show help message and exit.

    [--json]
    If specified, show json representation of app and exit.

    [--man]
    If specified, print (this) man page and exit.

    [--meta]
    If specified, print plugin meta data and exit.

    [--savejson <DIR>]
    If specified, save json representation file to DIR and exit.

    [-v <level>] [--verbosity <level>]
    Verbosity level for app. Not used currently.

    [--version]
    If specified, print version number and exit.


Getting inline help is:

.. code:: bash

    docker run --rm fnndsc/pl-csv2json csv2json --man

Run
~~~

You need to specify input and output directories using the `-v` flag to `docker run`.


.. code:: bash

    docker run --rm -u $(id -u)                             \
        -v $(pwd)/in:/incoming -v $(pwd)/out:/outgoing      \
        fnndsc/pl-csv2json csv2json                         \
        /incoming /outgoing


Development
-----------

Build the Docker container:

.. code:: bash

    docker build -t local/pl-csv2json .

Run unit tests:

.. code:: bash

    docker run --rm local/pl-csv2json nosetests

Examples
--------

Put some examples here!


.. image:: https://raw.githubusercontent.com/FNNDSC/cookiecutter-chrisapp/master/doc/assets/badge/light.png
    :target: https://chrisstore.co
