import requests
import os
import pandas as pd

# Yerel geliştirme ortamı için .env dosyasını yükle (GitHub Actions'da gerekmez)
if os.getenv("GITHUB_ACTIONS") != "true":
    from dotenv import load_dotenv
    load_dotenv()

# Ortam değişkenlerini al
api_token = os.getenv("CLICKUP_API_TOKEN")
team_id = os.getenv("TEAM_ID")
output_path = os.getenv("OUTPUT_PATH", "clickup_tasks_full.csv")

headers = {
    "Authorization": api_token
}

# 1. Görevleri al
tasks_url = f"https://api.clickup.com/api/v2/team/{team_id}/task"
tasks_params = {
    "archived": "false",
    "page": 0
}
tasks_response = requests.get(tasks_url, headers=headers, params=tasks_params)

# Hata kontrolü
if not tasks_response.ok:
    raise Exception(f"ClickUp API hatası: {tasks_response.status_code} - {tasks_response.text}")

tasks_data = tasks_response.json().get("tasks", [])
print(f"Toplam görev sayısı: {len(tasks_data)}")

tasks_list = []

# 2. Her görev için detayları topla
for task in tasks_data:
    task_id = task.get("id")
    priority = task.get("priority")
    priority_value = priority.get("priority") if priority else "None"
    tags = [tag['name'] for tag in task.get('tags', [])]
    time_estimate = task.get('time_estimate', 'None')
    assignee = task["assignees"][0]["username"] if task.get("assignees") else "Unassigned"

    # Özel alanlar
    custom_fields = {}
    for field in task.get('custom_fields', []):
        field_name = field.get('name', 'Unnamed Field')
        field_value = field.get('value', 'None')
        custom_fields[field_name] = field_value

    task_info = {
        "Task ID": task_id,
        "Name": task.get("name"),
        "Description": task.get("text_content"),
        "Status": task.get("status", {}).get("status", "Unknown"),
        "Assignee": assignee,
        "Due Date": task.get("due_date"),
        "Start Date": task.get("start_date"),
        "Created At": task.get("date_created"),
        "Updated At": task.get("date_updated"),
        "Priority": priority_value,
        "Tags": ', '.join(tags),
        "Time Estimate": time_estimate,
        "Parent Task ID": task.get("parent", "None"),
        "Task URL": task.get("url"),
        "Created By": task.get("creator", {}).get("username", "Unknown"),
        "List Name": task.get("list", {}).get("name", "Unknown"),
        "Folder Name": task.get("folder", {}).get("name", "Unknown"),
        "Space Name": task.get("space", {}).get("name", "Unknown")
    }

    task_info.update(custom_fields)

    # 3. Zaman girişlerini al
    time_url = f"https://api.clickup.com/api/v2/task/{task_id}/time_entries"
    time_response = requests.get(time_url, headers=headers)

    if time_response.ok:
        entries = time_response.json().get("data", [])
        task_info["Time Entry Count"] = len(entries)
        total_time = 0
        entry_descriptions = []
        entry_users = []
        entry_dates = []
        billable_flags = []

        for entry in entries:
            total_time += entry.get("duration", 0)
            entry_descriptions.append(entry.get("description", ""))
            entry_users.append(entry.get("user", {}).get("username", "Unknown"))
            start = entry.get("start", "")
            end = entry.get("end", "")
            entry_dates.append(f"{start} → {end}")
            billable_flags.append(str(entry.get("billable", False)))

        task_info["Total Time (ms)"] = total_time
        task_info["First Time Entry"] = entries[0]["start"] if entries else ""
        task_info["Last Time Entry"] = entries[-1]["end"] if entries else ""
        task_info["Time Entry Descriptions"] = " | ".join(entry_descriptions)
        task_info["Time Entry Users"] = " | ".join(entry_users)
        task_info["Entry Start-End Times"] = " | ".join(entry_dates)
        task_info["Billable Flags"] = " | ".join(billable_flags)
    else:
        task_info["Time Entry Count"] = 0
        task_info["Total Time (ms)"] = 0

    tasks_list.append(task_info)

# 4. CSV'ye yaz
df = pd.DataFrame(tasks_list)
df.to_csv(output_path, index=False)

print(f"\n✅ CSV başarıyla oluşturuldu: {output_path}\n")
