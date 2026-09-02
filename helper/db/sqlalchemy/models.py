from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Identity, Integer, String, Text, Unicode, UnicodeText
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

    ins_id: Mapped[int | None] = mapped_column(Integer, Identity(), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    verify: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="institute")


class School(Base, TimestampMixin):
    __tablename__ = "sch"

    sch_id: Mapped[int | None] = mapped_column(Integer, Identity(), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    verify: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="school")


class OwnerConsultant(Base, TimestampMixin):
    __tablename__ = "ocon"

    ocon_id: Mapped[int | None] = mapped_column(Integer, Identity(), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    sex: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verify: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="owner_consultant")


class Consultant(Base, TimestampMixin):
    __tablename__ = "con"

    con_id: Mapped[int | None] = mapped_column(Integer, Identity(), nullable=True)
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

    stu_id: Mapped[int | None] = mapped_column(Integer, Identity(), nullable=True)
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


class CapacityLog(Base, TimestampMixin):
    __tablename__ = "capacity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity_package_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_name: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    change: Mapped[int | None] = mapped_column("change", Integer, nullable=True)


class StudentPackageAccess(Base, TimestampMixin):
    __tablename__ = "student_package_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stu_user_id: Mapped[int] = mapped_column(ForeignKey("stu.user_id"), nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    consultant_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    package_name: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    permission: Mapped[int] = mapped_column(Integer, nullable=False)
    limit: Mapped[int] = mapped_column("limit", Integer, nullable=False)


class Setting(Base, TimestampMixin):
    __tablename__ = "setting"

    setting_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    voice: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    quiz_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Token(Base, TimestampMixin):
    __tablename__ = "tokens"

    token_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)


class Payment(Base, TimestampMixin):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    phone: Mapped[str] = mapped_column(Unicode(12), nullable=False)
    state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    status: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    track_id: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    discount_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    saleReferenceId: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    token: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    product_data: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)


class PaymentLog(Base, TimestampMixin):
    __tablename__ = "payment_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    phone: Mapped[str] = mapped_column(Unicode(12), nullable=False)
    state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    status: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    track_id: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    discount_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    saleReferenceId: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    token: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    product_data: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)


class Discount(Base, TimestampMixin):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    discount_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_apply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    count_apply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UsingDiscount(Base, TimestampMixin):
    __tablename__ = "using_discount"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    phone: Mapped[str] = mapped_column(Unicode(12), nullable=False)


class OtpLog(Base, TimestampMixin):
    __tablename__ = "otp_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(12), nullable=True)
    code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    type_otp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    provider_resp: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)


class Product(Base, TimestampMixin):
    __tablename__ = "product"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Unicode(400), nullable=True)
    comment: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    persian_date: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    phone: Mapped[str] = mapped_column(Unicode(12), nullable=False)
    role: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    db_name: Mapped[str] = mapped_column(Unicode(400), nullable=False)


class ApiLog(Base, TimestampMixin):
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phone: Mapped[str | None] = mapped_column(Unicode(12), nullable=True)
    end_point: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    func_name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    data: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    error_p: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roles: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    description: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    added_by: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    priority: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    persian_date: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    full_text: Mapped[str | None] = mapped_column("fullText", UnicodeText, nullable=True)


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    created_time: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, nullable=True)


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


class QuizMissingAnswer(Base, TimestampMixin):
    __tablename__ = "quiz_missing_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RedisLog(Base, TimestampMixin):
    __tablename__ = "redis_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phone: Mapped[str | None] = mapped_column(Unicode(12), nullable=True)


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


class ResultState(Base, TimestampMixin):
    __tablename__ = "result_state"

    result_state_id: Mapped[int | None] = mapped_column(Integer, Identity(), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    t_state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    r_state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    e_state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    a_state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    m_state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    f_state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    i_state: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)


class HedayatField(Base, TimestampMixin):
    __tablename__ = "hedayat_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    suggested: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    other: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)


__all__ = [
    "ApiLog",
    "Capacity",
    "CapacityLog",
    "CapacityPackage",
    "Consultant",
    "Institute",
    "OwnerConsultant",
    "Comment",
    "Notification",
    "NotificationRead",
    "Payment",
    "PaymentLog",
    "Discount",
    "HedayatField",
    "UsingDiscount",
    "OtpLog",
    "Product",
    "QuizAttempt",
    "QuizQuestionAnswer",
    "QuizMissingAnswer",
    "RedisLog",
    "ResultState",
    "School",
    "SclScore",
    "Score",
    "Setting",
    "Student",
    "StudentPackageAccess",
    "Token",
    "User",
]
