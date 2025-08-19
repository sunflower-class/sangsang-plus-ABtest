import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base

# 데이터베이스 설정
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./abtest.db")

# SQLite를 사용하는 경우 (개발용)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "isolation_level": None  # autocommit 모드
        },
        poolclass=StaticPool,
        pool_pre_ping=True,  # 연결 유효성 검사
        echo=False  # SQL 로깅 비활성화
    )
else:
    # PostgreSQL을 사용하는 경우 (운영용)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db_session():
    """데이터베이스 세션 반환 (컨텍스트 매니저용)"""
    return SessionLocal()

# 초기 테이블 생성
create_tables()
