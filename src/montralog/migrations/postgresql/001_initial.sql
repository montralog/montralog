
        CREATE TABLE IF NOT EXISTS logs (
          id BIGSERIAL PRIMARY KEY, time DOUBLE PRECISION NOT NULL, received DOUBLE PRECISION NOT NULL,
          service TEXT NOT NULL, environment TEXT NOT NULL, severity TEXT NOT NULL,
          message TEXT NOT NULL, pattern TEXT NOT NULL, trace_id TEXT NOT NULL,
          attributes TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS logs_time ON logs(time);
        CREATE INDEX IF NOT EXISTS logs_service_time ON logs(service,environment,time);
        CREATE INDEX IF NOT EXISTS logs_trace ON logs(trace_id);
        CREATE TABLE IF NOT EXISTS spans (
          trace_id TEXT NOT NULL, span_id TEXT NOT NULL, parent_id TEXT NOT NULL,
          time DOUBLE PRECISION NOT NULL, duration_ms DOUBLE PRECISION NOT NULL, service TEXT NOT NULL,
          environment TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL,
          attributes TEXT NOT NULL, PRIMARY KEY(trace_id,span_id));
        CREATE INDEX IF NOT EXISTS spans_time ON spans(time);
        CREATE TABLE IF NOT EXISTS samples (
          id BIGSERIAL PRIMARY KEY, time DOUBLE PRECISION NOT NULL, service TEXT NOT NULL,
          environment TEXT NOT NULL, name TEXT NOT NULL, value DOUBLE PRECISION NOT NULL,
          unit TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS samples_time ON samples(time);
        CREATE TABLE IF NOT EXISTS events (
          id BIGSERIAL PRIMARY KEY, time DOUBLE PRECISION NOT NULL, service TEXT NOT NULL,
          environment TEXT NOT NULL, kind TEXT NOT NULL, message TEXT NOT NULL);
        