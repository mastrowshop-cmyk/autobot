from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    token: str
    db: str
    admin_panel_token: str


def load_config() -> Config:
    return Config(
        token=os.getenv("BOT_TOKEN", ""),
        db=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./oplatym.db"),
        admin_panel_token=os.getenv("ADMIN_PANEL_TOKEN", "change_me_super_secret"),
    )
