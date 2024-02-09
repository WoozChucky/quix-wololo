import uuid
from datetime import datetime

from quixstreams import Application
from quixstreams.platforms.quix.env import QuixEnvironment
from quixstreams.models.serializers.quix import JSONDeserializer

import os
from dash import dcc, Input, Output, Dash, html, dash_table
import dash_bootstrap_components as dbc
import threading
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


app = Application.Quix(str(uuid.uuid4()), auto_offset_reset="latest")

stream_consumer = app.get_consumer()
input_topic = app.topic(os.environ["input"], value_deserializer=JSONDeserializer())

sdf = app.dataframe(input_topic)

external_stylesheets = [dbc.themes.LUMEN]

dash_app = Dash(external_stylesheets=external_stylesheets)

columns = ['Node', 'Container', 'Pod', 'Namespace', 'CPU', 'CPU_max', 'Memory', 'Memory_max', 'Detected_At']
data = []

dash_app.layout = dbc.Container([
    html.H1("Metrics Alerts"),
    dash_table.DataTable(
        id='tbl1',
        data=data,
        columns=[{"name": i, "id": i} for i in columns],
    ),
    dcc.Interval(id="interval", interval=1000)
])


@dash_app.callback(Output('tbl1', 'data'), [Input('interval', 'n_intervals')])
def update_data(n_intervals):
    return data


@dash_app.callback(Output('tbl1', 'columns'), [Input('interval', 'n_intervals')])
def update_column(n_intervals):
    return columns


def web_server():
    dash_app.run_server(debug=False, host="0.0.0.0", port=80)


def get_them_good_rows(d: dict):
    print(d)

    dt = datetime.fromtimestamp(float(d["detected_at"]) // 1000000000)
    detected_at = dt.strftime('%Y-%m-%d %H:%M:%S')

    if d["type"] == 'pod':

        print("Pod")

        if d.get("cpu", None) is not None:
            print("CPU")
            # pod cpu
            cpu = float(d["cpu"])  # this is in milli cores, then we have to convert it to cores
            cpu = cpu / 1000000000
            cpu_max = float(d["cpu_max"])  # this is in milli cores, then we have to convert it to cores
            cpu_max = cpu_max / 1000000000

            data.append({
                "Container": d["container"],
                "Pod": d["pod"],
                "Namespace": d["namespace"],
                "CPU": f'{cpu} Cores',
                "CPU_max": f'{cpu_max} Cores',
                "Detected_At": detected_at
            })

        if d.get("memory", None) is not None:
            print("Memory")
            # pod memory
            memory = float(d["memory"])  # this is in kilobytes, then we have to convert it to megabytes
            memory = int(memory / 1000)
            memory_max = float(d["memory_max"])  # this is in kilobytes, then we have to convert it to megabytes
            memory_max = int(memory_max / 1000)

            data.append({
                "Container": d["container"],
                "Pod": d["pod"],
                "Namespace": d["namespace"],
                "Memory": f'{memory} MB',
                "Memory_max": f'{memory_max} MB',
                "Detected_At": detected_at
            })

    else:
        if d.get("cpu", None) is not None:
            print("CPU")
            # pod cpu
            cpu = float(d["cpu"])  # this is in milli cores, then we have to convert it to cores
            cpu = cpu / 1000000000
            cpu_max = float(d["cpu_max"])  # this is in milli cores, then we have to convert it to cores
            cpu_max = cpu_max / 1000000000

            data.append({
                "Node": d["node"],
                "CPU": f'{cpu} Cores',
                "CPU_max": f'{cpu_max} Cores',
                "Detected_At": detected_at
            })

        if d.get("memory", None) is not None:
            print("Memory")
            # pod memory
            memory = float(d["memory"])  # this is in kilobytes, then we have to convert it to megabytes
            memory = int(memory / 1000)
            memory_max = float(d["memory_max"])  # this is in kilobytes, then we have to convert it to megabytes
            memory_max = int(memory_max / 1000)

            data.append({
                "Node": d["node"],
                "Memory": f'{memory} MB',
                "Memory_max": f'{memory_max} MB',
                "Detected_At": detected_at
            })


sdf = sdf.apply(func=get_them_good_rows, stateful=False)

t1 = threading.Thread(target=web_server)
t1.start()

app.run(sdf)
