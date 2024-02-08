import yaml
from kubernetes.client import CustomObjectsApi


def generate_k8s_configuration(cluster_name, cluster_endpoint, cluster_ca, client_ca, client_key, token):
    d = {
        "apiVersion": "v1",
        "kind": "config",
        "preferences": {},
        "current-context": cluster_name,
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": cluster_ca,
                    "server": cluster_endpoint,
                },
                "name": cluster_name
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": cluster_name,
                    "user": cluster_name
                },
                "name": cluster_name
            }
        ],
        "users": [
            {
                "name": cluster_name,
                "user": {
                    "client-certificate-data": client_ca,
                    "client-key-data": client_key,
                    "token": token
                }
            }
        ]
    }

    with open('config', "w") as yaml_file:
        yaml.dump(d, yaml_file, default_flow_style=False)


def get_pod_metrics(api: CustomObjectsApi, namespace: str):
    pod_list = api.list_namespaced_custom_object(
        group="metrics.k8s.io",
        version="v1beta1",
        namespace=namespace,
        plural="pods"
    )
    return pod_list['items']


def get_node_metrics(api: CustomObjectsApi):
    node_list = api.list_cluster_custom_object(
        group="metrics.k8s.io",
        version="v1beta1",
        plural="nodes"
    )
    return node_list['items']
