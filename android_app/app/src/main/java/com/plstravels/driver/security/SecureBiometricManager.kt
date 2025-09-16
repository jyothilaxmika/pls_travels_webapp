package com.plstravels.driver.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import timber.log.Timber
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Secure biometric authentication manager using Android Keystore
 */
@Singleton
class SecureBiometricManager @Inject constructor(
    private val context: Context
) {
    
    companion object {
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS_PREFIX = "pls_biometric_key_"
        private const val TRANSFORMATION = KeyProperties.KEY_ALGORITHM_AES + "/" +
                KeyProperties.BLOCK_MODE_CBC + "/" +
                KeyProperties.ENCRYPTION_PADDING_PKCS7
    }
    
    private var keyStore: KeyStore? = null
    
    init {
        initializeKeyStore()
    }
    
    private fun initializeKeyStore() {
        try {
            keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply {
                load(null)
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to initialize Android Keystore")
        }
    }
    
    /**
     * Check biometric availability with detailed status
     */
    fun getBiometricAvailability(): BiometricAvailability {
        val biometricManager = BiometricManager.from(context)
        return when (biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)) {
            BiometricManager.BIOMETRIC_SUCCESS -> BiometricAvailability.AVAILABLE
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> BiometricAvailability.NO_HARDWARE
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> BiometricAvailability.HARDWARE_UNAVAILABLE
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> BiometricAvailability.NONE_ENROLLED
            BiometricManager.BIOMETRIC_ERROR_SECURITY_UPDATE_REQUIRED -> BiometricAvailability.SECURITY_UPDATE_REQUIRED
            BiometricManager.BIOMETRIC_ERROR_UNSUPPORTED -> BiometricAvailability.UNSUPPORTED
            BiometricManager.BIOMETRIC_STATUS_UNKNOWN -> BiometricAvailability.UNKNOWN
            else -> BiometricAvailability.UNKNOWN
        }
    }
    
    /**
     * Generate a new biometric key in Android Keystore
     */
    fun generateBiometricKey(userId: Int): String? {
        return try {\n            val keyAlias = \"${KEY_ALIAS_PREFIX}${userId}\"\n            \n            // Delete existing key if any\n            deleteKey(keyAlias)\n            \n            val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)\n            val keyGenParameterSpec = KeyGenParameterSpec.Builder(\n                keyAlias,\n                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT\n            )\n                .setBlockModes(KeyProperties.BLOCK_MODE_CBC)\n                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_PKCS7)\n                .setUserAuthenticationRequired(true)\n                .setUserAuthenticationParameters(\n                    30, // Authentication valid for 30 seconds\n                    KeyProperties.AUTH_BIOMETRIC_STRONG\n                )\n                .setInvalidatedByBiometricEnrollment(true) // Invalidate if new biometric is enrolled\n                .build()\n                \n            keyGenerator.init(keyGenParameterSpec)\n            keyGenerator.generateKey()\n            \n            Timber.i(\"Biometric key generated successfully for user: $userId\")\n            keyAlias\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to generate biometric key\")\n            null\n        }\n    }\n    \n    /**\n     * Get cipher for biometric authentication\n     */\n    private fun getCipher(keyAlias: String, mode: Int): Cipher? {\n        return try {\n            val key = getKey(keyAlias) ?: return null\n            val cipher = Cipher.getInstance(TRANSFORMATION)\n            cipher.init(mode, key)\n            cipher\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to get cipher for key: $keyAlias\")\n            null\n        }\n    }\n    \n    /**\n     * Get secret key from keystore\n     */\n    private fun getKey(keyAlias: String): SecretKey? {\n        return try {\n            keyStore?.getKey(keyAlias, null) as? SecretKey\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to get key: $keyAlias\")\n            null\n        }\n    }\n    \n    /**\n     * Delete biometric key from keystore\n     */\n    fun deleteKey(keyAlias: String): Boolean {\n        return try {\n            keyStore?.deleteEntry(keyAlias)\n            Timber.i(\"Deleted biometric key: $keyAlias\")\n            true\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to delete key: $keyAlias\")\n            false\n        }\n    }\n    \n    /**\n     * Check if biometric key exists for user\n     */\n    fun hasBiometricKey(keyAlias: String): Boolean {\n        return try {\n            keyStore?.containsAlias(keyAlias) == true\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to check key existence: $keyAlias\")\n            false\n        }\n    }\n    \n    /**\n     * Perform secure biometric authentication\n     */\n    fun authenticateWithBiometric(\n        activity: FragmentActivity,\n        keyAlias: String,\n        title: String = \"Secure Authentication\",\n        subtitle: String = \"Use biometric to unlock your session\",\n        description: String = \"Authenticate using your fingerprint or face\",\n        onSuccess: (ByteArray?) -> Unit,\n        onError: (String) -> Unit,\n        onFailed: () -> Unit\n    ) {\n        val availability = getBiometricAvailability()\n        if (availability != BiometricAvailability.AVAILABLE) {\n            onError(getAvailabilityMessage(availability))\n            return\n        }\n        \n        if (!hasBiometricKey(keyAlias)) {\n            onError(\"Biometric key not found. Please set up biometric authentication again.\")\n            return\n        }\n        \n        val cipher = getCipher(keyAlias, Cipher.ENCRYPT_MODE)\n        if (cipher == null) {\n            onError(\"Failed to initialize biometric authentication. Please try again.\")\n            return\n        }\n        \n        val executor = ContextCompat.getMainExecutor(context)\n        val biometricPrompt = BiometricPrompt(activity, executor, object : BiometricPrompt.AuthenticationCallback() {\n            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {\n                super.onAuthenticationError(errorCode, errString)\n                Timber.e(\"Biometric authentication error: $errorCode - $errString\")\n                \n                when (errorCode) {\n                    BiometricPrompt.ERROR_USER_CANCELED,\n                    BiometricPrompt.ERROR_NEGATIVE_BUTTON -> {\n                        onFailed()\n                    }\n                    BiometricPrompt.ERROR_LOCKOUT,\n                    BiometricPrompt.ERROR_LOCKOUT_PERMANENT -> {\n                        onError(\"Biometric authentication is temporarily locked. Please try again later.\")\n                    }\n                    BiometricPrompt.ERROR_NO_BIOMETRICS -> {\n                        onError(\"No biometric credentials enrolled. Please set up biometric authentication in device settings.\")\n                    }\n                    else -> {\n                        onError(\"Authentication error: $errString\")\n                    }\n                }\n            }\n            \n            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {\n                super.onAuthenticationSucceeded(result)\n                Timber.i(\"Biometric authentication succeeded\")\n                \n                try {\n                    // Use the authenticated cipher to encrypt a test payload\n                    val authenticatedCipher = result.cryptoObject?.cipher\n                    if (authenticatedCipher != null) {\n                        // Encrypt a timestamp as proof of authentication\n                        val timestamp = System.currentTimeMillis().toString()\n                        val encryptedData = authenticatedCipher.doFinal(timestamp.toByteArray())\n                        onSuccess(encryptedData)\n                    } else {\n                        onSuccess(null)\n                    }\n                } catch (e: Exception) {\n                    Timber.e(e, \"Failed to process biometric authentication result\")\n                    onError(\"Authentication processing failed\")\n                }\n            }\n            \n            override fun onAuthenticationFailed() {\n                super.onAuthenticationFailed()\n                Timber.w(\"Biometric authentication failed\")\n                onFailed()\n            }\n        })\n        \n        val promptInfo = BiometricPrompt.PromptInfo.Builder()\n            .setTitle(title)\n            .setSubtitle(subtitle)\n            .setDescription(description)\n            .setNegativeButtonText(\"Use Phone Authentication\")\n            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)\n            .setConfirmationRequired(true) // Require explicit confirmation\n            .build()\n            \n        // Create crypto object with the cipher\n        val cryptoObject = BiometricPrompt.CryptoObject(cipher)\n        biometricPrompt.authenticate(promptInfo, cryptoObject)\n    }\n    \n    /**\n     * Setup biometric authentication for user\n     */\n    fun setupBiometricAuth(\n        activity: FragmentActivity,\n        userId: Int,\n        onSuccess: (String) -> Unit,\n        onError: (String) -> Unit\n    ) {\n        val availability = getBiometricAvailability()\n        if (availability != BiometricAvailability.AVAILABLE) {\n            onError(getAvailabilityMessage(availability))\n            return\n        }\n        \n        // Generate new key for this user\n        val keyAlias = generateBiometricKey(userId)\n        if (keyAlias == null) {\n            onError(\"Failed to generate secure key for biometric authentication\")\n            return\n        }\n        \n        // Test the newly generated key with a biometric prompt\n        authenticateWithBiometric(\n            activity = activity,\n            keyAlias = keyAlias,\n            title = \"Setup Biometric Authentication\",\n            subtitle = \"Verify your biometric to complete setup\",\n            description = \"This will enable secure biometric login for your account\",\n            onSuccess = { _ ->\n                onSuccess(keyAlias)\n            },\n            onError = { error ->\n                // Clean up the key if setup failed\n                deleteKey(keyAlias)\n                onError(error)\n            },\n            onFailed = {\n                // Clean up the key if setup failed\n                deleteKey(keyAlias)\n                onError(\"Biometric setup was cancelled\")\n            }\n        )\n    }\n    \n    /**\n     * Disable biometric authentication for user\n     */\n    fun disableBiometricAuth(keyAlias: String): Boolean {\n        return deleteKey(keyAlias)\n    }\n    \n    private fun getAvailabilityMessage(availability: BiometricAvailability): String {\n        return when (availability) {\n            BiometricAvailability.NO_HARDWARE -> \"Biometric hardware not available on this device\"\n            BiometricAvailability.HARDWARE_UNAVAILABLE -> \"Biometric hardware is currently unavailable\"\n            BiometricAvailability.NONE_ENROLLED -> \"No biometric credentials enrolled. Please set up fingerprint or face unlock in device settings\"\n            BiometricAvailability.SECURITY_UPDATE_REQUIRED -> \"Security update required for biometric authentication\"\n            BiometricAvailability.UNSUPPORTED -> \"Biometric authentication not supported on this device\"\n            BiometricAvailability.UNKNOWN -> \"Biometric authentication status unknown\"\n            BiometricAvailability.AVAILABLE -> \"Biometric authentication available\"\n        }\n    }\n    \n    enum class BiometricAvailability {\n        AVAILABLE,\n        NO_HARDWARE,\n        HARDWARE_UNAVAILABLE,\n        NONE_ENROLLED,\n        SECURITY_UPDATE_REQUIRED,\n        UNSUPPORTED,\n        UNKNOWN\n    }\n}