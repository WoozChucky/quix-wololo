import os
import time
import traceback
from enum import Enum

from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, JSONSerializer, JSONDeserializer
from quixstreams.platforms.quix.env import QuixEnvironment


class MetricsSource(Enum):
    pod = 0,
    node = 1


def by_metric_type(d: dict):
    if "type" in d:
        return d["type"] == sourceMetrics.name
    return False


def by_threshold(d: dict):
    if parameter_name in d:
        try:
            if float(d[parameter_name]) > threshold_value:
                print("Threshold exceeded")
                return True
        except:
            return False
    return False


def generate_threshold_message(d: dict):
    old_message = d
    d = dict()

    if sourceMetrics == MetricsSource.pod:
        d["container"] = old_message["container"]
    else:
        d["node"] = old_message["node"]
    d[parameter_name] = old_message[parameter_name]
    d[parameter_name + "_max"] = threshold_value
    d['detected_at'] = int(time.time())
    print(d)


if __name__ == "__main__":
    print("Listening to streams. Press CTRL-C to exit.")

    app = Application.Quix("transformation-v1", auto_offset_reset="latest")

    # Change consumer group to a different constant if you want to run model locally.
    print("Opening input and output topics")

    # Environment variables
    input_topic = app.topic(os.environ["input"], value_deserializer=JSONDeserializer())
    output_topic = app.topic(os.environ["output"], value_serializer=JSONSerializer())

    try:
        bufferMilliSeconds = os.environ["bufferMilliSeconds"]
        msecs = int(bufferMilliSeconds)
    except ValueError:
        print("bufferMilliSeconds should be an integer. ERROR: {}".format(traceback.format_exc()))

    threshold_value = float(os.environ["thresholdValue"])
    parameter_name = os.environ["parameterName"]

    sourceMetrics: MetricsSource
    try:
        sourceMetrics = MetricsSource[os.environ["METRIC_TYPE"]]
    except:
        sourceMetrics = MetricsSource.pod

    sdf = app.dataframe(input_topic)

    sdf = sdf.filter(func=by_metric_type, stateful=False)

    sdf = sdf.filter(func=by_threshold, stateful=False)

    sdf = sdf.update(func=generate_threshold_message, stateful=False)

    sdf = sdf.to_topic(output_topic)

    app.run(sdf)
