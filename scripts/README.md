# Dummy / demo data scripts

For **local and Docker testing only**. Do not run against production.

---

## Comprehensive demo seed (recommended)

Creates everything needed to exercise most flows in one go:

| Item | Details |
|------|---------|
| **Users** | `9876500001` (admin), `9876500002` (student, paid for today), `9876500003` (extra) |
| **Duel** | Today’s date, **active**, ₹9 fee, 5 bilingual MCQs (if no duel exists for today) |
| **Registration** | Demo student marked **payment completed** + `payments` row |
| **PYQ** | “Demo PYQ Pack (seeded)” + 2 PYQ questions |
| **Referral** | Admin referred demo student + sample loyalty transaction |
| **Support / feedback** | Sample ticket + feedback row |
| **Admin message** | In-app message to demo student |

### Database migrations

**Docker:** The backend container entrypoint runs `alembic upgrade head` before Uvicorn/Celery starts. Rebuild/restart so it runs against your Postgres volume:

```bash
docker compose up -d --build
```

**If you still see `UndefinedColumn` inside Docker** (old image without entrypoint), run once:

```bash
docker exec veducation_backend python -m alembic upgrade head
```

**Local host Postgres** (when you use `python scripts/...` on the host, not `docker exec`):

```bash
cd backend
python -m alembic upgrade head
```

Host and Compose Postgres are **different databases** — migrate and seed each environment you use.

Migrations are **idempotent** where common drift occurs (tables/columns already created by an older app or partial run). If `alembic upgrade` still fails, paste the error — you may need a one-off `alembic stamp` after DBA review.

### Run (Docker)

```bash
docker exec veducation_backend python scripts/seed_comprehensive_demo.py
```

Optional: **remove today’s duel and all related rows** (attempts, registrations, questions, payments), then seed fresh:

```bash
docker exec veducation_backend python scripts/seed_comprehensive_demo.py --wipe-today-duel
```

> **Warning:** `--wipe-today-duel` deletes **whatever** duel is stored for **today’s calendar date**, not only rows created by this script.

### Run (local Python, same `DATABASE_URL` as API)

```bash
cd backend
python scripts/seed_comprehensive_demo.py
```

### After seeding — log in

1. **OTP:** With default dev SMS settings, the OTP is **logged** by the backend (`OTP for …: <code>`). Watch `docker compose logs -f backend` when you tap Send OTP.
2. **Student app:** Log in with `9876500002` → Home should show **today’s duel**; you can open instructions / test (already registered + paid).
3. **Admin app:** Open Flutter web at `http://localhost:<port>/#/admin/login` and log in with **`9876500001`** (same OTP-from-logs flow). Admin APIs require `is_admin=true` (this script sets it for `9876500001`).

---

## Legacy: insert dummy duel only

Creates **only** a duel + questions for today. Requires user `9347485455` to already exist (older flow).

```bash
docker exec veducation_backend python scripts/insert_dummy_data.py
```

## Legacy: cleanup today’s duel

Deletes today’s duel, questions, registrations, attempts, answers, and **payments** linked to those registrations.

```bash
docker exec -it veducation_backend python scripts/cleanup_dummy_data.py
```

Type `yes` when prompted.

---

## Testing checklist (post-seed)

- [ ] Student login (`9876500002`) + OTP from logs  
- [ ] Home: today’s duel visible; register flow or go straight to instructions if already paid  
- [ ] Admin login (`9876500001`) + `#/admin/login` on web  
- [ ] Admin → Users: list includes demo users; try message + active toggle  
- [ ] Admin stats / support / feedback endpoints (if wired in UI)  
