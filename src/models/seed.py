import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import async_session
from src.models.model import (
    Role,
    City,
    Profession,
    Skill,
    WorkSchedule,
    EmploymentType,
    EducationalInstitution,
    Currency,
    Experience,
    Status,
    User,
)
from src.core.hash import HashService

# === Роли ===
ROLES = [
    {"name": "admin"},
    {"name": "company"},
    {"name": "applicant"},
]

# === Города Беларуси (все областные и районные центры) ===
CITIES = [
    "Минск", "Гомель", "Могилёв", "Витебск", "Гродно", "Брест",
    "Бобруйск", "Барановичи", "Борисов", "Пинск", "Орша", "Мозырь",
    "Солигорск", "Новополоцк", "Лида", "Молодечно", "Полоцк", "Жлобин",
    "Светлогорск", "Речица", "Слуцк", "Жодино", "Кобрин", "Волковыск",
    "Калинковичи", "Сморгонь", "Осиповичи", "Рогачёв", "Горки", "Березино",
    "Дзержинск", "Ивацевичи", "Лунинец", "Марьина Горка", "Столбцы",
    "Глубокое", "Лепель", "Новогрудок", "Слоним", "Добруш", "Житковичи",
    "Климовичи", "Кричев", "Мстиславль", "Чаусы", "Чериков", "Шклов",
    "Быхов", "Кировск", "Костюковичи", "Краснополье", "Крупки", "Мядель",
    "Поставы", "Толочин", "Чашники", "Шарковщина", "Верхнедвинск",
    "Браслав", "Докшицы", "Ушачи", "Россоны", "Миоры", "Городок",
    "Дубровно", "Лиозно", "Сенно", "Мир", "Бешенковичи",
    "Шумилино", "Берестовица", "Вороново", "Зельва", "Ивье", "Кореличи",
    "Мосты", "Островец", "Ошмяны", "Свислочь", "Щучин", "Берёза",
    "Ганцевичи", "Дрогичин", "Жабинка", "Иваново", "Каменец", "Кобрин",
    "Ляховичи", "Малорита", "Пружаны", "Столин", "Брагин", "Буда-Кошелёво",
    "Ветка", "Ельск", "Корма", "Лельчицы", "Лоев", "Наровля", "Октябрьский",
    "Петриков", "Хойники", "Чечерск"
]

# === Профессии (расширенный список) ===
PROFESSIONS = [
    # IT и разработка
    "Программист", "Веб-разработчик", "Системный администратор", "DevOps-инженер",
    "Тестировщик", "Аналитик", "Data Scientist", "ML-инженер", "UI/UX-дизайнер",
    "Product Manager", "Project Manager", "Scrum-мастер", "Технический писатель",
    # Инженерия и производство
    "Инженер", "Электрик", "Сварщик", "Строитель", "Архитектор", "Прораб",
    "Механик", "Технолог", "Конструктор", "Геодезист",
    # Медицина и образование
    "Врач", "Медсестра", "Фармацевт", "Учитель", "Преподаватель", "Воспитатель",
    "Педагог", "Психолог", "Логопед",
    # Торговля и услуги
    "Продавец", "Кассир", "Мерчендайзер", "Супервайзер", "Администратор",
    "Официант", "Повар", "Кондитер", "Пекарь", "Бармен", "Бариста",
    "Парикмахер", "Косметолог", "Маникюрша", "Фитнес-тренер",
    # Транспорт и логистика
    "Водитель", "Машинист", "Курьер", "Логист", "Кладовщик", "Грузчик",
    "Экспедитор", "Дальнобойщик", "Таксист",
    # Финансы и бухгалтерия
    "Бухгалтер", "Экономист", "Финансист", "Аудитор", "Налоговый консультант",
    # Юриспруденция
    "Юрист", "Адвокат", "Нотариус", "Юрисконсульт",
    # Маркетинг и реклама
    "Маркетолог", "SMM-менеджер", "Таргетолог", "Копирайтер", "PR-менеджер",
    "SEO-специалист", "Аналитик рекламы",
    # Управление и офис
    "Менеджер по продажам", "Менеджер по работе с клиентами", "Офис-менеджер",
    "Секретарь", "Делопроизводитель", "HR-менеджер", "Рекрутер",
    # Рабочие специальности
    "Слесарь", "Токарь", "Фрезеровщик", "Столяр", "Плотник", "Маляр",
    "Штукатур", "Каменщик", "Бетонщик", "Кровельщик", "Сантехник",
    # Сельское хозяйство
    "Агроном", "Ветеринар", "Зоотехник", "Тракторист", "Комбайнёр",
    "Доярка", "Птицевод",
    # Искусство и развлечения
    "Актёр", "Музыкант", "Художник", "Дизайнер", "Фотограф", "Видеооператор",
    "Режиссёр", "Сценарист", "Аниматор",
    # Спорт
    "Спортсмен", "Тренер", "Инструктор"
]

# === Навыки (расширенный список) ===
SKILLS = [
    # Технические
    "Python", "SQL", "JavaScript", "HTML", "CSS", "React", "Vue.js", "Node.js",
    "Django", "Flask", "FastAPI", "Java", "C#", "C++", "PHP", "Ruby", "Go",
    "Rust", "Kotlin", "Swift", "1С", "Photoshop", "Illustrator", "Figma",
    "AutoCAD", "SolidWorks", "Компас-3D", "Excel", "Word", "PowerPoint",
    "Linux", "Windows Server", "Docker", "Kubernetes", "Git", "CI/CD",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Kafka",
    "Hadoop", "Spark", "Tableau", "Power BI", "SAP", "CRM", "ERP",
    # Языковые
    "Английский язык", "Немецкий язык", "Французский язык", "Польский язык",
    "Китайский язык", "Испанский язык", "Итальянский язык",
    # Личностные
    "Коммуникабельность", "Ответственность", "Работа в команде", "Лидерство",
    "Креативность", "Стрессоустойчивость", "Обучаемость", "Тайм-менеджмент",
    "Организаторские способности", "Переговорные навыки", "Презентационные навыки",
    "Навыки продаж", "Ведение переговоров", "Управление проектами",
    "Аналитическое мышление", "Критическое мышление", "Внимание к деталям",
    # Специализированные
    "Сметное дело", "Кадровое делопроизводство", "Бухгалтерский учёт",
    "Налоговый учёт", "Международные стандарты финансовой отчётности",
    "Управление персоналом", "Проведение тренингов", "Техника продаж",
    "Работа с возражениями", "Холодные звонки", "В2B-продажи", "В2C-продажи",
    "Медицинские знания", "Педагогические навыки", "Вождение автомобиля",
    "Права категории B", "Права категории C", "Права категории D", "Права категории E",
    "Работа с оргтехникой", "1С:Предприятие", "Гарант", "КонсультантПлюс"
]

# === Графики работы ===
WORK_SCHEDULES = [
    "Полный день",
    "Сменный график",
    "Гибкий график",
    "Удаленная работа",
    "Вахтовый метод",
    "Вахта",
    "Свободный график",
]

# === Типы занятости ===
EMPLOYMENT_TYPES = [
    "Полная занятость",
    "Частичная занятость",
    "Стажировка",
    "Проектная работа",
    "Волонтерство",
    "Временная работа",
    "Сезонная работа",
]

# === Учебные заведения Беларуси (расширенный список) ===
EDUCATIONAL_INSTITUTIONS = [
    "Белорусский государственный университет (БГУ)",
    "Белорусский национальный технический университет (БНТУ)",
    "Белорусский государственный университет информатики и радиоэлектроники (БГУИР)",
    "Белорусский государственный экономический университет (БГЭУ)",
    "Минский государственный лингвистический университет (МГЛУ)",
    "Белорусский государственный медицинский университет (БГМУ)",
    "Гродненский государственный университет имени Янки Купалы",
    "Витебский государственный университет имени П.М. Машерова",
    "Могилёвский государственный университет имени А.А. Кулешова",
    "Полесский государственный университет",
    "Брестский государственный университет имени А.С. Пушкина",
    "Гомельский государственный университет имени Франциска Скорины",
    "Белорусский государственный технологический университет",
    "Белорусский государственный аграрный технический университет",
    "Академия управления при Президенте Республики Беларусь",
    "Минский государственный колледж электроники",
    "Минский государственный колледж сферы обслуживания",
    "Минский государственный профессионально-технический колледж строительства",
    "Гомельский государственный колледж связи",
    "Витебский государственный колледж культуры и искусств",
    "Белорусский государственный педагогический университет имени Максима Танка",
    "Белорусская государственная академия искусств",
    "Белорусская государственная академия музыки",
    "Белорусский государственный университет физической культуры",
    "Минский инновационный университет",
    "Частный институт управления и предпринимательства",
    "Международный университет «МИТСО»",
]

# === Валюты (контекст РБ) ===
CURRENCIES = [
    "BYN",
    "RUB",
    "USD",
    "EUR",
]

# === Опыт работы ===
EXPERIENCES = [
    "Без опыта",
    "Менее 1 года",
    "От 1 года до 3 лет",
    "От 3 до 6 лет",
    "Более 6 лет",
]

# === Статусы вакансий ===
STATUSES = [
    "Активна",
    "В архиве",
    "Приостановлена",
]

# === Вспомогательные функции ===
async def seed_roles(db: AsyncSession) -> None:
    for role_data in ROLES:
        existing = await db.execute(select(Role).where(Role.name == role_data["name"]))
        if not existing.scalar_one_or_none():
            role = Role(**role_data)
            db.add(role)
    await db.flush()
    print("✅ Роли обработаны.")

async def seed_cities(db: AsyncSession) -> None:
    for city_name in CITIES:
        existing = await db.execute(select(City).where(City.name == city_name))
        if not existing.scalar_one_or_none():
            city = City(name=city_name)
            db.add(city)
    await db.flush()
    print("✅ Города обработаны.")

async def seed_professions(db: AsyncSession) -> None:
    for prof_name in PROFESSIONS:
        existing = await db.execute(select(Profession).where(Profession.name == prof_name))
        if not existing.scalar_one_or_none():
            profession = Profession(name=prof_name)
            db.add(profession)
    await db.flush()
    print("✅ Профессии обработаны.")

async def seed_skills(db: AsyncSession) -> None:
    for skill_name in SKILLS:
        existing = await db.execute(select(Skill).where(Skill.name == skill_name))
        if not existing.scalar_one_or_none():
            skill = Skill(name=skill_name)
            db.add(skill)
    await db.flush()
    print("✅ Навыки обработаны.")

async def seed_work_schedules(db: AsyncSession) -> None:
    for schedule_name in WORK_SCHEDULES:
        existing = await db.execute(select(WorkSchedule).where(WorkSchedule.name == schedule_name))
        if not existing.scalar_one_or_none():
            schedule = WorkSchedule(name=schedule_name)
            db.add(schedule)
    await db.flush()
    print("✅ Графики работы обработаны.")

async def seed_employment_types(db: AsyncSession) -> None:
    for et_name in EMPLOYMENT_TYPES:
        existing = await db.execute(select(EmploymentType).where(EmploymentType.name == et_name))
        if not existing.scalar_one_or_none():
            emp_type = EmploymentType(name=et_name)
            db.add(emp_type)
    await db.flush()
    print("✅ Типы занятости обработаны.")

async def seed_educational_institutions(db: AsyncSession) -> None:
    for inst_name in EDUCATIONAL_INSTITUTIONS:
        existing = await db.execute(select(EducationalInstitution).where(EducationalInstitution.name == inst_name))
        if not existing.scalar_one_or_none():
            institution = EducationalInstitution(name=inst_name)
            db.add(institution)
    await db.flush()
    print("✅ Учреждения образования обработаны.")

async def seed_currencies(db: AsyncSession) -> None:
    for currency_name in CURRENCIES:
        existing = await db.execute(select(Currency).where(Currency.name == currency_name))
        if not existing.scalar_one_or_none():
            currency = Currency(name=currency_name)
            db.add(currency)
    await db.flush()
    print("✅ Валюты обработаны.")

async def seed_experiences(db: AsyncSession) -> None:
    for exp_name in EXPERIENCES:
        existing = await db.execute(select(Experience).where(Experience.name == exp_name))
        if not existing.scalar_one_or_none():
            exp = Experience(name=exp_name)
            db.add(exp)
    await db.flush()
    print("✅ Опыт работы обработан.")

async def seed_statuses(db: AsyncSession) -> None:
    for status_name in STATUSES:
        existing = await db.execute(select(Status).where(Status.name == status_name))
        if not existing.scalar_one_or_none():
            status = Status(name=status_name)
            db.add(status)
    await db.flush()
    print("✅ Статусы обработаны.")

async def seed_admin_user(db: AsyncSession) -> None:
    result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    if not admin_role:
        print("⚠️ Роль admin не найдена, администратор не создан.")
        return

    existing = await db.execute(select(User).where(User.email == "admin@example.com"))
    if existing.scalar_one_or_none():
        print("ℹ️ Администратор уже существует.")
        return

    hashed_password = HashService.get_password_hash("admin123")
    admin_user = User(
        email="admin@example.com",
        password=hashed_password,  # В модели поле называется password, не password_hash
        role_id=admin_role.id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        company_id=None,
        applicant_id=None,
    )
    db.add(admin_user)
    await db.flush()
    print("✅ Создан пользователь-администратор (admin@example.com / admin123).")

async def seed_all():
    async with async_session() as db:
        await seed_roles(db)
        await seed_cities(db)
        await seed_professions(db)
        await seed_skills(db)
        await seed_work_schedules(db)
        await seed_employment_types(db)
        await seed_educational_institutions(db)
        await seed_currencies(db)
        await seed_experiences(db)
        await seed_statuses(db)
        await seed_admin_user(db)

        await db.commit()
        print("🎉 Все справочники и администратор успешно созданы.")

if __name__ == "__main__":
    asyncio.run(seed_all())