from datetime import datetime

def log_admin_action(admin_id, action, details=None):
    with open('admin_actions.log', 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] admin_id={admin_id} | {action} | {details or ''}\n") 