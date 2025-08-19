from __future__ import annotations

from django import forms

from .models import (
    DashboardConfig,
    DashboardCustomMetric,
    DashboardFilter,
    DashboardLayout,
)


class DashboardConfigForm(forms.ModelForm):
    class Meta:
        model = DashboardConfig
        fields = ["nome", "publico"]

    def save(self, user, config_data, commit: bool = True):
        instance: DashboardConfig = super().save(commit=False)
        instance.user = user
        instance.config = config_data
        if commit:
            instance.save()
        return instance


class DashboardFilterForm(forms.ModelForm):
    class Meta:
        model = DashboardFilter
        fields = ["nome", "publico"]

    def save(self, user, filtros_data, commit: bool = True):
        instance: DashboardFilter = super().save(commit=False)
        instance.user = user
        allowed = {"metricas", "organizacao_id", "nucleo_id", "evento_id", "data_inicio", "data_fim"}
        instance.filtros = {k: v for k, v in filtros_data.items() if k in allowed}
        if commit:
            instance.save()
        return instance


class DashboardLayoutForm(forms.ModelForm):
    class Meta:
        model = DashboardLayout
        fields = ["nome", "publico"]

    def save(self, user, layout_data, commit: bool = True):
        instance: DashboardLayout = super().save(commit=False)
        instance.user = user
        instance.layout_json = layout_data
        if commit:
            instance.save()
        return instance


class DashboardCustomMetricForm(forms.ModelForm):
    class Meta:
        model = DashboardCustomMetric
        fields = ["code", "nome", "descricao", "query_spec", "escopo"]
