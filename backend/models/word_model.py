"""
Word database schema using SQLAlchemy.
backend/models/word_model.py
"""

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, Boolean, Text, JSON, DateTime
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

Path("backend/data").mkdir(parents=True, exist_ok=True)

Base = declarative_base()
DATABASE_URL = "sqlite:///backend/data/words.db"


class Word(Base):
    __tablename__ = "words"

    id              = Column(Integer, primary_key=True)
    word            = Column(String(100), unique=True,
                             nullable=False, index=True)
    grade_level     = Column(Integer, nullable=False,
                             index=True)
    difficulty      = Column(String(20), index=True)

    # Phonetics
    syllables       = Column(String(200))
    syllable_count  = Column(Integer)
    phonetic        = Column(String(200))
    ipa             = Column(String(200))
    audio_file      = Column(String(500))
    stress_pattern  = Column(String(20))

    # Grammar
    part_of_speech  = Column(String(50))
    other_forms     = Column(JSON)

    # Meaning
    definition      = Column(Text)
    child_definition = Column(Text)
    examples        = Column(JSON)

    # Memory aids
    mnemonic_text   = Column(Text)
    mnemonic_emoji  = Column(String(50))
    image_url       = Column(String(500))

    # Etymology
    root_word       = Column(String(100))
    root_meaning    = Column(String(200))
    root_language   = Column(String(50))
    prefix          = Column(String(100))
    suffix          = Column(String(100))
    language_of_origin = Column(String(50))

    # Relationships
    synonyms        = Column(JSON)
    antonyms        = Column(JSON)
    word_family     = Column(JSON)
    related_words   = Column(JSON)

    # Categorisation
    genres          = Column(JSON)
    sub_sector      = Column(String(50))
    scripps_level   = Column(String(50))
    frequency_rank  = Column(Integer)
    is_verified     = Column(Boolean, default=False)

    # Source tracking
    source          = Column(String(100))
    created_at      = Column(DateTime,
                             default=datetime.utcnow)
    updated_at      = Column(DateTime,
                             default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "word":             self.word,
            "grade_level":      self.grade_level,
            "difficulty":       self.difficulty,
            "syllables":        self.syllables,
            "phonetic":         self.phonetic,
            "ipa":              self.ipa,
            "audio_file":       self.audio_file,
            "part_of_speech":   self.part_of_speech,
            "other_forms":      self.other_forms or {},
            "definition":       self.definition,
            "child_definition": self.child_definition,
            "examples":         self.examples or [],
            "mnemonic_text":    self.mnemonic_text,
            "mnemonic_emoji":   self.mnemonic_emoji,
            "root_word":        self.root_word,
            "root_meaning":     self.root_meaning,
            "root_language":    self.root_language,
            "language_of_origin": self.language_of_origin,
            "synonyms":         self.synonyms or [],
            "antonyms":         self.antonyms or [],
            "word_family":      self.word_family or [],
            "genres":           self.genres or [],
            "frequency_rank":   self.frequency_rank,
        }


class StudentProgress(Base):
    __tablename__ = "student_progress"

    id             = Column(Integer, primary_key=True)
    student_id     = Column(String(100), index=True)
    word_id        = Column(Integer, index=True)
    word           = Column(String(100))
    error_count    = Column(Integer, default=0)
    correct_count  = Column(Integer, default=0)
    last_attempted = Column(DateTime)
    is_mastered    = Column(Boolean, default=False)
    flag_revision  = Column(Boolean, default=False)
    common_error   = Column(String(100))


class Session(Base):
    __tablename__ = "sessions"

    id               = Column(Integer, primary_key=True)
    session_id       = Column(String(100), unique=True)
    student_id       = Column(String(100), index=True)
    started_at       = Column(DateTime)
    ended_at         = Column(DateTime)
    duration_seconds = Column(Integer)
    mode             = Column(String(20))
    grade_level      = Column(Integer)
    words_attempted  = Column(Integer, default=0)
    words_correct    = Column(Integer, default=0)
    accuracy         = Column(Float)
    hints_used       = Column(Integer, default=0)


class WordAttempt(Base):
    __tablename__ = "word_attempts"

    id               = Column(Integer, primary_key=True)
    session_id       = Column(String(100), index=True)
    student_id       = Column(String(100), index=True)
    word             = Column(String(100))
    typed_spelling   = Column(String(100))
    is_correct       = Column(Boolean)
    error_type       = Column(String(50))
    attempt_number   = Column(Integer)
    time_taken_sec   = Column(Integer)
    hint_used        = Column(Boolean, default=False)
    hint_type        = Column(String(50))
    timestamp        = Column(DateTime,
                              default=datetime.utcnow)


def get_engine():
    return create_engine(DATABASE_URL)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("✅ Database initialised: backend/data/words.db")
    return engine


def get_session():
    engine = get_engine()
    Session_factory = sessionmaker(bind=engine)
    return Session_factory()


if __name__ == "__main__":
    init_db()