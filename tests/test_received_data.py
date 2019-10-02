import json
import wirepas_messaging
import datetime

from wirepas_backend_client.messages.interface import MessageManager


def test_received_messages():

    stats = dict()

    with open("./tests/mqtt_traffic.json") as mqtt_traffic:
        messages = mqtt_traffic.readlines()

    for message in messages:
        record = json.loads(message)

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

        parsed_message = MessageManager.map(
            wire_message.source_endpoint, wire_message.destination_endpoint
        ).from_bus(wire_message.payload)

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
