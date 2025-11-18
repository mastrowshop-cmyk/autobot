from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    token: str
    db: str
    superadmin_id: int
    manager_secret_code: str

def load_config() -> Config:
    return Config(
        token=os.getenv("BOT_TOKEN", ""),
        db=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./oplatym.db"),
        superadmin_id=int(os.getenv("SUPERADMIN_ID", "0")),
        manager_secret_code=os.getenv("MANAGER_SECRET_CODE", "Nikola"),
    )

