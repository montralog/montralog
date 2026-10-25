{{- define "montralog.name" -}}montralog{{- end -}}
{{- define "montralog.fullname" -}}
{{- if contains "montralog" .Release.Name -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-montralog" .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- define "montralog.labels" -}}
app.kubernetes.io/name: montralog
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}
{{- define "montralog.selector" -}}
app.kubernetes.io/name: montralog
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "montralog.image" -}}
{{- if .Values.image.digest -}}
{{ printf "%s@%s" .Values.image.repository .Values.image.digest }}
{{- else -}}
{{ printf "%s:%s" .Values.image.repository .Values.image.tag }}
{{- end -}}
{{- end -}}
{{- define "montralog.environment" -}}
- name: MONTRALOG_READ_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.auth.existingSecret }}
      key: {{ .Values.auth.readTokenKey }}
- name: MONTRALOG_INGEST_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.auth.existingSecret }}
      key: {{ .Values.auth.ingestTokenKey }}
{{- if .Values.encryption.existingSecret }}
- name: MONTRALOG_ENCRYPTION_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.encryption.existingSecret }}
      key: {{ .Values.encryption.key }}
- name: MONTRALOG_ENCRYPTION_REQUIRED
  value: "true"
{{- end }}
- name: MONTRALOG_COOKIE_SECURE
  value: {{ ternary "true" "false" .Values.ingress.enabled | quote }}
- name: MONTRALOG_DB
  value: /data/montralog.db
- name: RETENTION_DAYS
  value: {{ .Values.retentionDays | quote }}
{{- if .Values.collector.enabled }}
- name: MONTRALOG_ALLOW_INSECURE_COLLECTOR
  value: "true"
- name: MONTRALOG_COLLECTOR_URL
  value: {{ printf "http://%s-collector:4318" (include "montralog.fullname" .) | quote }}
{{- end }}
- name: PROMETHEUS_URL
  value: {{ if .Values.prometheus.enabled }}{{ printf "http://%s-prometheus:9090" (include "montralog.fullname" .) | quote }}{{ else }}{{ .Values.prometheus.externalUrl | quote }}{{ end }}
{{- if eq .Values.database.mode "postgresql" }}
- name: MONTRALOG_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.database.existingSecret }}
      key: {{ .Values.database.urlKey }}
{{- end }}
{{- end -}}
{{- define "montralog.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
capabilities:
  drop: [ALL]
{{- end -}}
