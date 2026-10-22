"""Shared gateway process settings for Docker and Helm."""
import os
bind = "0.0.0.0:8080"
workers = int(os.getenv("MONTRALOG_WORKERS","2"))
threads = int(os.getenv("MONTRALOG_THREADS","4"))
timeout = 30
graceful_timeout = 30
max_requests = 2000
max_requests_jitter = 200
worker_tmp_dir = "/tmp"
errorlog = "-"
# No operator control socket is required inside an immutable container.
control_socket_disable = True
