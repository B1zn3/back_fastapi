from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


company_cities = Table(
    "company_cities",
    Base.metadata,
    Column("company_id", Integer, ForeignKey("companies.id"), nullable=False),
    Column("city_id", Integer, ForeignKey("cities.id"), nullable=False),
)

vacancy_skills = Table(
    "vacancy_skills",
    Base.metadata,
    Column("vacancy_id", Integer, ForeignKey("vacancies.id"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
)

resume_skills = Table(
    "resume_skills",
    Base.metadata,
    Column("resume_id", Integer, ForeignKey("resumes.id"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
)

resume_favorite_vacancies = Table(
    "resume_favorite_vacancies",
    Base.metadata,
    Column("resume_id", Integer, ForeignKey("resumes.id"), primary_key=True, nullable=False),
    Column("favorite_vacancy_id", Integer, ForeignKey("favorite_vacancies.id"), primary_key=True, nullable=False),
)




class EmploymentType(Base):
    __tablename__ = "employment_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="employment_type")


class WorkSchedule(Base):
    __tablename__ = "work_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="work_schedule")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(
        secondary=vacancy_skills,
        back_populates="skills",
    )
    resumes: Mapped[List["Resume"]] = relationship(
        secondary=resume_skills,
        back_populates="skills",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    user: Mapped["User"] = relationship(back_populates="role", uselist=False)


class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("cities.id"))
    photo: Mapped[Optional[str]] = mapped_column(String)
    phone: Mapped[Optional[str]] = mapped_column(String, unique=True)
    birth_date: Mapped[Optional[datetime]] = mapped_column(Date)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    middle_name: Mapped[Optional[str]] = mapped_column(String)
    gender: Mapped[Optional[str]] = mapped_column(String)

    city: Mapped[Optional["City"]] = relationship(back_populates="applicants")
    user: Mapped[Optional["User"]] = relationship(back_populates="applicant", uselist=False)
    resumes: Mapped[List["Resume"]] = relationship(back_populates="applicant")
    educations: Mapped[List["Education"]] = relationship(back_populates="applicant")

class CompanyType(Base):
    __tablename__ = "company_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    companies: Mapped[List["Company"]] = relationship(back_populates="company_type")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String)
    logo: Mapped[Optional[str]] = mapped_column(String)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)
    company_type_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("company_types.id"),
        nullable=True,
        index=True,
    )

    company_type: Mapped[Optional["CompanyType"]] = relationship(back_populates="companies")
    user: Mapped[Optional["User"]] = relationship(back_populates="company", uselist=False)
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="company")
    cities: Mapped[List["City"]] = relationship(
        secondary=company_cities,
        back_populates="companies",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("companies.id"), unique=True)
    applicant_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("applicants.id"), unique=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    
    role: Mapped["Role"] = relationship(back_populates="user")
    company: Mapped[Optional["Company"]] = relationship(back_populates="user")
    applicant: Mapped[Optional["Applicant"]] = relationship(back_populates="user")
    messages: Mapped[List["Message"]] = relationship(back_populates="sender")


class Profession(Base):
    __tablename__ = "professions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="profession")
    resumes: Mapped[List["Resume"]] = relationship(back_populates="profession")


class Currency(Base):
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="currency")


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="experience")


class Status(Base):
    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="status")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employment_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("employment_types.id"), nullable=False)
    work_schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("work_schedules.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), nullable=False)
    experience_id: Mapped[int] = mapped_column(Integer, ForeignKey("experiences.id"), nullable=False)
    status_id: Mapped[int] = mapped_column(Integer, ForeignKey("statuses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    city_id: Mapped[int] = mapped_column(Integer, ForeignKey("cities.id"), nullable=False)
    profession_id: Mapped[int] = mapped_column(Integer, ForeignKey("professions.id"), nullable=False)

    employment_type: Mapped["EmploymentType"] = relationship(back_populates="vacancies")
    work_schedule: Mapped["WorkSchedule"] = relationship(back_populates="vacancies")
    currency: Mapped["Currency"] = relationship(back_populates="vacancies")
    experience: Mapped["Experience"] = relationship(back_populates="vacancies")
    status: Mapped["Status"] = relationship(back_populates="vacancies")
    company: Mapped["Company"] = relationship(back_populates="vacancies")
    city: Mapped["City"] = relationship(back_populates="vacancies")
    profession: Mapped["Profession"] = relationship(back_populates="vacancies")
    skills: Mapped[List["Skill"]] = relationship(secondary=vacancy_skills, back_populates="vacancies")
    applications: Mapped[List["Application"]] = relationship(back_populates="vacancy")

    favorite_records: Mapped[List["FavoriteVacancy"]] = relationship(
        back_populates="vacancy",
        cascade="all, delete-orphan",
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profession_id: Mapped[int] = mapped_column(Integer, ForeignKey("professions.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    applicant_id: Mapped[int] = mapped_column(Integer, ForeignKey("applicants.id"), nullable=False)

    profession: Mapped["Profession"] = relationship(back_populates="resumes")
    applicant: Mapped["Applicant"] = relationship(back_populates="resumes")
    skills: Mapped[List["Skill"]] = relationship(secondary=resume_skills, back_populates="resumes")
    applications: Mapped[List["Application"]] = relationship(back_populates="resume")
    work_experiences: Mapped[List["WorkExperience"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    changes: Mapped[List["ResumeChange"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    favorite_vacancies: Mapped[List["FavoriteVacancy"]] = relationship(secondary=resume_favorite_vacancies, back_populates="resumes")


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    resume: Mapped["Resume"] = relationship(back_populates="work_experiences")


class EducationalInstitution(Base):
    __tablename__ = "educational_institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    educations: Mapped[List["Education"]] = relationship(back_populates="institution")


class Education(Base):
    __tablename__ = "educations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    applicant_id: Mapped[int] = mapped_column(Integer, ForeignKey("applicants.id"), nullable=False)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey("educational_institutions.id"), nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)

    applicant: Mapped["Applicant"] = relationship(back_populates="educations")
    institution: Mapped["EducationalInstitution"] = relationship(back_populates="educations")

    @property
    def institution_name(self) -> Optional[str]:
        return self.institution.name if self.institution else None


class Application(Base):
    __tablename__ = "applications"

    __table_args__ = (
        UniqueConstraint("vacancy_id", "resume_id", name="uq_applications_vacancy_resume"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey("vacancies.id"), nullable=False, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String, nullable=False)
    cover_letter: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    vacancy: Mapped["Vacancy"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship(back_populates="applications")
    chat: Mapped[Optional["Chat"]] = relationship(back_populates="application", uselist=False)

class ResumeChange(Base):
    __tablename__ = "resume_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    resume: Mapped["Resume"] = relationship(back_populates="changes")

class FavoriteVacancy(Base):
    __tablename__ = "favorite_vacancies"

    __table_args__ = (UniqueConstraint("vacancy_id", name="uq_favorite_vacancies_vacancy_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey("vacancies.id"), nullable=False, index=True,)
    
    vacancy: Mapped["Vacancy"] = relationship(back_populates="favorite_records")
    resumes: Mapped[List["Resume"]] = relationship(secondary=resume_favorite_vacancies, back_populates="favorite_vacancies")

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id"), nullable=False, unique=True, index=True,)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow,)

    application: Mapped["Application"] = relationship(back_populates="chat")
    messages: Mapped[List["Message"]] = relationship(back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"), nullable=False, index=True,)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True,)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    chat: Mapped["Chat"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship(back_populates="messages")
    attachments: Mapped[List["MessageAttachment"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    message: Mapped["Message"] = relationship(back_populates="attachments")

class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    districts: Mapped[List["District"]] = relationship(back_populates="region", cascade="all, delete-orphan")


class District(Base):
    __tablename__ = "districts"

    __table_args__ = (
        UniqueConstraint("region_id", "name", name="uq_district_region_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    region: Mapped["Region"] = relationship(back_populates="districts")
    cities: Mapped[List["City"]] = relationship(back_populates="district", cascade="all, delete-orphan")


class SettlementType(Base):
    __tablename__ = "settlement_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    cities: Mapped[List["City"]] = relationship(back_populates="settlement_type")


class City(Base):
    __tablename__ = "cities"

    __table_args__ = (
        UniqueConstraint("district_id", "settlement_type_id", "name", name="uq_city_district_type_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    district_id: Mapped[int] = mapped_column(Integer, ForeignKey("districts.id"), nullable=False, index=True)
    settlement_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("settlement_types.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    district: Mapped["District"] = relationship(back_populates="cities")
    settlement_type: Mapped["SettlementType"] = relationship(back_populates="cities")
    applicants: Mapped[List["Applicant"]] = relationship(back_populates="city")
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="city")
    companies: Mapped[List["Company"]] = relationship(secondary=company_cities, back_populates="cities" )

    @property
    def full_name(self) -> str:
        settlement_type = self.settlement_type.name if self.settlement_type else ""
        district = self.district.name if self.district else ""
        region = self.district.region.name if self.district and self.district.region else ""

        parts = [
            f"{settlement_type} {self.name}".strip(),
            district,
            region,
        ]
        return ", ".join(part for part in parts if part)