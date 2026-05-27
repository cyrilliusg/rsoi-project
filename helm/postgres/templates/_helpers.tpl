{{- define "postgres.fullname" -}}
{{- default "postgres" .Values.service.name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "postgres.labels" -}}
app.kubernetes.io/name: {{ include "postgres.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "postgres.selectorLabels" -}}
app.kubernetes.io/name: {{ include "postgres.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
