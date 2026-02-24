from src.cruds.base_crud import BaseCrud
from src.models.model import WorkExperience

class WorkExperienceCrud(BaseCrud):
    def __init__(self):
        super().__init__(WorkExperience)

workexperiencecrud = WorkExperienceCrud()