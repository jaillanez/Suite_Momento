"""Valores iniciales configurables del seguimiento familiar."""

DEFAULT_WORKFLOW_STATUSES = (
    {
        "code": "received",
        "label": "Recibida",
        "display_order": 1,
        "is_active": True,
        "family_visible": True,
    },
    {
        "code": "assigned",
        "label": "Asignada",
        "display_order": 2,
        "is_active": True,
        "family_visible": True,
    },
    {
        "code": "in_progress",
        "label": "En atención",
        "display_order": 3,
        "is_active": True,
        "family_visible": True,
    },
    {
        "code": "responded",
        "label": "Respondida",
        "display_order": 4,
        "is_active": True,
        "family_visible": True,
    },
    {
        "code": "closed",
        "label": "Cerrada",
        "display_order": 5,
        "is_active": True,
        "family_visible": True,
    },
)
