package com.plstravels.driver.data.local

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Secure token storage using Android's EncryptedSharedPreferences
 */
@Singleton
class TokenManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        private const val PREFS_NAME = "pls_driver_tokens"
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USERNAME = "username"
        private const val KEY_ROLE = "role"
        private const val KEY_TOKEN_EXPIRES_AT = "token_expires_at"
    }
    
    private val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
    
    private val encryptedPrefs = EncryptedSharedPreferences.create(
        PREFS_NAME,
        masterKeyAlias,
        context,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    private val _isLoggedIn = MutableStateFlow(hasValidTokens())
    val isLoggedIn: Flow<Boolean> = _isLoggedIn.asStateFlow()
    
    suspend fun saveTokens(
        accessToken: String,
        refreshToken: String,
        userId: Int,
        username: String,
        role: String,
        expiresIn: Int
    ) {
        val expiresAt = System.currentTimeMillis() + (expiresIn * 1000L)
        
        encryptedPrefs.edit().apply {
            putString(KEY_ACCESS_TOKEN, accessToken)
            putString(KEY_REFRESH_TOKEN, refreshToken)
            putInt(KEY_USER_ID, userId)
            putString(KEY_USERNAME, username)
            putString(KEY_ROLE, role)
            putLong(KEY_TOKEN_EXPIRES_AT, expiresAt)
            apply()
        }
        
        _isLoggedIn.value = true
    }
    
    suspend fun getAccessToken(): String? {
        val token = encryptedPrefs.getString(KEY_ACCESS_TOKEN, null)
        val expiresAt = encryptedPrefs.getLong(KEY_TOKEN_EXPIRES_AT, 0L)
        
        // Check if token is expired (with 5 minute buffer)
        if (token != null && System.currentTimeMillis() > (expiresAt - 5 * 60 * 1000)) {
            return null // Token is expired or about to expire
        }
        
        return token
    }
    
    suspend fun getRefreshToken(): String? {
        return encryptedPrefs.getString(KEY_REFRESH_TOKEN, null)
    }
    
    suspend fun getCurrentUserId(): Int {
        return encryptedPrefs.getInt(KEY_USER_ID, -1)
    }
    
    suspend fun getCurrentUsername(): String? {
        return encryptedPrefs.getString(KEY_USERNAME, null)
    }
    
    suspend fun getCurrentUserRole(): String? {
        return encryptedPrefs.getString(KEY_ROLE, null)
    }
    
    suspend fun updateAccessToken(accessToken: String, expiresIn: Int) {
        val expiresAt = System.currentTimeMillis() + (expiresIn * 1000L)
        
        encryptedPrefs.edit().apply {
            putString(KEY_ACCESS_TOKEN, accessToken)
            putLong(KEY_TOKEN_EXPIRES_AT, expiresAt)
            apply()
        }
    }
    
    suspend fun clearTokens() {
        encryptedPrefs.edit().clear().apply()
        _isLoggedIn.value = false
    }
    
    private fun hasValidTokens(): Boolean {
        val accessToken = encryptedPrefs.getString(KEY_ACCESS_TOKEN, null)
        val refreshToken = encryptedPrefs.getString(KEY_REFRESH_TOKEN, null)
        val expiresAt = encryptedPrefs.getLong(KEY_TOKEN_EXPIRES_AT, 0L)
        
        return !accessToken.isNullOrEmpty() && 
               !refreshToken.isNullOrEmpty() && 
               System.currentTimeMillis() < expiresAt
    }
}