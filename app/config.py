import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    db_host: str = "localhost"
    db_user: str = "pw"
    db_password: str = ""
    db_name: str = "pw"

    pass_type: int = 1
    server_ip: str = "0.0.0.0"
    lan_ip: str = "127.0.0.1"
    server_port: int = 29400
    server_path: str = "/home/server/"
    admin_id: int = 0
    admin_pw: str = ""
    akey1: str = ""
    akey2: str = ""

    server_ver: int = 75

    start_gold: int = 0
    start_point: int = 0
    max_web_point: int = 9999
    point_exc: int = 1

    secret_key: str
    app_port: int = 8420

    pw_classes: str = "{}"
    gs_zones: str = "{}"
    server_files: str = "{}"

    @property
    def pw_classes_dict(self) -> dict[int, str]:
        return {int(k): v for k, v in json.loads(self.pw_classes).items()}

    @property
    def gs_zones_dict(self) -> dict[str, dict]:
        raw = json.loads(self.gs_zones)
        return {
            k: (v if isinstance(v, dict) else {"name": v})
            for k, v in raw.items()
        }

    @property
    def server_files_dict(self) -> dict[int, str]:
        return {int(k): v for k, v in json.loads(self.server_files).items()}


settings = Settings()
