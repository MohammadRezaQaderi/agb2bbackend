from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

from helper.db.sqlalchemy.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(Unicode(12), nullable=False)
    password: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    role: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)

    institute: Mapped["Institute | None"] = relationship(back_populates="user")
    school: Mapped["School | None"] = relationship(back_populates="user")
    owner_consultant: Mapped["OwnerConsultant | None"] = relationship(back_populates="user")
    consultant_profile: Mapped["Consultant | None"] = relationship(
        back_populates="user",
        foreign_keys="Consultant.user_id",
    )
    student_profile: Mapped["Student | None"] = relationship(
        back_populates="user",
        foreign_keys="Student.user_id",
    )


class Institute(Base, TimestampMixin):
    __tablename__ = "ins"

    ins_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    verify: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="institute")


class School(Base, TimestampMixin):
    __tablename__ = "sch"

    sch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    verify: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="school")


class OwnerConsultant(Base, TimestampMixin):
    __tablename__ = "ocon"

    ocon_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    sex: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verify: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="owner_consultant")


class Consultant(Base, TimestampMixin):
    __tablename__ = "con"

    con_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    sex: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(
        back_populates="consultant_profile",
        foreign_keys=[user_id],
    )
    owner: Mapped[User | None] = relationship(foreign_keys=[owner_user_id])


class Student(Base, TimestampMixin):
    __tablename__ = "stu"

    stu_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    sex: Mapped[int | None] = mapped_column(Integer, nullable=True)
    city: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    access: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    comment: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    birth_date: Mapped[str | None] = mapped_column(Unicode(4), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    consultant_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    adder_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(
        back_populates="student_profile",
        foreign_keys=[user_id],
    )
    owner: Mapped[User | None] = relationship(foreign_keys=[owner_user_id])
    consultant_user: Mapped[User | None] = relationship(foreign_keys=[consultant_user_id])


class Capacity(Base, TimestampMixin):
    __tablename__ = "capacity"

    capacity_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)

    packages: Mapped[list["CapacityPackage"]] = relationship(back_populates="capacity")


class CapacityPackage(Base, TimestampMixin):
    __tablename__ = "capacity_package"

    capacity_package_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capacity_id: Mapped[int | None] = mapped_column(ForeignKey("capacity.capacity_id"), nullable=True)
    package_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    total_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    capacity: Mapped[Capacity | None] = relationship(back_populates="packages")


class StudentPackageAccess(Base, TimestampMixin):
    __tablename__ = "student_package_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stu_user_id: Mapped[int] = mapped_column(ForeignKey("stu.user_id"), nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    consultant_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    package_name: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    permission: Mapped[int] = mapped_column(Integer, nullable=False)
    limit: Mapped[int] = mapped_column("limit", Integer, nullable=False)


class Token(Base, TimestampMixin):
    __tablename__ = "tokens"

    token_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    quiz_kind: Mapped[str] = mapped_column(String(25), nullable=False)
    quiz_id: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[int] = mapped_column(Integer, nullable=False)
    remain_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    consultant_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)


class QuizQuestionAnswer(Base, TimestampMixin):
    __tablename__ = "quiz_question_answer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("quiz_attempt.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    quiz_kind: Mapped[str] = mapped_column(String(25), nullable=False)
    quiz_id: Mapped[int] = mapped_column(Integer, nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, nullable=False)
    answer_value: Mapped[str] = mapped_column(UnicodeText, nullable=False)


class Score(Base, TimestampMixin):
    __tablename__ = "scores"

    scores_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    quiz_score: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    brain_fields: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    brain_categories: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    brain_branches: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)


class SclScore(Base, TimestampMixin):
    __tablename__ = "scl_scores"

    scores_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    scl_date: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)


__all__ = [
    "Capacity",
    "CapacityPackage",
    "Consultant",
    "Institute",
    "OwnerConsultant",
    "QuizAttempt",
    "QuizQuestionAnswer",
    "School",
    "SclScore",
    "Score",
    "Student",
    "StudentPackageAccess",
    "Token",
    "User",
]
