# Railway Production Deployment Guide

## Required Environment Variables

Set these in your Railway project settings:

### Core Django Settings
```bash
ENV=production
DEBUG=False
SECRET_KEY=<generate-a-secure-random-key>
DATABASE_URL=<automatically-set-by-railway-postgres>
```

### Application Settings
```bash
ALLOWED_HOSTS=tokenizedinvoicediscounting-production.up.railway.app
```

### KRA eTIMS API (Optional)
```bash
KRA_API_BASE_URL=https://sbx.kra.go.ke
KRA_CONSUMER_KEY=<your-kra-consumer-key>
KRA_CONSUMER_SECRET=<your-kra-consumer-secret>
KRA_API_TIMEOUT=30
KRA_VERIFICATION_ENABLED=True
```

## Deployment Checklist

- [ ] All environment variables set in Railway
- [ ] DEBUG=False in production
- [ ] SECRET_KEY is different from dev
- [ ] Database migrations run automatically (via nixpacks.toml)
- [ ] Static files collected
- [ ] CORS origins configured correctly

## Automatic Migration

The `nixpacks.toml` file ensures migrations run automatically on each deployment:
```
python manage.py migrate --noinput && gunicorn ...
```

## Manual Migration (if needed)

If you need to run migrations manually:
```bash
railway run python manage.py migrate
```

## Verify Deployment

After deployment, check:
1. `GET /api/` - Should return JSON, not HTML
2. `POST /api/invoices/` - Should accept invoices without legacy fields
3. `GET /api/users/` - Should only return current user (not all users)
4. Errors should return JSON, not Django debug pages

## Troubleshooting

### Issue: "kra_verified violates not-null constraint"
**Solution**: Migration 0004 hasn't run. Check Railway logs or run manually:
```bash
railway run python manage.py migrate discounting 0004
```

### Issue: Django debug pages showing in production
**Solution**: Ensure `DEBUG=False` is set in Railway environment variables

### Issue: All users exposed via GET /api/users/
**Solution**: Latest code restricts to current user only. Redeploy to apply.
