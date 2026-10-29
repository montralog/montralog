import json
import os
import urllib.request
import urllib.parse
from .config import MAX_BODY

PANELS = {
    'targets': ('Scrape targets', 'up', 'state'),
    'cpu': ('Host CPU usage', '100 * (1 - avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) or (montralog_host_cpu_percent and on(host_name) (time() - montralog_host_collection_timestamp_seconds < 60))', '%'),
    'memory': ('Host memory usage', '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) or (montralog_host_memory_percent and on(host_name) (time() - montralog_host_collection_timestamp_seconds < 60))', '%'),
    'container_cpu': ('Container CPU cores', 'sum by(name) (rate(container_cpu_usage_seconds_total{name!=""}[5m])) or (montralog_docker_cpu_cores and on(host_name,container_name) (time() - montralog_docker_last_seen_timestamp_seconds < 60))', 'cores'),
    'host_disk': ('Local host system disk usage', 'montralog_host_disk_percent and on(host_name) (time() - montralog_host_collection_timestamp_seconds < 60)', '%'),
    'docker_containers': ('Docker running containers', 'montralog_docker_running_containers and on(host_name) (time() - montralog_docker_collection_timestamp_seconds < 60)', 'containers'),
    'docker_memory': ('Docker container memory', 'montralog_docker_memory_bytes and on(host_name,container_name) (time() - montralog_docker_last_seen_timestamp_seconds < 60)', 'bytes'),
    'docker_memory_percent': ('Docker memory limit used', 'montralog_docker_memory_percent and on(host_name,container_name) (time() - montralog_docker_last_seen_timestamp_seconds < 60)', '% of limit'),
    'docker_processes': ('Docker container processes', 'montralog_docker_processes and on(host_name,container_name) (time() - montralog_docker_last_seen_timestamp_seconds < 60)', 'processes'),
    'docker_received': ('Docker network received', 'montralog_docker_network_received_bytes and on(host_name,container_name) (time() - montralog_docker_last_seen_timestamp_seconds < 60)', 'cumulative bytes'),
    'docker_sent': ('Docker network sent', 'montralog_docker_network_sent_bytes and on(host_name,container_name) (time() - montralog_docker_last_seen_timestamp_seconds < 60)', 'cumulative bytes'),
    'docker_last_seen': ('Docker container last observed', 'montralog_docker_last_seen_timestamp_seconds', 'Unix seconds'),
    'agent_age': ('Local metrics freshness', 'time() - montralog_docker_collection_timestamp_seconds', 'seconds since collection'),
    'pods': ('Kubernetes pod phases', 'sum by(namespace,phase) (kube_pod_status_phase)', 'pods'),
    'app_requests': ('Application request rate', 'sum by(service_name) (rate(http_server_request_duration_seconds_count[5m]))', 'req/s'),
}

def prometheus(path, params=None, source_id=''):
    from .connections import resolve, query
    return query(resolve(source_id),path,params)


def build_query(panel, aggregation='none', group_by=''):
    """Build bounded PromQL from reviewed metrics and allowlisted operations."""
    if panel not in PANELS:
        raise ValueError('Unknown dashboard panel')
    if aggregation not in ('none', 'avg', 'sum', 'min', 'max', 'count'):
        raise ValueError('Unsupported aggregation')
    if group_by not in ('', 'instance', 'host_name', 'container_name', 'namespace', 'service_name'):
        raise ValueError('Unsupported grouping label')
    if aggregation == 'none' and group_by:
        raise ValueError('Choose an aggregation before grouping')
    query = PANELS[panel][1]
    if aggregation != 'none':
        grouping = f' by ({group_by})' if group_by else ''
        query = f'{aggregation}{grouping} ({query})'
    return query
