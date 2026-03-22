{{- define "padhal.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "padhal.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" (include "padhal.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "padhal.labels" -}}
app.kubernetes.io/name: {{ include "padhal.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}

{{- define "padhal.selectorLabels" -}}
app.kubernetes.io/name: {{ include "padhal.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "padhal.apiName" -}}
{{- printf "%s-api" (include "padhal.fullname" .) -}}
{{- end -}}

{{- define "padhal.frontendName" -}}
{{- printf "%s-frontend" (include "padhal.fullname" .) -}}
{{- end -}}

{{- define "padhal.redisName" -}}
{{- printf "%s-redis" (include "padhal.fullname" .) -}}
{{- end -}}

{{- define "padhal.imageTag" -}}
{{- if .component.image.tag -}}
{{- .component.image.tag -}}
{{- else if .root.Values.global.imageTag -}}
{{- .root.Values.global.imageTag -}}
{{- else -}}
{{- .root.Chart.AppVersion -}}
{{- end -}}
{{- end -}}
