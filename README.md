# Backend client


[![Build Status](https://travis-ci.org/wirepas/backend-client.svg?branch=master)](https://travis-ci.org/wirepas/backend-client) [![PyPi](https://img.shields.io/pypi/v/wirepas-backend-client.svg)](https://pypi.org/project/wirepas-backend-client/)


Backend client is a tool to interface with Wirepas' WM-RM-128 API. The API
consists of a set of MQTT topic to interact with a Wirepas Mesh network.

For successfully communicating with a Wirepas network you will need to
have a complaint gateway which publishes and subscribes to a MQTT broker.


The backend client tool allows you too consume data from such API as well
as interacting with other Wirepas' services, such as Wirepas Network Tool
and the Wirepas Positioning Engine.


## Docker Hub builds


Backend client builds are avilable from Docker Hub. Each release has a
corresponding tag which you can pull.

The latest tag points to the last release whereas the edge points to the
top of master and is built after each commit.


### Using the docker image

You will need to mount or build and image with your MQTT and/or other
WM services parameters.


The default image command will launch the gateway client with the settings
present in /home/wirepas/vars/settings.yml.

To run it with docker type:

```shell
    docker run -v $(pwd)/settings.yml:/home/wirepas/vars/settings.yml \
                wirepas
```



### Building the image locally


To build the image locally in the root of the repo type:
```shell
    docker build -f container/Dockerfile -t backend-client .
```
Alternatively you can also build using the docker-compose.yml present in
the root of the directory:


```shell
    docker-compose -f container/docker-compose.yml  build
```
If you want to pull use:


```shell
    docker-compose -f container/docker-compose.yml  pull
```
To run the backend client using docker compose, drop the setting in
.settings.yml and start the service with:

```shell
    docker-compose container/docker-compose.yml up
```
The file .settings.yml is set as ignored for git and docker.



## Installation


To install this package in development mode, please run

```shell
    pip install -e .
```
To build the source distribution and wheel file, make sure you have the
wheel package installed

```shell
    pip install wheel
```
and then run

```shell
    py3clean .

    python3 setup.py clean --all

    python3 setup.py sdist bdist_wheel
```
afterwards you can install the wirepas-backend-client wheel from the dist
folder with

```shell
    pip install dist/*.whl
```

To install from the public registry

```shell
    pip install wirepas-backend-client
```

## Parameters


Parameters are given as input arguments or through a configuration file
written in yaml.

An example on how to write the configuration file to connect to the
mqtt broker at *mqttbroker.com*:

```yaml
    mqtt_hostname: "mqttbroker.com"
    mqtt_username: "mqttuser"
    mqtt_password: "mqttpassword"
    mqtt_port: 8883

```

** WARNING **
    Parameters read from the file will take precedence over command line
    arguments.


### WNT parameters

When talking to a WNT target, you must set the following settings with
the backend client



```yaml
    wnt_username: "wntuser"
    wnt_password: "98asuyd907171ehjmasd"
    wnt_hostname: "wnthost.com"
```


### WPE parameters

When talking to a WPE target, you must set the following settings with
the backend client
```yaml
    wpe_service_definition: ./mywpesettings.json
    wpe_network: 1092
```


### Fluentd parameters

The backend client has integrated logging with fluentd through Python's
logging facility.

Routing data to a fluentd host requires that you define the target host
when executing a backend client script.

To configure the target host, tag and record for the stream, ensure that
you configure the settingd.yml file with

```yaml
    # tags stream with app.mesh
    fluentd_hostname: "myfluenthost"
    fluentd_record: mesh
    fluentd_tag: app
```
The same commands can be provided as input arguments.


### Influx parameters

The backend client can talk to an influx database and it requires the
following parameters to be defined.

```yaml
    influx_hostname: "wnthost.com"
    influx_port: "wntinfluxport"
    influx_username: "someuser"
    influx_password: "somepassword"
    influx_database: "somedatabase"
```


## Shell entrypoints

The backend client provides the following entry points:


    wm-gw-cli: interacts with a MQTT broker to view details
                about the gateways and its networks



## Examples

This section contains a brief description of the available examples.

To  execute them, install the backend client and change into the examples
folder.

Once inside the folder execute the example you wish with

```shell
    python3 example_file.py --settings ./settings.yml
```

where

- **example_file.py**: is one of the examples given below

- **settings.yml**: contains all the connection details and program arguments


### Logging & decoding MQTT traffic

The [mqtt viewer](./examples/mqtt_viewer.py) subscribes
and decodes incoming MQTT data on the fly.

This example is ideal if you want to pass through WM data to [fluentd and kibana](https://github.com/wirepas/evk).


### Find all nodes

The [find all nodes](./examples/find_all_nodes.py) prints the nodes
present in the network as it observes data packets from them.


### Influx viewer

The [influx viewer](./examples/influx_viewer.py) allows you to query the
WNT influx datastore and transform the coded column names to human readable
names.


### License

Licensed under the Apache License, Version 2.0. See LICENSE for the full license text.

