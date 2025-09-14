package com.plstravels.driver.data.models

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import java.util.UUID

/**
 * Base interface for offline commands that can be queued and executed later
 */
interface OfflineCommand {
    val type: CommandType
    val payload: String
    val timestamp: Long
    val retryCount: Int
    
    suspend fun execute(apiService: com.plstravels.driver.data.network.ApiService): CommandResult
}

/**
 * Types of commands that can be queued for offline execution
 */
enum class CommandType {
    START_DUTY,
    END_DUTY,
    UPDATE_LOCATION,
    UPLOAD_PHOTO,
    UPDATE_FCM_TOKEN,
    ACCEPT_DUTY_ASSIGNMENT
}

/**
 * Result of command execution
 */
sealed class CommandResult {
    data class Success(val serverEntityId: String? = null, val reconciliationData: Map<String, Any>? = null) : CommandResult()
    data class Failure(val error: String, val shouldRetry: Boolean = true) : CommandResult()
    data class Conflict(val serverData: String) : CommandResult()
}

/**
 * Room entity for storing offline commands
 */
@Entity(tableName = "command_queue")
data class QueuedCommand(
    @PrimaryKey
    val id: String = UUID.randomUUID().toString(),
    val type: CommandType,
    val payload: String,
    val timestamp: Long = System.currentTimeMillis(),
    val retryCount: Int = 0,
    val maxRetries: Int = 3,
    val isExecuting: Boolean = false,
    val lastError: String? = null,
    val idempotencyKey: String? = null,
    val tempEntityId: String? = null, // Temporary ID assigned locally
    val serverEntityId: String? = null, // Server ID received after sync
    val isReconciled: Boolean = false // Whether temp/server ID mapping is complete
)

/**
 * Start Duty Command
 */
data class StartDutyCommand(
    val vehicleId: Int,
    val startOdometer: Int?,
    val notes: String?,
    val tempDutyId: String? = UUID.randomUUID().toString(), // Temporary local ID
    val idempotencyKey: String = UUID.randomUUID().toString(),
    override val timestamp: Long = System.currentTimeMillis(),
    override val retryCount: Int = 0
) : OfflineCommand {
    override val type = CommandType.START_DUTY
    override val payload: String get() = Gson().toJson(this)
    
    override suspend fun execute(apiService: com.plstravels.driver.data.network.ApiService): CommandResult {
        return try {
            val request = StartDutyRequest(
                vehicleId = vehicleId,
                startOdometer = startOdometer,
                notes = notes,
                idempotencyKey = idempotencyKey
            )
            val response = apiService.startDuty(request)
            if (response.isSuccessful) {
                val responseBody = response.body()
                val serverDutyId = responseBody?.dutyId?.toString()
                CommandResult.Success(
                    serverEntityId = serverDutyId,
                    reconciliationData = mapOf(
                        "tempDutyId" to tempDutyId,
                        "serverDutyId" to serverDutyId
                    )
                )
            } else {
                CommandResult.Failure("Server error: ${response.code()}")
            }
        } catch (e: Exception) {
            CommandResult.Failure("Network error: ${e.message}")
        }
    }
}

/**
 * End Duty Command
 */
data class EndDutyCommand(
    val dutyId: Int,
    val endOdometer: Int?,
    val notes: String?,
    val idempotencyKey: String = UUID.randomUUID().toString(),
    override val timestamp: Long = System.currentTimeMillis(),
    override val retryCount: Int = 0
) : OfflineCommand {
    override val type = CommandType.END_DUTY
    override val payload: String get() = Gson().toJson(this)
    
    override suspend fun execute(apiService: com.plstravels.driver.data.network.ApiService): CommandResult {
        return try {
            val request = EndDutyRequest(
                dutyId = dutyId,
                endOdometer = endOdometer,
                notes = notes
            )
            val response = apiService.endDuty(request)
            if (response.isSuccessful) {
                CommandResult.Success()
            } else {
                CommandResult.Failure("Server error: ${response.code()}")
            }
        } catch (e: Exception) {
            CommandResult.Failure("Network error: ${e.message}")
        }
    }
}

/**
 * Location Update Command
 */
data class LocationUpdateCommand(
    val locations: List<LocationUpdate>,
    override val timestamp: Long = System.currentTimeMillis(),
    override val retryCount: Int = 0
) : OfflineCommand {
    override val type = CommandType.UPDATE_LOCATION
    override val payload: String get() = Gson().toJson(this)
    
    override suspend fun execute(apiService: com.plstravels.driver.data.network.ApiService): CommandResult {
        return try {
            val response = apiService.uploadLocation(locations)
            if (response.isSuccessful) {
                CommandResult.Success()
            } else {
                CommandResult.Failure("Server error: ${response.code()}")
            }
        } catch (e: Exception) {
            CommandResult.Failure("Network error: ${e.message}")
        }
    }
}

/**
 * FCM Token Update Command
 */
data class FCMTokenUpdateCommand(
    val fcmToken: String,
    val deviceId: String,
    val appVersion: String,
    override val timestamp: Long = System.currentTimeMillis(),
    override val retryCount: Int = 0
) : OfflineCommand {
    override val type = CommandType.UPDATE_FCM_TOKEN
    override val payload: String get() = Gson().toJson(this)
    
    override suspend fun execute(apiService: com.plstravels.driver.data.network.ApiService): CommandResult {
        return try {
            val request = FCMTokenRequest(
                fcmToken = fcmToken,
                deviceId = deviceId,
                platform = "android",
                appVersion = appVersion
            )
            val response = apiService.updateFCMToken(request)
            if (response.isSuccessful) {
                CommandResult.Success()
            } else {
                CommandResult.Failure("Server error: ${response.code()}", shouldRetry = false)
            }
        } catch (e: Exception) {
            CommandResult.Failure("Network error: ${e.message}")
        }
    }
}

/**
 * Accept Duty Assignment Command
 */
data class AcceptDutyCommand(
    val dutyId: Int,
    override val timestamp: Long = System.currentTimeMillis(),
    override val retryCount: Int = 0
) : OfflineCommand {
    override val type = CommandType.ACCEPT_DUTY_ASSIGNMENT
    override val payload: String get() = Gson().toJson(this)
    
    override suspend fun execute(apiService: com.plstravels.driver.data.network.ApiService): CommandResult {
        return try {
            val response = apiService.acceptDutyAssignment(dutyId)
            if (response.isSuccessful) {
                CommandResult.Success()
            } else {
                CommandResult.Failure("Server error: ${response.code()}")
            }
        } catch (e: Exception) {
            CommandResult.Failure("Network error: ${e.message}")
        }
    }
}