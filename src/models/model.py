from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Date, Boolean, Numeric, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship


class Base(DeclarativeBase):
    pass


vacancy_skills = Table(
    'vacancy_skills',
    Base.metadata,
    Column('vacancy_id', Integer, ForeignKey('vacancies.id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True)
)

resume_skills = Table(
    'resume_skills',
    Base.metadata,
    Column('resume_id', Integer, ForeignKey('resumes.id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True)
)


class City(Base):
    __tablename__ = 'cities'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    applicants: Mapped[List["Applicant"]] = relationship(back_populates="city")
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="city")  


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    users: Mapped[List["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id'), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    role: Mapped["Role"] = relationship(back_populates="users")
    profile: Mapped[Optional["Profile"]] = relationship(back_populates="user", uselist=False)


class Company(Base):
    __tablename__ = 'companies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String)
    logo: Mapped[Optional[str]] = mapped_column(String)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)

    profile: Mapped[Optional["Profile"]] = relationship(back_populates="company", uselist=False)
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="company")


class Applicant(Base):
    __tablename__ = 'applicants'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    photo: Mapped[Optional[str]] = mapped_column(String)
    phone: Mapped[Optional[str]] = mapped_column(String)
    address: Mapped[Optional[str]] = mapped_column(String)
    birth_date: Mapped[Optional[Date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String)
    city_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('cities.id'))

    city: Mapped[Optional["City"]] = relationship(back_populates="applicants")
    profile: Mapped[Optional["Profile"]] = relationship(back_populates="applicant", uselist=False)
    resumes: Mapped[List["Resume"]] = relationship(back_populates="applicant")


class Profile(Base):
    __tablename__ = 'profiles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), unique=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('companies.id'), unique=True)
    applicant_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('applicants.id'), unique=True)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    middle_name: Mapped[Optional[str]] = mapped_column(String)

    user: Mapped[Optional["User"]] = relationship(back_populates="profile")
    company: Mapped[Optional["Company"]] = relationship(back_populates="profile")
    applicant: Mapped[Optional["Applicant"]] = relationship(back_populates="profile")


class Profession(Base):
    __tablename__ = 'professions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="profession")
    resumes: Mapped[List["Resume"]] = relationship(back_populates="profession")


class EmploymentType(Base):
    __tablename__ = 'employment_types'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)  

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="employment_type")


class WorkSchedule(Base):
    __tablename__ = 'work_schedules'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)  

    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="work_schedule")


class Skill(Base):
    __tablename__ = 'skills'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    vacancies: Mapped[List["Vacancy"]] = relationship(secondary=vacancy_skills, back_populates="skills")
    resumes: Mapped[List["Resume"]] = relationship(secondary=resume_skills, back_populates="skills")


class Vacancy(Base):
    __tablename__ = 'vacancies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    currency: Mapped[Optional[str]] = mapped_column(String)
    experience_required: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    profession_id: Mapped[int] = mapped_column(Integer, ForeignKey('professions.id'), nullable=False)
    employment_type_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('employment_types.id'))
    work_schedule_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('work_schedules.id'))
    city_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('cities.id'))  

    company: Mapped["Company"] = relationship(back_populates="vacancies")
    profession: Mapped["Profession"] = relationship(back_populates="vacancies")
    employment_type: Mapped[Optional["EmploymentType"]] = relationship(back_populates="vacancies")
    work_schedule: Mapped[Optional["WorkSchedule"]] = relationship(back_populates="vacancies")
    city: Mapped[Optional["City"]] = relationship(back_populates="vacancies")  
    skills: Mapped[List["Skill"]] = relationship(secondary=vacancy_skills, back_populates="vacancies")
    applications: Mapped[List["Application"]] = relationship(back_populates="vacancy")


class Resume(Base):
    __tablename__ = 'resumes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profession_id: Mapped[int] = mapped_column(Integer, ForeignKey('professions.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    applicant_id: Mapped[int] = mapped_column(Integer, ForeignKey('applicants.id'), nullable=False)

    profession: Mapped["Profession"] = relationship(back_populates="resumes")
    applicant: Mapped["Applicant"] = relationship(back_populates="resumes")
    skills: Mapped[List["Skill"]] = relationship(secondary=resume_skills, back_populates="resumes")
    applications: Mapped[List["Application"]] = relationship(back_populates="resume")
    work_experiences: Mapped[List["WorkExperience"]] = relationship(back_populates="resume")
    educations: Mapped[List["Education"]] = relationship(back_populates="resume")


class Application(Base):
    __tablename__ = 'applications'

    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey('vacancies.id'), primary_key=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey('resumes.id'), primary_key=True)
    status: Mapped[Optional[str]] = mapped_column(String, default='pending')

    vacancy: Mapped["Vacancy"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship(back_populates="applications")


class WorkExperience(Base):
    __tablename__ = 'work_experiences'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey('resumes.id'), nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[Date]] = mapped_column(Date)
    description: Mapped[Optional[str]] = mapped_column(Text)

    resume: Mapped["Resume"] = relationship(back_populates="work_experiences")


class EducationalInstitution(Base):
    __tablename__ = 'educational_institutions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    educations: Mapped[List["Education"]] = relationship(back_populates="institution")


class Education(Base):
    __tablename__ = 'educations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey('resumes.id'), nullable=False)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('educational_institutions.id'), nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[Date]] = mapped_column(Date)

    resume: Mapped["Resume"] = relationship(back_populates="educations")
    institution: Mapped["EducationalInstitution"] = relationship(back_populates="educations")