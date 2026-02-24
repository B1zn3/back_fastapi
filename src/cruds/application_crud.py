from src.cruds.base_crud import BaseCrud
from src.models.model import Application

class ApplicationCrud(BaseCrud):
    def __init__(self):
        super().__init__(Application)

applicationcrud = ApplicationCrud()