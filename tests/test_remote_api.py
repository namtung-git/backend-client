# flake8: noqa

from wirepas_backend_client.mesh.interfaces.remote_api import *
from wirepas_backend_client.mesh.services import msap, csap


def test_remote_api_commands():

    command = Ping()
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")
    if (
        payload.hex()
        != f"{command.request_type:02X}{command.request_length:02X}"
    ):
        raise ValueError("Mismatch in payload")

    command = Begin()
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")
    if (
        payload.hex()
        != f"{command.request_type:02X}{command.request_length:02X}"
    ):
        raise ValueError("Mismatch in payload")

    lock_key = bytes(bytearray(16))
    command = BeginWithLock(lock_key)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")
    if (
        payload.hex()
        != f"{command.request_type:02X}{command.request_length:02X}{lock_key.hex()}"
    ):
        raise ValueError("Mismatch in payload")

    command = End()
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")
    if (
        payload.hex()
        != f"{command.request_type:02X}{command.request_length:02X}"
    ):
        raise ValueError("Mismatch in payload")

    command = Cancel()
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")
    if (
        payload.hex()
        != f"{command.request_type:02X}{command.request_length:02X}"
    ):
        raise ValueError("Mismatch in payload")

    command = Update()
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")
    if (
        payload.hex()
        != f"{command.request_type:02X}{command.request_length:02X}"
    ):
        raise ValueError("Mismatch in payload")

    command = Update()
    command.countdown = 10
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = Update()
    command.countdown = 32767
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    #### MSAP
    command = WriteMSAP()
    command.attribute = msap.AccessCycleRange(0)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = WriteMSAP()
    command.attribute = msap.AccessCycleRange(2000)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = WriteMSAP()
    command.attribute = msap.AccessCycleRange(4000)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = WriteMSAP()
    command.attribute = msap.AccessCycleRange(8000)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = WriteMSAP()
    try:
        command.attribute = msap.AccessCycleRange(8000)
    except ValueError:
        pass

    command = ReadMSAP()
    command.attribute = msap.AccessCycleRange(4000)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = WriteCSAP()
    command.attribute = csap.NodeAddress(1123)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = ReadCSAP()
    command.attribute = csap.NodeAddress(0)
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = ScratchpadStatus()
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = ScratchpadUpdate()
    command.sequence = 1
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = QueueTimeWrite()
    command.priority = 3
    command.time = 20
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")

    command = QueueTimeRead()
    command.priority = 1
    payload = command.encode()
    print(f"{command} PAYLOAD: {payload.hex()}")
