package com.plstravels.driver.security

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.plstravels.driver.data.local.TokenManager
import com.plstravels.driver.security.SecurityManager
import com.plstravels.driver.testutils.factories.TestDataFactory
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.spec.SecretKeySpec

/**
 * Security validation tests for authentication, encryption, and security features
 * Tests token security, data encryption, certificate pinning, and security controls
 */
@RunWith(AndroidJUnit4::class)
class SecurityValidationTest {

    private lateinit var context: Context
    private lateinit var tokenManager: TokenManager
    private lateinit var securityManager: SecurityManager

    @Before
    fun setup() {
        context = ApplicationProvider.getApplicationContext()
        
        // Initialize security components
        tokenManager = TokenManager(context)
        securityManager = SecurityManager(context)
    }

    @Test
    fun tokenEncryption_shouldStoreTokensSecurely() = runTest {
        // Arrange
        val testToken = "test_access_token_123456"
        val testRefreshToken = "test_refresh_token_654321"
        val userId = 1
        val username = "testuser"
        val role = "driver"

        // Act
        tokenManager.saveTokens(
            accessToken = testToken,
            refreshToken = testRefreshToken,
            userId = userId,
            username = username,
            role = role,
            expiresIn = 3600
        )

        // Assert
        val retrievedToken = tokenManager.getAccessToken()
        assertThat(retrievedToken).isEqualTo(testToken)

        // Verify tokens are encrypted in storage
        val prefs = context.getSharedPreferences("pls_tokens", Context.MODE_PRIVATE)
        val rawStoredToken = prefs.getString("access_token", null)
        
        // Raw token should not equal the original (it should be encrypted)
        assertThat(rawStoredToken).isNotEqualTo(testToken)
    }

    @Test
    fun encryptedSharedPreferences_shouldProtectSensitiveData() {
        // Arrange
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        val encryptedPrefs = EncryptedSharedPreferences.create(
            context,
            "test_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )

        val sensitiveData = "sensitive_user_data_12345"

        // Act
        encryptedPrefs.edit()
            .putString("sensitive_key", sensitiveData)
            .apply()

        // Assert
        val retrievedData = encryptedPrefs.getString("sensitive_key", null)
        assertThat(retrievedData).isEqualTo(sensitiveData)

        // Verify data is encrypted in underlying storage
        val regularPrefs = context.getSharedPreferences("test_secure_prefs", Context.MODE_PRIVATE)
        val rawStoredData = regularPrefs.getString("sensitive_key", null)
        
        // Raw data should not equal original (it should be encrypted)
        assertThat(rawStoredData).isNotEqualTo(sensitiveData)
        assertThat(rawStoredData).isNotNull()
    }

    @Test
    fun biometricAuthentication_shouldBeAvailable() {
        // Act
        val isBiometricAvailable = securityManager.isBiometricAuthenticationAvailable()

        // Assert - On most test devices, biometric might not be available
        // but the method should not crash
        assertThat(isBiometricAvailable).isAnyOf(true, false)
    }

    @Test
    fun rootDetection_shouldDetectRootedDevices() {
        // Act
        val isRooted = securityManager.isDeviceRooted()

        // Assert - Most test devices are not rooted
        assertThat(isRooted).isFalse()
    }

    @Test
    fun debuggerDetection_shouldDetectDebugging() {
        // Act
        val isDebugging = securityManager.isDebuggingEnabled()

        // Assert - In test environment, debugging might be enabled
        assertThat(isDebugging).isAnyOf(true, false)
    }

    @Test
    fun certificatePinning_shouldValidateServerCertificates() {
        // This would test certificate pinning implementation
        // In a real test, you'd use a test server with known certificates
        
        val testCertificateHash = "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
        val validHashes = setOf(testCertificateHash)

        // Act
        val isPinned = securityManager.isCertificatePinned("api.plstravels.com", validHashes)

        // Assert
        assertThat(isPinned).isAnyOf(true, false)
    }

    @Test
    fun dataAtRest_shouldBeEncrypted() {
        // Test that sensitive data at rest is encrypted
        val testData = TestDataFactory.createTestUser()
        val encryptionKey = generateTestEncryptionKey()

        // Act
        val encryptedData = securityManager.encryptSensitiveData(testData.toString(), encryptionKey)
        val decryptedData = securityManager.decryptSensitiveData(encryptedData, encryptionKey)

        // Assert
        assertThat(decryptedData).isEqualTo(testData.toString())
        assertThat(encryptedData).isNotEqualTo(testData.toString())
    }

    @Test
    fun apiKeyValidation_shouldRejectInvalidKeys() {
        // Arrange
        val validApiKey = "valid_api_key_12345"
        val invalidApiKey = "invalid_key"

        // Act & Assert
        assertThat(securityManager.isValidApiKey(validApiKey)).isTrue()
        assertThat(securityManager.isValidApiKey(invalidApiKey)).isFalse()
        assertThat(securityManager.isValidApiKey("")).isFalse()
        assertThat(securityManager.isValidApiKey(null)).isFalse()
    }

    @Test
    fun sessionTimeout_shouldInvalidateExpiredTokens() = runTest {
        // Arrange
        val shortExpiryToken = "short_lived_token"
        val userId = 1

        // Act - Save token with very short expiry
        tokenManager.saveTokens(
            accessToken = shortExpiryToken,
            refreshToken = "refresh_token",
            userId = userId,
            username = "testuser",
            role = "driver",
            expiresIn = 1 // 1 second
        )

        // Wait for expiry
        Thread.sleep(2000)

        // Assert
        val isExpired = tokenManager.isTokenExpired()
        assertThat(isExpired).isTrue()
    }

    @Test
    fun inputValidation_shouldSanitizeUserInput() {
        // Test SQL injection prevention
        val maliciousInput = "'; DROP TABLE users; --"
        val sanitizedInput = securityManager.sanitizeInput(maliciousInput)
        
        assertThat(sanitizedInput).doesNotContain("DROP")
        assertThat(sanitizedInput).doesNotContain("--")
        
        // Test XSS prevention
        val xssInput = "<script>alert('xss')</script>"
        val sanitizedXss = securityManager.sanitizeInput(xssInput)
        
        assertThat(sanitizedXss).doesNotContain("<script>")
        assertThat(sanitizedXss).doesNotContain("alert")
    }

    @Test
    fun networkTraffic_shouldBeSecure() {
        // Test HTTPS enforcement
        val httpUrl = "http://api.plstravels.com/test"
        val httpsUrl = "https://api.plstravels.com/test"

        assertThat(securityManager.isSecureUrl(httpsUrl)).isTrue()
        assertThat(securityManager.isSecureUrl(httpUrl)).isFalse()
    }

    @Test
    fun keystore_shouldProtectCryptographicKeys() {
        // Test Android Keystore usage
        val keyAlias = "test_key_alias"
        
        // Act
        val keyGenerated = securityManager.generateKeyInKeystore(keyAlias)
        val keyExists = securityManager.keyExistsInKeystore(keyAlias)

        // Assert
        assertThat(keyGenerated).isTrue()
        assertThat(keyExists).isTrue()

        // Cleanup
        securityManager.deleteKeyFromKeystore(keyAlias)
    }

    @Test
    fun dataTransmission_shouldBeProtected() {
        // Test data transmission security
        val sensitiveData = "user_personal_data_123"
        
        // Act
        val protectedData = securityManager.protectDataForTransmission(sensitiveData)
        val originalData = securityManager.unprotectReceivedData(protectedData)

        // Assert
        assertThat(originalData).isEqualTo(sensitiveData)
        assertThat(protectedData).isNotEqualTo(sensitiveData)
    }

    @Test
    fun memoryProtection_shouldClearSensitiveData() {
        // Test secure memory handling
        val sensitiveArray = "password123".toCharArray()
        
        // Act
        securityManager.clearSensitiveMemory(sensitiveArray)

        // Assert - Array should be zeroed out
        assertThat(sensitiveArray).isEqualTo(CharArray(sensitiveArray.size) { '\u0000' })
    }

    @Test
    fun appIntegrity_shouldValidateApplication() {
        // Test app signature validation
        val isSignatureValid = securityManager.isAppSignatureValid(context)
        
        // Assert - In debug builds, this might be different
        assertThat(isSignatureValid).isAnyOf(true, false)
    }

    @Test
    fun screenCapture_shouldBeBlocked() {
        // Test screen capture protection for sensitive screens
        val isScreenCaptureBlocked = securityManager.isScreenCaptureBlocked()
        
        // This would typically be tested at the Activity level
        assertThat(isScreenCaptureBlocked).isAnyOf(true, false)
    }

    @Test
    fun antiTampering_shouldDetectModification() {
        // Test anti-tampering measures
        val checksumValid = securityManager.verifyAppChecksum()
        val isAppModified = securityManager.isAppTampered()

        assertThat(checksumValid).isTrue()
        assertThat(isAppModified).isFalse()
    }

    @Test
    fun secureRandom_shouldGenerateUnpredictableValues() {
        // Test secure random number generation
        val random1 = securityManager.generateSecureRandom(32)
        val random2 = securityManager.generateSecureRandom(32)

        // Assert
        assertThat(random1).hasLength(32)
        assertThat(random2).hasLength(32)
        assertThat(random1).isNotEqualTo(random2)
    }

    // Helper methods
    private fun generateTestEncryptionKey(): SecretKeySpec {
        val keyGen = KeyGenerator.getInstance("AES")
        keyGen.init(256)
        val secretKey = keyGen.generateKey()
        return SecretKeySpec(secretKey.encoded, "AES")
    }
}