# Cuesync Production Readiness Backlog

**Current State:** Secure for development/testing with basic hardening applied

**Risk Level:** Medium (scheduled automation with API credentials, no user data)

---

## ✅ Completed Security Hardening

- [x] SSH restricted to single IP address (98.163.38.234/32)
- [x] All security updates applied
- [x] fail2ban installed (3 failed attempts = 1 hour ban)
- [x] Unused ports closed (only SSH-22 open)
- [x] SSH key authentication (no passwords)
- [x] Secrets in .env (gitignored)

---

## 🔒 Security

### High Priority (Before Real API Keys)

- [ ] **Secrets Management**
  - [ ] Move secrets from .env to AWS Secrets Manager or AWS Systems Manager Parameter Store
  - [ ] Use IAM role for server to access secrets (no credentials on disk)
  - [ ] Rotate API keys every 90 days
  - [ ] Document secret rotation procedure

- [ ] **Automated Security Updates**
  - [ ] Enable unattended-upgrades for security patches
  - [ ] Configure auto-reboot for kernel updates (off-hours)
  - [ ] Set up email notifications for pending updates

- [ ] **Backup SSH Access**
  - [ ] Add backup SSH key (in case primary is lost)
  - [ ] Document IP whitelist update procedure (if IP changes)
  - [ ] Test recovery from locked-out scenario

- [ ] **Server Hardening**
  - [ ] Disable root login via SSH (edit /etc/ssh/sshd_config)
  - [ ] Enable UFW firewall (redundant with Lightsail, but defense in depth)
  - [ ] Disable password authentication completely
  - [ ] Set up automatic security scan (lynis or similar)

### Medium Priority

- [ ] **Audit Logging**
  - [ ] Enable CloudWatch logging for cron job output
  - [ ] Log all SSH access attempts
  - [ ] Set up log rotation for application logs
  - [ ] Monitor disk space usage (logs can fill disk)

- [ ] **API Key Rotation**
  - [ ] Create script to test if API keys still work
  - [ ] Document Upwork API key rotation process
  - [ ] Set calendar reminder to rotate keys quarterly

### Low Priority

- [ ] Consider switching to AWS SSM Session Manager (no SSH port needed)
- [ ] Set up AWS GuardDuty for threat detection
- [ ] Enable VPC for network isolation (requires EC2 instead of Lightsail)
- [ ] Consider private GitHub repo access via deploy keys instead of public repos

---

## 📊 Monitoring & Alerting

### High Priority

- [ ] **Health Checks**
  - [ ] Create dead man's switch (daily ping that maestro is alive)
  - [ ] Alert if morning-workflow doesn't run for 2 days
  - [ ] Alert if sync.sh fails repeatedly (git pull issues)
  - [ ] Monitor disk space (alert at 80% full)

- [ ] **Error Alerting**
  - [ ] Send email/SMS if cuesheet execution fails
  - [ ] Alert on failed git pull (credentials issue, network down)
  - [ ] Alert if cron jobs stop running (cron daemon crashed)

### Medium Priority

- [ ] **Performance Monitoring**
  - [ ] Track cuesheet execution time
  - [ ] Monitor memory usage (512 MB is limited)
  - [ ] Alert if sync takes >5 minutes (slow network)

- [ ] **Cost Monitoring**
  - [ ] Set AWS budget alert ($10/month threshold)
  - [ ] Monitor Lightsail data transfer (1TB/month included)

### Low Priority

- [ ] Set up CloudWatch dashboard for server metrics
- [ ] Create uptime monitoring (external service pinging server)
- [ ] Log API call counts (track Upwork API usage)

---

## 🔄 Reliability & Recovery

### High Priority

- [ ] **Backup Strategy**
  - [ ] Enable automated Lightsail snapshots (daily, keep 7 days)
  - [ ] Test restore from snapshot (dry run)
  - [ ] Document recovery procedure in README

- [ ] **Disaster Recovery**
  - [ ] Document complete rebuild procedure
  - [ ] Test deploying to fresh server from scratch
  - [ ] Keep copy of .env secrets in password manager (1Password, etc.)

- [ ] **Dependency Management**
  - [ ] Pin Python package versions in requirements.txt
  - [ ] Test maestro execution after updates
  - [ ] Document rollback procedure if deploy breaks things

### Medium Priority

- [ ] **High Availability**
  - [ ] Consider standby server (manual failover acceptable for this use case)
  - [ ] Document manual failover procedure
  - [ ] Test failover scenario

- [ ] **Data Integrity**
  - [ ] Verify logs are being written correctly
  - [ ] Check log archive process works
  - [ ] Ensure cron regeneration doesn't lose jobs

### Low Priority

- [ ] Set up staging environment (separate server)
- [ ] Blue/green deployment strategy
- [ ] Automated rollback on failure

---

## 🚀 Operational Excellence

### High Priority

- [ ] **Documentation**
  - [ ] Add troubleshooting guide to README
  - [ ] Document common error scenarios
  - [ ] Create runbook for emergency procedures

- [ ] **Testing**
  - [ ] Test cuesheet execution manually before deploying
  - [ ] Verify schedule changes in cron after deploy
  - [ ] Test hooks commands regularly

### Medium Priority

- [ ] **Deployment Process**
  - [ ] Add pre-deploy validation (lint schedule.yaml)
  - [ ] Add deploy confirmation prompt for production
  - [ ] Create deploy checklist

- [ ] **Configuration Management**
  - [ ] Validate schedule.yaml syntax before commit
  - [ ] Add comments to schedule.yaml for cron syntax
  - [ ] Version control for .env changes (without committing secrets)

### Low Priority

- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Automated testing for cuesheets
- [ ] Deploy previews for schedule changes

---

## 📈 Future Enhancements

### Features

- [ ] Web UI to view cron status and logs
- [ ] Slack integration for notifications
- [ ] Manual trigger endpoint (run cuesheet on demand)
- [ ] Multi-environment support (dev/staging/prod)

### Infrastructure

- [ ] Auto-scaling (if load increases significantly)
- [ ] Move to EC2 with auto-recovery
- [ ] Container-based deployment (Docker)
- [ ] Kubernetes deployment (overkill for current needs)

---

## 🎯 Minimum Production Checklist

Before going to production with real API keys:

1. ✅ SSH restricted to your IP
2. ✅ Security updates applied
3. ✅ fail2ban installed
4. ⬜ Secrets moved to AWS Secrets Manager
5. ⬜ Automated security updates enabled
6. ⬜ Lightsail snapshots enabled (daily)
7. ⬜ Dead man's switch alerting configured
8. ⬜ .env backup stored in password manager
9. ⬜ Disaster recovery procedure documented and tested
10. ⬜ Error alerting configured (email/SMS)

---

## Risk Assessment

**Current Risk Level:** ✅ **ACCEPTABLE FOR TESTING**

**For Production:** Complete minimum checklist above

**Threat Model:**
- Primary risk: Compromised API keys → Financial loss (Upwork access)
- Secondary risk: Server compromise → Crypto mining, spam sending
- Tertiary risk: Data loss → Lost execution history (low impact)

**Mitigation Strategy:**
- Secrets in AWS Secrets Manager (not on disk)
- Automated backups (snapshots)
- Rate limiting on API calls (prevent runaway costs)
- Budget alerts ($10/month threshold)

**Acceptable Risk:**
- Manual deployment (low frequency, acceptable)
- Single server (downtime acceptable for this use case)
- No encryption at rest (no sensitive user data)

---

**Last Updated:** 2026-01-18
**Review Frequency:** Quarterly or before adding real API credentials
