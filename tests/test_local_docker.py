import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('local_docker_agent',Path(__file__).resolve().parents[1]/'agents/docker/agent.py')
agent=importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

class LocalDockerTests(unittest.TestCase):
    def test_units_and_cpu_conversion(self):
        rows=[{'Name':'api','ID':'abc','MemUsage':'128MiB / 1GiB','NetIO':'12kB / 2MB',
               'BlockIO':'0B / 1GiB','CPUPerc':'125.00%','MemPerc':'12.50%','PIDs':'7'}]
        points=agent.docker_points(rows,1000)
        values={name:value for name,value,labels in points}
        self.assertEqual(values['montralog_docker_cpu_cores'],1.25)
        self.assertEqual(values['montralog_docker_memory_bytes'],128*1024**2)
        self.assertEqual(values['montralog_docker_network_received_bytes'],12000)
        self.assertEqual(values['montralog_docker_running_containers'],1)
        payload=agent.payload(points,'windows-host',1000)
        encoded=json.dumps(payload,allow_nan=False)
        self.assertNotIn('password',encoded)
        self.assertIn('container_name',encoded)
        self.assertEqual(len(payload['resourceMetrics'][0]['scopeMetrics'][0]['metrics']),12)

    def test_empty_docker_is_zero_not_failure(self):
        self.assertEqual(agent.docker_points([],1000)[0],('montralog_docker_running_containers',0,{}))

    def test_invalid_sizes_rejected(self):
        for value in ('--','NaN','-1MiB','1unknown'):
            with self.assertRaises((ValueError,KeyError)):agent.quantity(value)
