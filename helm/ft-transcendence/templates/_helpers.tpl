{{/*
Service names are fixed: the services reach each other through hostnames
hardcoded in their settings, startup scripts and nginx.conf (postgresql, redis,
users, website, game-server). Install one release per namespace.
*/}}

{{- define "ft.labels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/part-of: ft-transcendence
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .root.Chart.Name .root.Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "ft.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end }}

{{- define "ft.image" -}}
{{- printf "%s:%s" .repository (toString .tag) -}}
{{- end }}

{{- define "ft.secretName" -}}
{{- .Values.secrets.existingSecret | default (printf "%s-secrets" .Release.Name) -}}
{{- end }}

{{- define "ft.ipAddress" -}}
{{- required "ipAddress is required: the hostname or IP browsers use to reach the site" .Values.ipAddress -}}
{{- end }}

{{/* Value given in values.yaml, else the one already stored, else a random one. */}}
{{- define "ft.secretValue" -}}
{{- $stored := index . 0 -}}
{{- $key := index . 1 -}}
{{- $value := index . 2 -}}
{{- if $value -}}
{{- $value | b64enc | quote -}}
{{- else if hasKey $stored $key -}}
{{- index $stored $key | quote -}}
{{- else -}}
{{- randAlphaNum 48 | b64enc | quote -}}
{{- end -}}
{{- end }}

{{- define "ft.pullSecrets" -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{- define "ft.secretEnv" -}}
- name: {{ .name }}
  valueFrom:
    secretKeyRef:
      name: {{ include "ft.secretName" .root }}
      key: {{ .name }}
{{- end }}

{{- define "ft.env.ipAddress" -}}
- name: IP_ADDRESS
  value: {{ include "ft.ipAddress" . | quote }}
{{- end }}

{{- define "ft.env.postgres" -}}
{{ include "ft.secretEnv" (dict "root" . "name" "POSTGRES_USER") }}
{{ include "ft.secretEnv" (dict "root" . "name" "POSTGRES_PASSWORD") }}
{{- end }}

{{- define "ft.env.django" -}}
{{ include "ft.secretEnv" (dict "root" . "name" "DJANGO_SECRET_KEY") }}
{{- end }}

{{/* The services run migrations before listening, so give them time to start. */}}
{{- define "ft.httpProbes" -}}
startupProbe:
  tcpSocket:
    port: {{ .port }}
  periodSeconds: 5
  failureThreshold: 60
readinessProbe:
  tcpSocket:
    port: {{ .port }}
  periodSeconds: 10
livenessProbe:
  tcpSocket:
    port: {{ .port }}
  periodSeconds: 20
  failureThreshold: 3
{{- end }}
