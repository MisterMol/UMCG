def platforms_context(request):
    return {
        "platforms": [
            {"name": "Vodafone", "url": "/automation/vodafone"},
            {"name": "KPN", "url": "/automation/kpn"},
            {"name": "Mitel", "url": "/automation/mitel"},
            {"name": "Micollab", "url": "/automation/micollab"},
            {"name": "DevOps", "url": "/automation/devops"},
        ]
    }
