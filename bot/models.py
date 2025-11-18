from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base
import enum


class Role(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    lead = "lead"
    manager = "manager"


class Status(str, enum.Enum):
    online = "online"
    busy = "busy"
    offline = "offline"


class Direction(str, enum.Enum):
    transfers = "transfers"
    alipay = "alipay"
    service = "service"


class OrderStatus(str, enum.Enum):
    new = "new"
    active = "active"
    closed = "closed"


class Manager(Base):
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    tg_user_id = Column(Integer, nullable=True, unique=True)
    role = Column(Enum(Role), default=Role.manager, nullable=False)
    status = Column(Enum(Status), default=Status.offline, nullable=False)

    clients = relationship("Client", back_populates="manager")
    orders = relationship("Order", back_populates="manager")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    manager_id = Column(Integer, ForeignKey("managers.id"), nullable=True)
    manager = relationship("Manager", back_populates="clients")

    current_direction = Column(Enum(Direction), nullable=True)

    orders = relationship("Order", back_populates="client")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String, unique=True, nullable=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("managers.id"), nullable=False)

    direction = Column(Enum(Direction), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.active, nullable=False)

    amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String, nullable=True)
    service_desc = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    client = relationship("Client", back_populates="orders")
    manager = relationship("Manager", back_populates="orders")
