import json
with open("config/config.json", "r") as _config:
    CONFIG = json.load(_config)
with open("config/serverSettings.json", "r") as _serverSettings:
    SERVER_SETTINGS = json.load(_serverSettings)
with open("config/localSettings.json", "r") as _localSettings:
    LOCAL_SETTINGS = json.load(_localSettings)