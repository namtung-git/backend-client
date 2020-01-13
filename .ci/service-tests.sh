#!/usr/bin/env bash

set -e

if [[ -f ".wnt-secrets" ]]
then
    set -a
    source ".wnt-secrets"
    set +a
fi

function pull_dependencies()
{

    WAIT_FOR_IT_PATH=tests/services/wait-for-it

    if [[ ! -d "${WAIT_FOR_IT_PATH}" ]]
    then
        git clone https://github.com/vishnubob/wait-for-it.git "${WAIT_FOR_IT_PATH}"
    fi
}

function run_test()
{
    export WM_BACKEND_CLI_CMD
    WM_BACKEND_CLI_CMD=$1
    _TIMEOUT=${2:-5}
    timeout --preserve-status "${_TIMEOUT}" docker-compose \
            -f tests/services/docker-compose.yml up \
            --abort-on-container-exit \
            --exit-code-from backend-client
}


pull_dependencies

run_test "/usr/bin/tools/wait-for-it/wait-for-it.sh mysql:3306 -s -t 20 -- python -m wirepas_backend_client.test.kpi_mesh"
run_test "python -m wirepas_backend_client.test.kpi_adv" "5"

run_test "python /home/wirepas/.local/wirepas_backend_client-extras/examples/mqtt_viewer.py"  "5"
run_test "python /home/wirepas/.local/wirepas_backend_client-extras/examples/influx_viewer.py" "5"
run_test "python /home/wirepas/.local/wirepas_backend_client-extras/examples/find_all_nodes.py" "2"

run_test "wm-gw-cli" "5"
run_test "wm-wnt-viewer"  "5"
