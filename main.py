import os
import gitlab
import json
import pytz
from datetime import datetime

domain = os.getenv('GITLAB_DOMAIN')
token = os.getenv('GITLAB_PRIVATE_TOKEN')
login = os.getenv('GITLAB_LOGIN')

if not token:
    raise ValueError("Token environment variable are not set")

if not domain:
    raise ValueError("Domain environment variable are not set")

if not login:
    raise ValueError("Login environment variable are not set")

base_url_with_auth = f'https://{login}:{token}@{domain}'

gl = gitlab.Gitlab(domain, private_token=token)

groups = gl.groups.list(all=True)

moscow_tz = pytz.timezone('Europe/Moscow')
configuration = {
    "name": f"index-{datetime.now(moscow_tz).strftime('%Y-%m-%d %H:%M:%S')}",
    "repositories": []
}

projects_set = set()
for group in groups:
    # Получаем все проекты группы и оставляем только подходящие под наши условия (приватности)
    projects = group.projects.list(get_all=True)
    for project in projects:
        # только активные и открытые проекты (необязательное условие, если в токене заложены ограничения)
        if project.archived or project.visibility == 'private' or project.can_create_merge_request_in == False:
            continue

        # проверка уникальности проектов (например скринеры безопасности есть во многих группах)
        if project.path_with_namespace in projects_set:
            continue
        projects_set.add(project.path_with_namespace)

        # Формирование конфигурацию под каждый репозиторий
        repo_config = {
            # путь к папке, все изначально клонируется в WORKDIR докерфайла
            "path": project.name, 
            # имя репозитория, включая родительские папки (позволяет настроить фильтрацию по командам)
            "name": project.path_with_namespace, 
            # индексируемая ветка
            "revisions": [project.default_branch], 
            "metadata": {
                # паттерн который будет применятся для редиректа в гитлаб
                "url_pattern": f"{project.web_url}/-/blob/{project.default_branch}/{{path}}#L{{lno}}",
                # путь для скачивания репозитория
                "remote": base_url_with_auth + project.web_url.replace(f'https://{domain}', '')
            }
        }
        configuration["repositories"].append(repo_config)

with open("configuration.json", "w") as f:
    json.dump(configuration, f, indent=4)
