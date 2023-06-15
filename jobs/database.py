from datetime import datetime
import sqlalchemy
from typing import List, Optional
from sqlalchemy import (
    ForeignKey,
    String,
    DateTime,
    Integer,
    create_engine,
    select,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "Users"

    id: Mapped[int] = mapped_column(primary_key=True)
    timezone: Mapped[str]


class Requests(Base):
    __tablename__ = "Requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    message: Mapped[str]
    date: Mapped[datetime]
    type: Mapped[str]


class Huomenet(Base):
    __tablename__ = "Huomenet"

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    hour: Mapped[int]


class HuomentaResponses(Base):
    __tablename__ = "HuomentaResponses"

    id: Mapped[int] = mapped_column(primary_key=True)
    response: Mapped[str] = mapped_column(unique=True)
    rarity: Mapped[int]
    rat: Mapped[int]


class HuomentaUserStats(Base):
    __tablename__ = "HuomentaUserStats"

    id: Mapped[int] = mapped_column(ForeignKey("Users.id"), primary_key=True)
    foundlist: Mapped[Optional[str]]
    rarelist: Mapped[Optional[str]]
    ultralist: Mapped[Optional[str]]
    lastdate: Mapped[Optional[datetime]]


class LotteryPlayers(Base):
    __tablename__ = "LotteryPlayers"

    id: Mapped[int] = mapped_column(ForeignKey("Users.id"), primary_key=True)
    credits: Mapped[int]
    sub: Mapped[bool]


class CurrentLottery(Base):
    __tablename__ = "CurrentLottery"

    id: Mapped[int] = mapped_column(primary_key=True)
    pool: Mapped[int]
    startdate: Mapped[datetime]


class LotteryBets(Base):
    __tablename__ = "LotteryBets"

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    roundid: Mapped[int] = mapped_column(ForeignKey("CurrentLottery.id"))
    row: Mapped[str]


class LotteryWins(Base):
    __tablename__ = "LotteryWins"

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    roundid: Mapped[int] = mapped_column(ForeignKey("CurrentLottery.id"))
    payout: Mapped[int]
    date: Mapped[datetime]


class Alcoholist(Base):
    __tablename__ = "Alcoholist"

    id: Mapped[int] = mapped_column(ForeignKey("Users.id"), primary_key=True)
    weight: Mapped[int]
    r: Mapped[float]
    bac: Mapped[float]


class Alarms(Base):
    __tablename__ = "Alarms"

    id: Mapped[int] = mapped_column(ForeignKey("Users.id"), primary_key=True)
    time: Mapped[Optional[int]]
    weekdays: Mapped[Optional[str]]
    last: Mapped[Optional[datetime]]
    snooze: Mapped[Optional[int]]


engine = create_engine("sqlite+pysqlite:///data/database.db")
