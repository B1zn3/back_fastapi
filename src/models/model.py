from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, DateTime, Date, Boolean, Integer, ForeignKey, Table, Column
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


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    applicants: Mapped[List["Applicant"]] = relationship(back_populates="city")
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="city")
    companies: Mapped[List["Company"]] = relationship(
        secondary=company_cities,
        back_populates="cities"
    )
'''"Полная занятость",
    "Частичная занятость",
    "Стажировка",
    "Проектная работа",
    "Волонтерство"'''
class EmploymentType(Base):
    __tablename__ = "employment_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="employment_type")

''' "Полный день",
    "Сменный график",
    "Гибкий график",
    "Удаленная работа",
    "Вахтовый метод"'''
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
        secondary=vacancy_skills, back_populates="skills"
    )
    resumes: Mapped[List["Resume"]] = relationship(
        secondary=resume_skills, back_populates="skills"
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


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String)
    logo: Mapped[Optional[str]] = mapped_column(String)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped[Optional["User"]] = relationship(back_populates="company", uselist=False)
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="company")
    cities: Mapped[List["City"]] = relationship(
        secondary=company_cities,
        back_populates="companies"
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

    role: Mapped["Role"] = relationship(back_populates="user")
    company: Mapped[Optional["Company"]] = relationship(back_populates="user")
    applicant: Mapped[Optional["Applicant"]] = relationship(back_populates="user")


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
    work_experiences: Mapped[List["WorkExperience"]] = relationship(back_populates="resume")


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
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

    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey("vacancies.id"), primary_key=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)

    vacancy: Mapped["Vacancy"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship(back_populates="applications")

