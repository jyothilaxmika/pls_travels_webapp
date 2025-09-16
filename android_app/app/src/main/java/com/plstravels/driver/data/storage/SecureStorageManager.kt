package com.plstravels.driver.data.storage

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Secure storage manager using EncryptedSharedPreferences for sensitive data
 */
@Singleton
class SecureStorageManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    
    companion object {
        private const val PREFS_FILE_NAME = "pls_secure_prefs"
        
        // Keys for storing authentication data
        const val KEY_ACCESS_TOKEN = "access_token"
        const val KEY_REFRESH_TOKEN = "refresh_token"
        const val KEY_TOKEN_EXPIRES_AT = "token_expires_at"
        const val KEY_USER_ID = "user_id"
        const val KEY_USERNAME = "username"
        const val KEY_FULL_NAME = "full_name"
        const val KEY_PHONE = "phone"
        const val KEY_IS_LOGGED_IN = "is_logged_in"
        const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
        const val KEY_LAST_LOGIN_TIME = "last_login_time"
        const val KEY_BIOMETRIC_KEY_ALIAS = "biometric_key_alias"
    }
    
    private val masterKey: MasterKey by lazy {
        try {
            MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .setRequestStrongBoxBacked(true) // Use hardware security module if available
                .build()
        } catch (e: Exception) {
            Timber.w("Failed to create StrongBox-backed key, falling back to standard key: ${e.message}")
            // Fallback to standard key if StrongBox is not available
            MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
        }
    }
    
    private val encryptedPrefs: SharedPreferences by lazy {
        try {
            EncryptedSharedPreferences.create(
                context,
                PREFS_FILE_NAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (e: Exception) {
            Timber.e(e, "Failed to create encrypted preferences")
            throw SecurityException("Failed to initialize secure storage", e)
        }
    }
    
    /**
     * Save encrypted string value
     */
    suspend fun saveString(key: String, value: String?) = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.edit().apply {
                if (value != null) {
                    putString(key, value)
                } else {
                    remove(key)
                }
                apply()
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to save string for key: $key")
            throw SecurityException("Failed to save secure data", e)
        }
    }
    
    /**
     * Get encrypted string value
     */
    suspend fun getString(key: String, defaultValue: String? = null): String? = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.getString(key, defaultValue)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get string for key: $key")
            null
        }
    }
    
    /**
     * Save encrypted integer value
     */
    suspend fun saveInt(key: String, value: Int) = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.edit().putInt(key, value).apply()
        } catch (e: Exception) {
            Timber.e(e, "Failed to save int for key: $key")
            throw SecurityException("Failed to save secure data", e)
        }
    }
    
    /**
     * Get encrypted integer value
     */
    suspend fun getInt(key: String, defaultValue: Int = 0): Int = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.getInt(key, defaultValue)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get int for key: $key")
            defaultValue
        }
    }
    
    /**
     * Save encrypted long value
     */
    suspend fun saveLong(key: String, value: Long) = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.edit().putLong(key, value).apply()
        } catch (e: Exception) {
            Timber.e(e, "Failed to save long for key: $key")
            throw SecurityException("Failed to save secure data", e)
        }
    }
    
    /**
     * Get encrypted long value
     */
    suspend fun getLong(key: String, defaultValue: Long = 0L): Long = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.getLong(key, defaultValue)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get long for key: $key")
            defaultValue
        }
    }
    
    /**
     * Save encrypted boolean value
     */
    suspend fun saveBoolean(key: String, value: Boolean) = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.edit().putBoolean(key, value).apply()
        } catch (e: Exception) {
            Timber.e(e, "Failed to save boolean for key: $key")
            throw SecurityException("Failed to save secure data", e)
        }
    }
    
    /**
     * Get encrypted boolean value
     */
    suspend fun getBoolean(key: String, defaultValue: Boolean = false): Boolean = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.getBoolean(key, defaultValue)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get boolean for key: $key")
            defaultValue
        }
    }
    
    /**
     * Remove specific key
     */
    suspend fun remove(key: String) = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.edit().remove(key).apply()
        } catch (e: Exception) {
            Timber.e(e, "Failed to remove key: $key")
        }
    }
    
    /**
     * Clear all secure data
     */
    suspend fun clearAll() = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.edit().clear().apply()
            Timber.i("Cleared all secure storage data")
        } catch (e: Exception) {
            Timber.e(e, "Failed to clear secure storage")
        }
    }
    
    /**
     * Check if key exists
     */
    suspend fun contains(key: String): Boolean = withContext(Dispatchers.IO) {
        try {
            encryptedPrefs.contains(key)
        } catch (e: Exception) {
            Timber.e(e, "Failed to check if key exists: $key")
            false
        }
    }
    
    /**
     * Check if storage is healthy and accessible
     */
    suspend fun isStorageHealthy(): Boolean = withContext(Dispatchers.IO) {
        try {
            // Test write and read operation
            val testKey = "health_check_${System.currentTimeMillis()}"
            val testValue = "test_value"
            
            encryptedPrefs.edit().putString(testKey, testValue).apply()
            val retrievedValue = encryptedPrefs.getString(testKey, null)
            encryptedPrefs.edit().remove(testKey).apply()
            
            retrievedValue == testValue
        } catch (e: Exception) {
            Timber.e(e, "Storage health check failed")
            false
        }
    }
}