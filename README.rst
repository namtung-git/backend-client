Backend client
==============

.. image:: https://travis-ci.org/wirepas/backend-client.svg?branch=master
    :target: https://travis-ci.org/wirepas/backend-client

.. image:: https://badge.fury.io/py/wirepas-backend-client.svg
    :target: https://badge.fury.io/py/wirepas-backend-client



Backend client is a tool to interface with Wirepas' WM-RM-128 API. The API
consists of a set of MQTT topic to interact with a Wirepas Mesh network.

For successfuly communicating with a Wirepas network you will need to
have a complaint gateway which publishes and subscribes to a MQTT broker.


The backend client tool allows you too consume data from such API as well
as interacting with other Wirepas' services, such as Wirepas Network Tool
and the Wirepas Positioning Engine.



Installation
============

To install this package in development mode, please run

::

    pip install -e .

To build the source distribution and wheel file, make sure you have the
wheel package installed

::

    pip install wheel

and then run

::

    py3clean .

    python3 setup.py clean --all

    python3 setup.py sdist bdist_wheel

afterwards you can install the wirepas-backend-client wheel from the dist
folder with

::

    pip install dist/*.whl


To install from the public registry


::

    pip install wirepas-backend-client


Parameters
==========

Parameters are given as input arguments or through a configuration file
written in yaml.

An example on how to write the configuration file to connect to the
mqtt broker at *mqttbroker.com*:

::

    mqtt_hostname: "mqttbroker.com"
    mqtt_username: "mqttuser"
    mqtt_password: "mqttpassword"
    mqtt_port: 8883


.. WARNING::
    Parameters read from the file will take precedence over command line
    arguments.


WNT parameters
---------------
.. _wnt:

When talking to a WNT target, you must set the following settings with
the backend client


::

    wnt_username: "wntuser"
    wnt_password: "98asuyd907171ehjmasd"
    wnt_hostname: "wnthost.com"



WPE parameters
---------------
.. _wpe:

When talking to a WPE target, you must set the following settings with
the backend client


::

    wpe_service_definition: ./mywpesettings.json
    wpe_network: 1092



Fluentd parameters
-----------------------

.. _fluentd:

The backend client has integrated logging with fluentd through Python's
logging facility.

Routing data to a fluentd host requires that you define the target host
when executing a backend client script.

To configure the target host, tag and record for the stream, ensure that
you configure the settingd.yml file with

::

    # tags stream with app.mesh
    fluentd_hostname: "myfluenthost"
    fluentd_record: mesh
    fluentd_tag: app

The same commands can be provided as input arguments.


Influx parameters
------------------

.. _influx:

The backend client can talk to an influx database and it requires the
following parameters to be defined.


::

    influx_hostname: "wnthost.com"
    influx_port: "wntinfluxport"
    influx_username: "someuser"
    influx_password: "somepassword"
    influx_database: "somedatabase"



Shell entrypoints
=================

.. _entrypoints:

The backend client provides the following entry points:


::

    wm-gw-cli: interacts with a MQTT broker to view details
                about the gateways and its networks



Examples
========

This section contains a brief description of the available examples.

To  execute them, install the backend client and change into the examples
folder.

Once inside the folder execute the example you wish with


::

    python3 example_file.py --settings ./settings.yml


where

- **example_file.py**: is one of the examples given below

- **settings.yml**: contains all the connection details and program arguments


Logging & decoding MQTT traffic
-------------------------------
The `mqtt viewer <https://github.com/wirepas/backend-client/examples/mqtt_viewer.py>`__ subscribes
and decodes incoming MQTT data on the fly.

This example is ideal if you want to pass through WM data to `fluentd and kibana`_.


Find all nodes
--------------
The `find all nodes <https://github.com/wirepas/backend-client/examples/find_all_nodes.py>`__ prints the nodes
present in the network as it observes data packets from them.


Influx viewer
-------------
The `influx viewer <https://github.com/wirepas/backend-client/examples/influx_viewer.py>`__ allows you to query the
WNT influx datastore and transform the coded column names to human readable
names.


License
------------
Licensed under the Apache License, Version 2.0. See LICENSE for the full license text.


.. _fluentd and kibana: https://github.com/wirepas/evk
