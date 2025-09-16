package com.plstravels.driver.data.repository

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import com.plstravels.driver.data.api.AuthApi
import com.plstravels.driver.data.model.AuthResponse
import com.plstravels.driver.data.model.OtpSendResponse
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "auth_preferences")

/**
 * Repository for authentication and token management
 */
@Singleton
class AuthRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val authApi: AuthApi
) {

    private object PreferenceKeys {
        val ACCESS_TOKEN = stringPreferencesKey("access_token")
        val REFRESH_TOKEN = stringPreferencesKey("refresh_token")
        val TOKEN_EXPIRES_AT = longPreferencesKey("token_expires_at")
        val USER_ID = intPreferencesKey("user_id")
        val USERNAME = stringPreferencesKey("username")
        val FULL_NAME = stringPreferencesKey("full_name")
        val PHONE = stringPreferencesKey("phone")
        val IS_LOGGED_IN = booleanPreferencesKey("is_logged_in")
        val BIOMETRIC_ENABLED = booleanPreferencesKey("biometric_enabled")
        val LAST_LOGIN_TIME = longPreferencesKey("last_login_time")
    }

    private val dataStore = context.dataStore

    /**
     * Check if user is currently logged in
     */
    val isLoggedIn: Flow<Boolean> = dataStore.data.map { preferences ->
        preferences[PreferenceKeys.IS_LOGGED_IN] ?: false
    }

    /**
     * Get current access token
     */
    val accessToken: Flow<String?> = dataStore.data.map { preferences ->
        preferences[PreferenceKeys.ACCESS_TOKEN]
    }

    /**
     * Get current user info
     */
    val currentUser: Flow<UserInfo?> = dataStore.data.map { preferences ->
        val userId = preferences[PreferenceKeys.USER_ID]
        val username = preferences[PreferenceKeys.USERNAME]
        val fullName = preferences[PreferenceKeys.FULL_NAME]
        val phone = preferences[PreferenceKeys.PHONE]
        
        if (userId != null && username != null && fullName != null && phone != null) {
            UserInfo(userId, username, fullName, phone)
        } else {
            null
        }
    }

    /**
     * Send OTP to phone number
     */
    suspend fun sendOtp(phone: String): Result<OtpSendResponse> {
        return try {
            val response = authApi.sendOtp(phone)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                val errorMessage = response.errorBody()?.string() ?: "Failed to send OTP"
                Timber.e("Send OTP failed: $errorMessage")
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Timber.e(e, "Send OTP exception")
            Result.failure(e)
        }
    }

    /**
     * Verify OTP and login
     */
    suspend fun verifyOtp(
        phone: String, 
        otp: String, 
        deviceInfo: String? = null, 
        fcmToken: String? = null
    ): Result<AuthResponse> {
        return try {
            val response = authApi.verifyOtp(phone, otp, deviceInfo, fcmToken)
            if (response.isSuccessful && response.body() != null) {
                val authResponse = response.body()!!
                if (authResponse.success) {
                    // Save tokens and user info
                    saveAuthData(authResponse)
                }
                Result.success(authResponse)
            } else {
                val errorMessage = response.errorBody()?.string() ?: "Failed to verify OTP"
                Timber.e("Verify OTP failed: $errorMessage")
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Timber.e(e, "Verify OTP exception")
            Result.failure(e)
        }
    }

    /**
     * Refresh access token
     */
    suspend fun refreshToken(): Result<AuthResponse> {
        return try {
            val refreshToken = getRefreshToken()
            if (refreshToken == null) {
                return Result.failure(Exception("No refresh token available"))
            }

            val response = authApi.refreshToken(refreshToken)
            if (response.isSuccessful && response.body() != null) {
                val authResponse = response.body()!!
                if (authResponse.success) {
                    // Save new tokens
                    saveAuthData(authResponse)
                }
                Result.success(authResponse)
            } else {
                val errorMessage = response.errorBody()?.string() ?: "Failed to refresh token"
                Timber.e("Refresh token failed: $errorMessage")
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Timber.e(e, "Refresh token exception")
            Result.failure(e)
        }
    }

    /**
     * Logout user
     */
    suspend fun logout(): Result<Unit> {
        return try {
            // Call logout API
            authApi.logout()
            
            // Clear all stored data
            clearAuthData()
            
            Result.success(Unit)
        } catch (e: Exception) {
            Timber.e(e, "Logout exception")
            // Clear local data even if API call fails
            clearAuthData()
            Result.success(Unit)
        }
    }

    /**
     * Get current access token synchronously (for interceptors)
     */
    suspend fun getCurrentAccessToken(): String? {
        return try {
            val preferences = dataStore.data.map { it[PreferenceKeys.ACCESS_TOKEN] }
            preferences.collect { return it }
        } catch (e: Exception) {
            Timber.e(e, "Failed to get access token")
            null
        }
    }

    private suspend fun getRefreshToken(): String? {
        return try {
            val preferences = dataStore.data.map { it[PreferenceKeys.REFRESH_TOKEN] }
            preferences.collect { return it }
        } catch (e: Exception) {
            Timber.e(e, "Failed to get refresh token")
            null
        }
    }

    private suspend fun saveAuthData(authResponse: AuthResponse) {
        dataStore.edit { preferences ->
            authResponse.accessToken?.let {
                preferences[PreferenceKeys.ACCESS_TOKEN] = it
            }
            authResponse.refreshToken?.let {
                preferences[PreferenceKeys.REFRESH_TOKEN] = it
            }
            authResponse.expiresIn?.let {
                preferences[PreferenceKeys.TOKEN_EXPIRES_AT] = System.currentTimeMillis() + (it * 1000)
            }
            authResponse.user?.let { user ->
                preferences[PreferenceKeys.USER_ID] = user.id
                preferences[PreferenceKeys.USERNAME] = user.username
                preferences[PreferenceKeys.FULL_NAME] = user.fullName
                preferences[PreferenceKeys.PHONE] = user.phone
            }
            preferences[PreferenceKeys.IS_LOGGED_IN] = true
            preferences[PreferenceKeys.LAST_LOGIN_TIME] = System.currentTimeMillis()
        }
    }

    private suspend fun clearAuthData() {
        dataStore.edit { preferences ->
            preferences.clear()
        }
    }

    /**
     * Enable/disable biometric authentication
     */
    suspend fun setBiometricEnabled(enabled: Boolean) {
        dataStore.edit { preferences ->
            preferences[PreferenceKeys.BIOMETRIC_ENABLED] = enabled
        }
    }

    /**
     * Check if biometric authentication is enabled
     */
    val isBiometricEnabled: Flow<Boolean> = dataStore.data.map { preferences ->
        preferences[PreferenceKeys.BIOMETRIC_ENABLED] ?: false
    }

    data class UserInfo(
        val id: Int,
        val username: String,
        val fullName: String,
        val phone: String
    )
}