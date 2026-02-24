from src.cruds.base_crud import BaseCrud
from src.models.model import Education

class EducationCrud(BaseCrud):
    def __init__(self):
        super().__init__(Education)

educationcrud = EducationCrud()