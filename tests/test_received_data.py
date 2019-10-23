import json
import wirepas_messaging
import datetime

from wirepas_backend_client.messages.interface import MessageManager


def get_traffic(filepath):
    with open(filepath) as mqtt_traffic:
        messages = mqtt_traffic.readlines()
    return messages


def build_wire_message(record):

    wire_message = wirepas_messaging.gateway.api.ReceivedDataEvent(
        record["gw_id"],
        record["sink_id"],
        int(
            datetime.datetime.fromisoformat(record["rx_time"]).timestamp()
            * 1e3
        ),
        record["source_address"],
        record["destination_address"],
        record["source_endpoint"],
        record["destination_endpoint"],
        record["travel_time_ms"],
        record["qos"],
        bytes.fromhex(record["data_payload"]),
        hop_count=record["hop_count"],
    )
    return wire_message


def parse_wire_message(message):
    parsed_message = MessageManager.map(
        message.source_endpoint, message.destination_endpoint
    ).from_bus(message.payload)
    return parsed_message


def test_exception_handling():
    """ This test ensures that incorrect payloads do not crash the decoder """

    messages = get_traffic("./tests/mqtt_incorrect_payload.json")

    for message in messages:
        record = json.loads(message)
        wire_message = build_wire_message(record)
        parse_wire_message(wire_message)


def test_received_messages():
    """
    This takes recorded mqtt traffic and checks
    that the protobuff message can be regenerated
    and that its decoding results in the same object
    """

    stats = dict()
    messages = get_traffic("./tests/mqtt_traffic.json")

    for message in messages:

        record = json.loads(message)
        wire_message = build_wire_message(record)
        parsed_message = parse_wire_message(wire_message)

        for k in parsed_message.apdu:

            try:
                if record[k] != parsed_message.apdu[k]:
                    raise ValueError(
                        "{}: {} != {}".format(
                            k, record[k], parsed_message.apdu[k]
                        )
                    )
            except KeyError:
                print("Key error: {} / {}".format(k, parsed_message.apdu))
                raise

        try:
            stats[
                "{}:{}".format(
                    wire_message.source_endpoint,
                    wire_message.destination_endpoint,
                )
            ] += 1
        except KeyError:
            stats[
                "{}:{}".format(
                    wire_message.source_endpoint,
                    wire_message.destination_endpoint,
                )
            ] = 1

    print("Endpoints and messages tested: {}".format(stats))


if __name__ == "__main__":
    test_received_messages()
    test_exception_handling()
