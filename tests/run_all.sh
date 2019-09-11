#!/usr/bin/env bash
# Copyright Wirepas Ltd 2019
# Quickly validate the execution of the examples
# shellcheck disable=SC2086
_ARGS=("$@")

# Error control
VALID_RC=${VALID_RC:-124}
EXIT_WITH=${EXIT_WITH:-1}
TIMEOUT_DURATION=${TIMEOUT_DURATION:-10}

# Execution manifest
KPI_TESTS=("-m wirepas_backend_client.test.kpi_mesh" "-m wirepas_backend_client.test.kpi_adv")
ENTRYPOINTS=("wm-gw-cli" "wm-wnt-viewer" "wm-wpe-viewer" )
EXAMPLES_DIR=${EXAMPLES_DIR:-"examples/*"}

# Notifications
SUCCESS_MESSAGE=${SUCCESS_MESSAGE:-"Ok!"}
ERROR_MESSAGE=${ERROR_MESSAGE:-"Error!"}

function timed_run()
{
    _run=${*}
    echo "[TIMED_RUN] | executing: ${_run} (timeout in: ${TIMEOUT_DURATION})"
    eval "timeout ${TIMEOUT_DURATION} ${_run}"

    # > /dev/null

    if [[ "$?" == "${VALID_RC}" ]]
    then
        echo "${SUCCESS_MESSAGE}"
    else
        echo "${ERROR_MESSAGE}"
        exit "${EXIT_WITH}"
    fi
}

function _loop()
{
    _TARGETS=("$@")
    LOOP_CMD=${LOOP_CMD:-}

    for _target in "${_TARGETS[@]}"
    do

        if [[ "${_target}" == *"fluent"* \
            || "${_target}" == *"influx"* \
            || "${_target}" == *"txt"* \
            || "${_target}" == *"report_parser"* \
            || "${_target}" == *"settings"* \
            || "${_target}" == *"sh"* \
            || "${_target}" == *".csv" \
            || "${_target}" == *".json" \
            || "${_target}" == *".txt" \
            || "${_target}" == *"settings.yml"* \
            || "${_target}" == *"private"*  ]]
        then
            continue
        fi


        timed_run "${LOOP_CMD} ${_target} ${_ARGS[*]}"
    done
}

function _test()
{
    _TARGETS=("$@")
    LOOP_CMD=${LOOP_CMD:-}

    for _target in "${_TARGETS[@]}"
    do
        echo "${_target}"
    done
}

function _main()
{
    echo "running entrypoints"
    LOOP_CMD=
    _loop "${ENTRYPOINTS[@]}"

    echo "running perf tests"
    LOOP_CMD="python"
    _loop "${KPI_TESTS[@]}"

    echo "running examples"
    LOOP_CMD="python"
    _loop ${EXAMPLES_DIR}
}

_main
