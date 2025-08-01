from __future__ import annotations

from django import forms

from .models import DashboardConfig


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
