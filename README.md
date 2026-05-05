# saas-vanilla

Reusable Flask-based SaaS foundation for spinning up new internal or customer-facing prototypes quickly.

## Included

- Login and logout
- Dashboard
- User management
- Roles and permissions
- System configuration for LLM models, attributes, and integrations
- Help center backed by markdown docs
- Release notes with manual generation
- Avatar upload and user menu

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Default admin account:

- Username: `admin`
- Password: `Changeme-123`

The app will prompt the admin to change the password after first login.

