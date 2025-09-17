# app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Mapped, mapped_column
from sqlalchemy import String, BigInteger, Boolean, Text, Integer, insert, select, text

from app.config import settings

engine = create_async_engine(settings.DB_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Channel(Base):
    __tablename__ = "channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(Text)
    chat_id: Mapped[str] = mapped_column(String(100), nullable=True)  # Временно nullable
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Promotion(Base):
    __tablename__ = "promotions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    welcome_text: Mapped[str] = mapped_column(Text, default="Добро пожаловать!")
    welcome_photo: Mapped[str] = mapped_column(Text, nullable=True)
    action_url: Mapped[str] = mapped_column(Text, default="https://example.com")
    click_count: Mapped[int] = mapped_column(BigInteger, default=0)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Обновляем существующие каналы, добавляя chat_id если его нет
        await conn.execute(
            text("UPDATE channels SET chat_id = '@channel1' WHERE id = 1 AND chat_id IS NULL")
        )
        await conn.execute(
            text("UPDATE channels SET chat_id = '@channel2' WHERE id = 2 AND chat_id IS NULL")
        )
        
        # Добавляем два канала по умолчанию, если их нет
        default_channels = [
            {"id": 1, "name": "Канал1", "url": "https://example.com/channel1", "chat_id": "@channel1"},
            {"id": 2, "name": "Канал2", "url": "https://example.com/channel2", "chat_id": "@channel2"}
        ]
        
        for channel_data in default_channels:
            exists = await conn.execute(
                select(Channel).where(Channel.id == channel_data["id"])
            )
            if not exists.scalar_one_or_none():
                await conn.execute(
                    insert(Channel).values(
                        id=channel_data["id"],
                        name=channel_data["name"],
                        url=channel_data["url"],
                        chat_id=channel_data["chat_id"],
                        is_active=True
                    )
                )
        await conn.commit()