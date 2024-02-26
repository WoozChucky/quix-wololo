import datetime
import os
import time
from enum import Enum

import kubernetes as k8s
from quixstreams import Application
from quixstreams.models.serializers.quix import JSONSerializer, SerializationContext
from quixstreams.models.serializers.quix import QuixTimeseriesSerializer
from quixstreams.platforms.quix.env import QuixEnvironment

import kubernetes_functions as k8s_helper


class MetricsSource(Enum):
    Pods = 0,
    Nodes = 1


if __name__ == "__main__":

    clusterName = os.environ["K8SClusterName"]
    clusterEndpoint = os.environ["K8SEndpoint"]
    clusterCA = os.environ["K8SClusterCertificateAuthorityData"]
    clientCA = os.environ["K8SClientCertificateData"]
    clientKey = os.environ["K8SClientKeyData"]
    clientToken = os.environ["K8SToken"]

    app = Application.Quix("k8s-metrics-source", auto_offset_reset="latest")
    output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())
    serializer = JSONSerializer()
    metrics_producer = app.get_producer()
    serialization_ctx = SerializationContext(output_topic.name)

    sourceMetrics = MetricsSource.Pods
    namespace = ''

    try:
        namespace = os.environ["K8SNamespace"]
    except:
        sourceMetrics = MetricsSource.Nodes

    if namespace == '':
        sourceMetrics = MetricsSource.Nodes

    k8s_helper.generate_k8s_configuration(clusterName, clusterEndpoint, clusterCA, clientCA, clientKey, clientToken)

    k8s.config.load_kube_config(config_file='config')
    api_instance = k8s.client.CustomObjectsApi()

    total_metrics = 0
    last_total_metrics = 0
    processedTimestamps = dict()

    if sourceMetrics == MetricsSource.Pods:
        print(f'Collecting pod metrics from namespace {namespace}')
        while True:

            if total_metrics > 0:
                print(f'Published total of {total_metrics} metrics')

            with metrics_producer:

                pod_metrics = k8s_helper.get_pod_metrics(api_instance, namespace)

                # Print pod metrics
                for pod in pod_metrics:

                    pod_name = pod['metadata']['name']
                    containers = pod['containers']

                    for container in containers:

                        container_name = container['name']
                        cpu_usage = container['usage']['cpu']
                        memory_usage = container['usage']['memory']
                        collected_at = datetime.datetime.strptime(pod['timestamp'], '%Y-%m-%dT%H:%M:%SZ')

                        key = f'{pod_name}-{namespace}-{container_name}'

                        lastProcessedTimestamp = datetime.datetime.min

                        if key in processedTimestamps:
                            lastProcessedTimestamp = processedTimestamps[key]

                        if not collected_at > lastProcessedTimestamp:
                            continue

                        value = {
                            "type": 'pod',
                            "pod": pod_name,
                            "namespace": namespace,
                            "container": container_name,
                            "cpu": cpu_usage[:len(cpu_usage) - 1],
                            "memory": memory_usage[:len(memory_usage) - 2],
                            "timestamp": time.time_ns(),
                        }

                        metrics_producer.produce(
                            topic=output_topic.name,
                            key=f'pod-metrics-{namespace}',
                            value=serializer(
                                value=value, ctx=serialization_ctx
                            )
                        )

                        processedTimestamps[key] = collected_at
                        total_metrics += 1

            time.sleep(5)
    else:
        print('Collecting node metrics')
        while True:

            if total_metrics > 0:
                print(f'Published total of {total_metrics} metrics')

            with metrics_producer:

                node_metrics = k8s_helper.get_node_metrics(api_instance)

                for node in node_metrics:

                    node_name = node['metadata']['name']
                    labels = node['metadata']['labels']
                    cpu_usage = node['usage']['cpu']
                    memory_usage = node['usage']['memory']

                    key = f'{node_name}'

                    collected_at = datetime.datetime.strptime(node['timestamp'], '%Y-%m-%dT%H:%M:%SZ')

                    lastProcessedTimestamp = datetime.datetime.min

                    if key in processedTimestamps:
                        lastProcessedTimestamp = processedTimestamps[key]

                    if not collected_at > lastProcessedTimestamp:
                        continue

                    value = {
                        "type": 'node',
                        "node": node_name,
                        "labels": labels,
                        "cpu": cpu_usage[:len(cpu_usage) - 1],
                        "memory": memory_usage[:len(memory_usage) - 2],
                        "timestamp": time.time_ns(),
                    }

                    metrics_producer.produce(
                        topic=output_topic.name,
                        key='node-metrics',
                        value=serializer(
                            value=value, ctx=serialization_ctx
                        )
                    )

                    processedTimestamps[key] = collected_at
                    total_metrics += 1
            time.sleep(5)

