import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.hash import HashService
from src.db.database import async_session
from src.models.model import (
    City,
    CompanyType,
    Currency,
    District,
    EducationalInstitution,
    EmploymentType,
    Experience,
    Profession,
    Region,
    Role,
    SettlementType,
    Skill,
    Status,
    User,
    WorkSchedule,
)

ROLES = [
    {"name": "admin"},
    {"name": "company"},
    {"name": "applicant"},
]

REGIONS = [
    "Брестская область",
    "Витебская область",
    "Гомельская область",
    "Гродненская область",
    "Минская область",
    "Могилёвская область",
]

SETTLEMENT_TYPES = [
    "город",
    "агрогородок",
    "деревня",
    "поселок",
]

DISTRICTS = [
    {"name": "Брестский район", "region": "Брестская область"},
    {"name": "Барановичский район", "region": "Брестская область"},
    {"name": "Берёзовский район", "region": "Брестская область"},
    {"name": "Дрогичинский район", "region": "Брестская область"},
    {"name": "Жабинковский район", "region": "Брестская область"},
    {"name": "Ивановский район", "region": "Брестская область"},
    {"name": "Ивацевичский район", "region": "Брестская область"},
    {"name": "Каменецкий район", "region": "Брестская область"},
    {"name": "Кобринский район", "region": "Брестская область"},
    {"name": "Лунинецкий район", "region": "Брестская область"},
    {"name": "Пинский район", "region": "Брестская область"},
    {"name": "Пружанский район", "region": "Брестская область"},
    {"name": "Столинский район", "region": "Брестская область"},

    {"name": "Витебский район", "region": "Витебская область"},
    {"name": "Браславский район", "region": "Витебская область"},
    {"name": "Глубокский район", "region": "Витебская область"},
    {"name": "Докшицкий район", "region": "Витебская область"},
    {"name": "Лепельский район", "region": "Витебская область"},
    {"name": "Оршанский район", "region": "Витебская область"},
    {"name": "Полоцкий район", "region": "Витебская область"},
    {"name": "Поставский район", "region": "Витебская область"},
    {"name": "Сенненский район", "region": "Витебская область"},
    {"name": "Толочинский район", "region": "Витебская область"},
    {"name": "Чашникский район", "region": "Витебская область"},

    {"name": "Гомельский район", "region": "Гомельская область"},
    {"name": "Брагинский район", "region": "Гомельская область"},
    {"name": "Буда-Кошелёвский район", "region": "Гомельская область"},
    {"name": "Ветковский район", "region": "Гомельская область"},
    {"name": "Добрушский район", "region": "Гомельская область"},
    {"name": "Житковичский район", "region": "Гомельская область"},
    {"name": "Жлобинский район", "region": "Гомельская область"},
    {"name": "Калинковичский район", "region": "Гомельская область"},
    {"name": "Мозырский район", "region": "Гомельская область"},
    {"name": "Речицкий район", "region": "Гомельская область"},
    {"name": "Рогачёвский район", "region": "Гомельская область"},
    {"name": "Светлогорский район", "region": "Гомельская область"},

    {"name": "Гродненский район", "region": "Гродненская область"},
    {"name": "Берестовицкий район", "region": "Гродненская область"},
    {"name": "Волковысский район", "region": "Гродненская область"},
    {"name": "Вороновский район", "region": "Гродненская область"},
    {"name": "Зельвенский район", "region": "Гродненская область"},
    {"name": "Ивьевский район", "region": "Гродненская область"},
    {"name": "Лидский район", "region": "Гродненская область"},
    {"name": "Новогрудский район", "region": "Гродненская область"},
    {"name": "Островецкий район", "region": "Гродненская область"},
    {"name": "Ошмянский район", "region": "Гродненская область"},
    {"name": "Слонимский район", "region": "Гродненская область"},
    {"name": "Сморгонский район", "region": "Гродненская область"},
    {"name": "Щучинский район", "region": "Гродненская область"},

    {"name": "Минский район", "region": "Минская область"},
    {"name": "Березинский район", "region": "Минская область"},
    {"name": "Борисовский район", "region": "Минская область"},
    {"name": "Дзержинский район", "region": "Минская область"},
    {"name": "Крупский район", "region": "Минская область"},
    {"name": "Молодечненский район", "region": "Минская область"},
    {"name": "Мядельский район", "region": "Минская область"},
    {"name": "Слуцкий район", "region": "Минская область"},
    {"name": "Солигорский район", "region": "Минская область"},
    {"name": "Столбцовский район", "region": "Минская область"},

    {"name": "Могилёвский район", "region": "Могилёвская область"},
    {"name": "Бобруйский район", "region": "Могилёвская область"},
    {"name": "Быховский район", "region": "Могилёвская область"},
    {"name": "Горецкий район", "region": "Могилёвская область"},
    {"name": "Кировский район", "region": "Могилёвская область"},
    {"name": "Климовичский район", "region": "Могилёвская область"},
    {"name": "Кричевский район", "region": "Могилёвская область"},
    {"name": "Мстиславский район", "region": "Могилёвская область"},
    {"name": "Осиповичский район", "region": "Могилёвская область"},
    {"name": "Чаусский район", "region": "Могилёвская область"},
    {"name": "Шкловский район", "region": "Могилёвская область"},
]

CITIES = [
    {"name": "Брест", "district": "Брестский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Барановичи", "district": "Барановичский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Берёза", "district": "Берёзовский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Дрогичин", "district": "Дрогичинский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Жабинка", "district": "Жабинковский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Иваново", "district": "Ивановский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Ивацевичи", "district": "Ивацевичский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Каменец", "district": "Каменецкий район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Кобрин", "district": "Кобринский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Лунинец", "district": "Лунинецкий район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Пинск", "district": "Пинский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Пружаны", "district": "Пружанский район", "region": "Брестская область", "settlement_type": "город"},
    {"name": "Столин", "district": "Столинский район", "region": "Брестская область", "settlement_type": "город"},

    {"name": "Витебск", "district": "Витебский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Браслав", "district": "Браславский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Глубокое", "district": "Глубокский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Докшицы", "district": "Докшицкий район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Лепель", "district": "Лепельский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Орша", "district": "Оршанский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Полоцк", "district": "Полоцкий район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Новополоцк", "district": "Полоцкий район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Поставы", "district": "Поставский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Сенно", "district": "Сенненский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Толочин", "district": "Толочинский район", "region": "Витебская область", "settlement_type": "город"},
    {"name": "Чашники", "district": "Чашникский район", "region": "Витебская область", "settlement_type": "город"},

    {"name": "Гомель", "district": "Гомельский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Брагин", "district": "Брагинский район", "region": "Гомельская область", "settlement_type": "поселок"},
    {"name": "Буда-Кошелёво", "district": "Буда-Кошелёвский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Ветка", "district": "Ветковский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Добруш", "district": "Добрушский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Житковичи", "district": "Житковичский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Жлобин", "district": "Жлобинский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Калинковичи", "district": "Калинковичский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Мозырь", "district": "Мозырский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Речица", "district": "Речицкий район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Рогачёв", "district": "Рогачёвский район", "region": "Гомельская область", "settlement_type": "город"},
    {"name": "Светлогорск", "district": "Светлогорский район", "region": "Гомельская область", "settlement_type": "город"},

    {"name": "Гродно", "district": "Гродненский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Большая Берестовица", "district": "Берестовицкий район", "region": "Гродненская область", "settlement_type": "поселок"},
    {"name": "Волковыск", "district": "Волковысский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Вороново", "district": "Вороновский район", "region": "Гродненская область", "settlement_type": "поселок"},
    {"name": "Зельва", "district": "Зельвенский район", "region": "Гродненская область", "settlement_type": "поселок"},
    {"name": "Ивье", "district": "Ивьевский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Лида", "district": "Лидский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Новогрудок", "district": "Новогрудский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Островец", "district": "Островецкий район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Ошмяны", "district": "Ошмянский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Слоним", "district": "Слонимский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Сморгонь", "district": "Сморгонский район", "region": "Гродненская область", "settlement_type": "город"},
    {"name": "Щучин", "district": "Щучинский район", "region": "Гродненская область", "settlement_type": "город"},

    {"name": "Минск", "district": "Минский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Березино", "district": "Березинский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Борисов", "district": "Борисовский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Жодино", "district": "Борисовский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Дзержинск", "district": "Дзержинский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Крупки", "district": "Крупский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Молодечно", "district": "Молодечненский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Мядель", "district": "Мядельский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Слуцк", "district": "Слуцкий район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Солигорск", "district": "Солигорский район", "region": "Минская область", "settlement_type": "город"},
    {"name": "Столбцы", "district": "Столбцовский район", "region": "Минская область", "settlement_type": "город"},

    {"name": "Могилёв", "district": "Могилёвский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Бобруйск", "district": "Бобруйский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Быхов", "district": "Быховский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Горки", "district": "Горецкий район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Кировск", "district": "Кировский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Климовичи", "district": "Климовичский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Кричев", "district": "Кричевский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Мстиславль", "district": "Мстиславский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Осиповичи", "district": "Осиповичский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Чаусы", "district": "Чаусский район", "region": "Могилёвская область", "settlement_type": "город"},
    {"name": "Шклов", "district": "Шкловский район", "region": "Могилёвская область", "settlement_type": "город"},
]

PROFESSIONS = [
    "Программист", "Веб-разработчик", "Системный администратор", "DevOps-инженер",
    "Тестировщик", "Аналитик", "Data Scientist", "ML-инженер", "UI/UX-дизайнер",
    "Product Manager", "Project Manager", "Scrum-мастер", "Технический писатель",
    "Инженер", "Электрик", "Сварщик", "Строитель", "Архитектор", "Прораб",
    "Механик", "Технолог", "Конструктор", "Геодезист",
    "Врач", "Медсестра", "Фармацевт", "Учитель", "Преподаватель", "Воспитатель",
    "Педагог", "Психолог", "Логопед",
    "Продавец", "Кассир", "Мерчендайзер", "Супервайзер", "Администратор",
    "Официант", "Повар", "Кондитер", "Пекарь", "Бармен", "Бариста",
    "Парикмахер", "Косметолог", "Маникюрша", "Фитнес-тренер",
    "Водитель", "Машинист", "Курьер", "Логист", "Кладовщик", "Грузчик",
    "Экспедитор", "Дальнобойщик", "Таксист",
    "Бухгалтер", "Экономист", "Финансист", "Аудитор", "Налоговый консультант",
    "Юрист", "Адвокат", "Нотариус", "Юрисконсульт",
    "Маркетолог", "SMM-менеджер", "Таргетолог", "Копирайтер", "PR-менеджер",
    "SEO-специалист", "Аналитик рекламы",
    "Менеджер по продажам", "Менеджер по работе с клиентами", "Офис-менеджер",
    "Секретарь", "Делопроизводитель", "HR-менеджер", "Рекрутер",
    "Слесарь", "Токарь", "Фрезеровщик", "Столяр", "Плотник", "Маляр",
    "Штукатур", "Каменщик", "Бетонщик", "Кровельщик", "Сантехник",
    "Агроном", "Ветеринар", "Зоотехник", "Тракторист", "Комбайнёр",
    "Доярка", "Птицевод",
    "Актёр", "Музыкант", "Художник", "Дизайнер", "Фотограф", "Видеооператор",
    "Режиссёр", "Сценарист", "Аниматор",
    "Спортсмен", "Тренер", "Инструктор",
]

SKILLS = [
    "Python", "SQL", "JavaScript", "HTML", "CSS", "React", "Vue.js", "Node.js",
    "Django", "Flask", "FastAPI", "Java", "C#", "C++", "PHP", "Ruby", "Go",
    "Rust", "Kotlin", "Swift", "1С", "Photoshop", "Illustrator", "Figma",
    "AutoCAD", "SolidWorks", "Компас-3D", "Excel", "Word", "PowerPoint",
    "Linux", "Windows Server", "Docker", "Kubernetes", "Git", "CI/CD",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Kafka",
    "Hadoop", "Spark", "Tableau", "Power BI", "SAP", "CRM", "ERP",
    "Английский язык", "Немецкий язык", "Французский язык", "Польский язык",
    "Китайский язык", "Испанский язык", "Итальянский язык",
    "Коммуникабельность", "Ответственность", "Работа в команде", "Лидерство",
    "Креативность", "Стрессоустойчивость", "Обучаемость", "Тайм-менеджмент",
    "Организаторские способности", "Переговорные навыки", "Презентационные навыки",
    "Навыки продаж", "Ведение переговоров", "Управление проектами",
    "Аналитическое мышление", "Критическое мышление", "Внимание к деталям",
    "Сметное дело", "Кадровое делопроизводство", "Бухгалтерский учёт",
    "Налоговый учёт", "Международные стандарты финансовой отчётности",
    "Управление персоналом", "Проведение тренингов", "Техника продаж",
    "Работа с возражениями", "Холодные звонки", "В2B-продажи", "В2C-продажи",
    "Медицинские знания", "Педагогические навыки", "Вождение автомобиля",
    "Права категории B", "Права категории C", "Права категории D", "Права категории E",
    "Работа с оргтехникой", "1С:Предприятие", "Гарант", "КонсультантПлюс",
]

WORK_SCHEDULES = [
    "5/2",
    "2/2",
    "3/2",
    "4/3",
    "1/2",
    "4/4",
    "2/1",
]

EMPLOYMENT_TYPES = [
    "Гибрид",
    "На месте работадателя",
    "Удаленно",
]

COMPANY_TYPES = [
    "ООО",
    "ЗАО",
    "ОАО",
    "АО",
    "ИП",
    "ЧУП",
    "УП",
    "ОДО",
]

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

CURRENCIES = [
    "BYN",
    "RUB",
    "USD",
    "EUR",
]

EXPERIENCES = [
    "Без опыта",
    "Менее 1 года",
    "От 1 года до 3 лет",
    "От 3 до 6 лет",
    "Более 6 лет",
]

STATUSES = [
    "Активна",
    "В архиве",
]


async def seed_roles(db: AsyncSession) -> None:
    for role_data in ROLES:
        existing = await db.execute(select(Role).where(Role.name == role_data["name"]))
        if not existing.scalar_one_or_none():
            db.add(Role(**role_data))
    await db.flush()
    print("✅ Роли обработаны.")


async def get_or_create_by_name(db: AsyncSession, model, name: str):
    existing = await db.execute(select(model).where(model.name == name))
    item = existing.scalar_one_or_none()

    if item:
        return item

    item = model(name=name)
    db.add(item)
    await db.flush()
    return item


async def seed_regions(db: AsyncSession) -> None:
    for region_name in REGIONS:
        await get_or_create_by_name(db, Region, region_name)
    await db.flush()
    print("✅ Области обработаны.")


async def seed_settlement_types(db: AsyncSession) -> None:
    for settlement_type_name in SETTLEMENT_TYPES:
        await get_or_create_by_name(db, SettlementType, settlement_type_name)
    await db.flush()
    print("✅ Типы населённых пунктов обработаны.")


async def seed_districts(db: AsyncSession) -> None:
    for district_data in DISTRICTS:
        region = await get_or_create_by_name(db, Region, district_data["region"])

        existing = await db.execute(
            select(District).where(
                District.name == district_data["name"],
                District.region_id == region.id,
            )
        )

        if not existing.scalar_one_or_none():
            db.add(
                District(
                    name=district_data["name"],
                    region_id=region.id,
                )
            )

    await db.flush()
    print("✅ Районы обработаны.")


async def seed_cities(db: AsyncSession) -> None:
    for city_data in CITIES:
        region = await get_or_create_by_name(db, Region, city_data["region"])

        district_result = await db.execute(
            select(District).where(
                District.name == city_data["district"],
                District.region_id == region.id,
            )
        )
        district = district_result.scalar_one_or_none()

        if not district:
            district = District(
                name=city_data["district"],
                region_id=region.id,
            )
            db.add(district)
            await db.flush()

        settlement_type = await get_or_create_by_name(
            db,
            SettlementType,
            city_data["settlement_type"],
        )

        existing = await db.execute(
            select(City).where(
                City.name == city_data["name"],
                City.district_id == district.id,
                City.settlement_type_id == settlement_type.id,
            )
        )

        if not existing.scalar_one_or_none():
            db.add(
                City(
                    name=city_data["name"],
                    district_id=district.id,
                    settlement_type_id=settlement_type.id,
                )
            )

    await db.flush()
    print("✅ Населённые пункты обработаны.")


async def seed_professions(db: AsyncSession) -> None:
    for prof_name in PROFESSIONS:
        existing = await db.execute(select(Profession).where(Profession.name == prof_name))
        if not existing.scalar_one_or_none():
            db.add(Profession(name=prof_name))
    await db.flush()
    print("✅ Профессии обработаны.")


async def seed_skills(db: AsyncSession) -> None:
    for skill_name in SKILLS:
        existing = await db.execute(select(Skill).where(Skill.name == skill_name))
        if not existing.scalar_one_or_none():
            db.add(Skill(name=skill_name))
    await db.flush()
    print("✅ Навыки обработаны.")


async def seed_work_schedules(db: AsyncSession) -> None:
    for schedule_name in WORK_SCHEDULES:
        existing = await db.execute(select(WorkSchedule).where(WorkSchedule.name == schedule_name))
        if not existing.scalar_one_or_none():
            db.add(WorkSchedule(name=schedule_name))
    await db.flush()
    print("✅ Графики работы обработаны.")


async def seed_employment_types(db: AsyncSession) -> None:
    for et_name in EMPLOYMENT_TYPES:
        existing = await db.execute(select(EmploymentType).where(EmploymentType.name == et_name))
        if not existing.scalar_one_or_none():
            db.add(EmploymentType(name=et_name))
    await db.flush()
    print("✅ Типы занятости обработаны.")


async def seed_company_types(db: AsyncSession) -> None:
    for ct_name in COMPANY_TYPES:
        existing = await db.execute(select(CompanyType).where(CompanyType.name == ct_name))
        if not existing.scalar_one_or_none():
            db.add(CompanyType(name=ct_name))
    await db.flush()
    print("✅ Типы компаний обработаны.")


async def seed_educational_institutions(db: AsyncSession) -> None:
    for inst_name in EDUCATIONAL_INSTITUTIONS:
        existing = await db.execute(
            select(EducationalInstitution).where(EducationalInstitution.name == inst_name)
        )
        if not existing.scalar_one_or_none():
            db.add(EducationalInstitution(name=inst_name))
    await db.flush()
    print("✅ Учреждения образования обработаны.")


async def seed_currencies(db: AsyncSession) -> None:
    for currency_name in CURRENCIES:
        existing = await db.execute(select(Currency).where(Currency.name == currency_name))
        if not existing.scalar_one_or_none():
            db.add(Currency(name=currency_name))
    await db.flush()
    print("✅ Валюты обработаны.")


async def seed_experiences(db: AsyncSession) -> None:
    for exp_name in EXPERIENCES:
        existing = await db.execute(select(Experience).where(Experience.name == exp_name))
        if not existing.scalar_one_or_none():
            db.add(Experience(name=exp_name))
    await db.flush()
    print("✅ Опыт работы обработан.")


async def seed_statuses(db: AsyncSession) -> None:
    for status_name in STATUSES:
        existing = await db.execute(select(Status).where(Status.name == status_name))
        if not existing.scalar_one_or_none():
            db.add(Status(name=status_name))
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
        password=hashed_password,
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

        await seed_regions(db)
        await seed_settlement_types(db)
        await seed_districts(db)
        await seed_cities(db)

        await seed_professions(db)
        await seed_skills(db)
        await seed_work_schedules(db)
        await seed_employment_types(db)
        await seed_company_types(db)
        await seed_educational_institutions(db)
        await seed_currencies(db)
        await seed_experiences(db)
        await seed_statuses(db)
        await seed_admin_user(db)

        await db.commit()
        print("🎉 Все справочники и администратор успешно созданы.")


if __name__ == "__main__":
    asyncio.run(seed_all())
