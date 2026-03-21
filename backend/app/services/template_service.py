from jinja2 import Environment, BaseLoader
from typing import Dict, Any


class TemplateService:
    def __init__(self):
        self.env = Environment(loader=BaseLoader())
    
    def render(self, template_content: str, variables: Dict[str, Any]) -> str:
        template = self.env.from_string(template_content)
        return template.render(**variables)
    
    def validate(self, template_content: str) -> tuple[bool, str]:
        try:
            self.env.from_string(template_content)
            return True, "Template is valid"
        except Exception as e:
            return False, str(e)
