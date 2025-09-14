# Keystore Security Guide

## ⚠️ SECURITY WARNING
**NEVER commit keystore files or passwords to version control!**

## Files in this directory:
- `staging.keystore` - Staging environment keystore (included for development)
- `release.keystore` - Production keystore (**NEVER commit this!**)
- `keystore-config.properties` - Configuration template (**NEVER commit with real passwords!**)

## Production Setup:

### 1. Generate Production Keystore
```bash
keytool -genkey -v -keystore release.keystore -alias plsdriver -keyalg RSA -keysize 2048 -validity 25000
```

### 2. Secure Storage
- Store production keystore in secure location (not in source code)
- Use CI/CD environment variables for passwords
- Keep backup copies in secure vault

### 3. Environment Variables for CI/CD
```bash
export KEYSTORE_PASSWORD="your-secure-password"
export KEY_PASSWORD="your-secure-key-password"  
export KEY_ALIAS="plsdriver"
```

### 4. Security Best Practices
- Use strong passwords (16+ characters)
- Different passwords for staging and production
- Rotate keystore passwords annually
- Never store passwords in plain text
- Use hardware security modules for enterprise deployments

### 5. Certificate Pinning Setup
Update the certificate pins in:
- `network_security_config.xml`
- `CertificatePinnerConfig.kt`

To get certificate pins:
```bash
openssl s_client -connect api.plstravels.com:443 | openssl x509 -pubkey -noout | openssl rsa -pubin -outform der | openssl dgst -sha256 -binary | openssl enc -base64
```

## Emergency Recovery
If keystore is lost:
1. Generate new keystore
2. Update certificate pins
3. Release new app version (users will need to reinstall)
4. Update all CI/CD configurations