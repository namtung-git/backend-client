#!/usr/bin/env bash

set -e


function make_request()
{
    local _REQUEST
    local _VERB
    local _EXPECTED_CODE
    local _RESPONSE
    local _RESPONSE_VALUES

    _REQUEST=${1:-}
    _VERB=${2:-"GET"}
    _EXPECTED_CODE=${3:-200}

    _REQUEST=${PROTOCOL}://${HOSTNAME}:${PORT}/${_REQUEST}
    _RESPONSE=$(curl --write-out "%{http_code}:%{time_starttransfer}" \
                    --silent \
                    --output /dev/null \
                    -X  "${_VERB}" "${_REQUEST}")

    IFS=':' read -ra _RESPONSE_VALUES <<< "$_RESPONSE"

    echo "${_VERB} ${_REQUEST} / ${_RESPONSE}"

    if [[ "${_RESPONSE_VALUES[0]}" != "${_EXPECTED_CODE}" ]]
    then
        echo "Failed due to ${_RESPONSE_VALUES[0]} != ${_EXPECTED_CODE}"
        exit 1
    fi

}

function _main()
{
    export HOSTNAME
    export PORT
    export PROTOCOL

    HOSTNAME=${1:-"localhost"}
    PORT=${2:-8000}
    PROTOCOL="http"

    pps "datatx?destination=210&source_ep=210&dest_ep=1231&qos=1&payload=0011&fast=1" 10 0.1

    make_request "setconfig" "GET" 200
    make_request "datatx" "GET" 500
    make_request "start" "GET" 200
    make_request "info" "GET" 200

    make_request "setconfig" "POST" 200
    make_request "datatx" "POST" 500
    make_request "start" "POST" 200
    make_request "info" "POST" 200

    make_request "datatx?destination=210&source_ep=210&dest_ep=1231&qos=1&payload=0011&fast=1&hoplimit=2&count=1" "GET" 200
    make_request "datatx?destination=210&source_ep=210&dest_ep=1231&qos=1&payload=0011&fast=1&hoplimit=2&count=10" "GET" 200
    make_request "datatx?destination=210&source_ep=210&dest_ep=1231&qos=1&payload=0011&fast=1&hoplimit=2" "GET" 200
    make_request "datatx?destination=210&source_ep=210&dest_ep=1231&qos=1&payload=0011&fast=1" "GET" 200
    make_request "datatx?destination=210&source_ep=210&dest_ep=1231&qos=1&payload=0011" "GET" 200
    make_request "datatx?destination=210&source_ep=210&dest_ep=1231&qos=1" "GET" 500
    make_request "datatx?destination=210&source_ep=210&dest_ep=1231&" "GET" 500
    make_request "datatx?destination=210&source_ep=210&" "GET" 500
    make_request "datatx?destination=210?" "GET" 500
    make_request "datatx?" "GET" 500

    echo "Ok!"
}

# Sends N packets every X seconds towards a given ROUTE
function pps()
{

    local _WAIT_FOR
    local _NB_REQ
    local _ROUTE

    _ROUTE=${1:-}
    _NB_REQ=${2:-1000}
    _WAIT_FOR=${3:-0.25}

    if [[ "${_ROUTE}" ]]
    then
        for counter in $(seq 1 "${_NB_REQ}");
        do
            echo "PPS test: ${_ROUTE} #${counter}/${_NB_REQ} @${_WAIT_FOR}s"
            make_request "${_ROUTE}" "GET"
            sleep "${_WAIT_FOR}"
        done
    fi
}



_main "${@}"
