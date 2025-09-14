package com.plstravels.driver.data.repository

import com.plstravels.driver.data.local.CommandQueueDao
import com.plstravels.driver.data.local.DutyDao
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.network.ApiService
import com.google.gson.Gson
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.delay
import javax.inject.Inject
import javax.inject.Singleton
import android.util.Log

/**
 * Repository for managing offline command queue operations
 */
@Singleton
class CommandQueueRepository @Inject constructor(
    private val commandQueueDao: CommandQueueDao,
    private val apiService: ApiService,
    private val connectivityRepository: ConnectivityRepository,
    private val dutyDao: DutyDao
) {
    private val gson = Gson()
    
    companion object {
        private const val TAG = "CommandQueueRepository"
        private const val MAX_EXECUTION_TIME_MS = 30_000L // 30 seconds
        private const val CLEANUP_OLDER_THAN_DAYS = 7
    }
    
    /**
     * Queue a command for offline execution
     */
    suspend fun queueCommand(command: OfflineCommand, idempotencyKey: String? = null, tempEntityId: String? = null) {
        // Extract idempotency key from command if not provided
        val effectiveIdempotencyKey = idempotencyKey ?: extractIdempotencyKey(command)
        
        // Check for duplicate command by idempotency key
        effectiveIdempotencyKey?.let { key ->
            val existingCommand = commandQueueDao.getCommandByIdempotencyKey(key)
            if (existingCommand != null) {
                Log.d(TAG, "Command with idempotency key $key already exists, skipping")
                return
            }
        }
        
        val queuedCommand = QueuedCommand(
            type = command.type,
            payload = command.payload,
            timestamp = command.timestamp,
            retryCount = command.retryCount,
            idempotencyKey = effectiveIdempotencyKey,
            tempEntityId = tempEntityId,
            isReconciled = false
        )
        
        commandQueueDao.insertCommand(queuedCommand)
        Log.d(TAG, "Queued command: ${command.type} with idempotency key: $effectiveIdempotencyKey")
        
        // Attempt immediate execution if online
        if (connectivityRepository.isConnected.first()) {
            executeNextCommand()
        }
    }
    
    /**
     * Execute all pending commands
     */
    suspend fun executeAllCommands(): Int {
        var executedCount = 0
        
        while (true) {
            val executed = executeNextCommand()
            if (!executed) break
            executedCount++
            
            // Small delay between commands to avoid overwhelming the server
            delay(100)
        }
        
        return executedCount
    }
    
    /**
     * Execute the next pending command
     */
    suspend fun executeNextCommand(): Boolean {
        val pendingCommands = commandQueueDao.getPendingCommands()
        if (pendingCommands.isEmpty()) {
            return false
        }
        
        val command = pendingCommands.first()
        return executeCommand(command)
    }
    
    /**
     * Execute a specific command
     */
    private suspend fun executeCommand(queuedCommand: QueuedCommand): Boolean {
        if (!connectivityRepository.isConnected.first()) {
            Log.d(TAG, "No connectivity, skipping command execution")
            return false
        }
        
        // Mark command as executing
        commandQueueDao.updateCommandExecutionStatus(queuedCommand.id, true)
        
        try {
            val command = parseCommand(queuedCommand)
            if (command == null) {
                Log.e(TAG, "Failed to parse command: ${queuedCommand.type}")
                commandQueueDao.deleteCommand(queuedCommand.id)
                return false
            }
            
            Log.d(TAG, "Executing command: ${queuedCommand.type}")
            val result = command.execute(apiService)
            
            when (result) {
                is CommandResult.Success -> {
                    Log.d(TAG, "Command executed successfully: ${queuedCommand.type}")
                    
                    // Handle reconciliation if server entity ID is provided
                    result.serverEntityId?.let { serverId ->
                        commandQueueDao.updateCommandReconciliation(queuedCommand.id, serverId)
                        Log.d(TAG, "Updated reconciliation: ${queuedCommand.tempEntityId} -> $serverId")
                        
                        // Handle additional reconciliation data
                        result.reconciliationData?.let { data ->
                            handleReconciliationData(queuedCommand, data)
                        }
                    }
                    
                    // Only delete command if no reconciliation is needed or it's complete
                    if (result.serverEntityId == null || queuedCommand.tempEntityId == null) {
                        commandQueueDao.deleteCommand(queuedCommand.id)
                    }
                    return true
                }
                
                is CommandResult.Failure -> {
                    Log.w(TAG, "Command failed: ${queuedCommand.type}, error: ${result.error}")
                    
                    if (result.shouldRetry && queuedCommand.retryCount < queuedCommand.maxRetries) {
                        // Increment retry count and try again later
                        commandQueueDao.updateCommandRetry(
                            queuedCommand.id,
                            queuedCommand.retryCount + 1,
                            result.error
                        )
                        commandQueueDao.updateCommandExecutionStatus(queuedCommand.id, false)
                    } else {
                        // Max retries reached or shouldn't retry
                        Log.e(TAG, "Command failed permanently: ${queuedCommand.type}")
                        commandQueueDao.deleteCommand(queuedCommand.id)
                    }
                    return false
                }
                
                is CommandResult.Conflict -> {
                    Log.w(TAG, "Command conflict: ${queuedCommand.type}")
                    // Handle conflict resolution here
                    commandQueueDao.deleteCommand(queuedCommand.id)
                    return false
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception executing command: ${queuedCommand.type}", e)
            
            if (queuedCommand.retryCount < queuedCommand.maxRetries) {
                commandQueueDao.updateCommandRetry(
                    queuedCommand.id,
                    queuedCommand.retryCount + 1,
                    e.message
                )
                commandQueueDao.updateCommandExecutionStatus(queuedCommand.id, false)
            } else {
                commandQueueDao.deleteCommand(queuedCommand.id)
            }
            return false
        }
    }
    
    /**
     * Parse queued command back to executable command
     */
    private fun parseCommand(queuedCommand: QueuedCommand): OfflineCommand? {
        return try {
            when (queuedCommand.type) {
                CommandType.START_DUTY -> gson.fromJson(queuedCommand.payload, StartDutyCommand::class.java)
                CommandType.END_DUTY -> gson.fromJson(queuedCommand.payload, EndDutyCommand::class.java)
                CommandType.UPDATE_LOCATION -> gson.fromJson(queuedCommand.payload, LocationUpdateCommand::class.java)
                CommandType.UPLOAD_PHOTO -> {
                    // Photo uploads are handled by a separate service
                    // Return null to indicate this command type is not processed here
                    // Note: Photo uploads should be handled by PhotoUploadService
                    Log.d(TAG, "Photo upload command detected - delegating to PhotoUploadService")
                    null
                }
                CommandType.UPDATE_FCM_TOKEN -> gson.fromJson(queuedCommand.payload, FCMTokenUpdateCommand::class.java)
                CommandType.ACCEPT_DUTY_ASSIGNMENT -> gson.fromJson(queuedCommand.payload, AcceptDutyCommand::class.java)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse command payload", e)
            null
        }
    }
    
    /**
     * Get pending command count as flow for UI updates
     */
    fun getPendingCommandCount(): Flow<Int> = commandQueueDao.getPendingCommandCount()
    
    /**
     * Get all commands for debugging/monitoring
     */
    fun getAllCommands(): Flow<List<QueuedCommand>> = commandQueueDao.getAllCommandsFlow()
    
    /**
     * Clean up old and failed commands
     */
    suspend fun cleanup() {
        try {
            // Delete commands that have failed too many times
            commandQueueDao.deleteFailedCommands()
            
            // Delete commands older than specified days
            val cutoffTime = System.currentTimeMillis() - (CLEANUP_OLDER_THAN_DAYS * 24 * 60 * 60 * 1000L)
            commandQueueDao.deleteOldCommands(cutoffTime)
            
            // Reset any commands that have been executing for too long
            val executingCommands = commandQueueDao.getExecutingCommands()
            executingCommands.forEach { command ->
                if (System.currentTimeMillis() - command.timestamp > MAX_EXECUTION_TIME_MS) {
                    commandQueueDao.updateCommandExecutionStatus(command.id, false)
                    Log.w(TAG, "Reset stuck command: ${command.type}")
                }
            }
            
            Log.d(TAG, "Command queue cleanup completed")
        } catch (e: Exception) {
            Log.e(TAG, "Error during cleanup", e)
        }
    }
    
    /**
     * Clear all commands (for testing)
     */
    suspend fun clearAll() {
        commandQueueDao.clearAllCommands()
        Log.d(TAG, "All commands cleared")
    }
    
    /**
     * Extract idempotency key from command payload
     */
    private fun extractIdempotencyKey(command: OfflineCommand): String? {
        return try {
            when (command.type) {
                CommandType.START_DUTY -> {
                    val startCommand = gson.fromJson(command.payload, StartDutyCommand::class.java)
                    startCommand.idempotencyKey
                }
                CommandType.END_DUTY -> {
                    val endCommand = gson.fromJson(command.payload, EndDutyCommand::class.java)
                    endCommand.idempotencyKey
                }
                else -> null // Other commands can be extended as needed
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to extract idempotency key from command", e)
            null
        }
    }
    
    /**
     * Handle reconciliation data for ID mapping
     */
    private suspend fun handleReconciliationData(command: QueuedCommand, data: Map<String, Any>) {
        // Update local database entities with server IDs
        when (command.type) {
            CommandType.START_DUTY -> {
                val tempDutyId = data["tempDutyId"] as? String
                val serverDutyId = data["serverDutyId"] as? String
                if (tempDutyId != null && serverDutyId != null) {
                    Log.d(TAG, "Reconciling duty ID: $tempDutyId -> $serverDutyId")
                    
                    // Update local duty with server ID
                    try {
                        // Find local duty by temp ID hash (since we converted String to Int)
                        val tempIdHash = tempDutyId.hashCode()
                        val localDuty = dutyDao.getDutyById(tempIdHash)
                        if (localDuty != null) {
                            // Update duty with server ID and mark as synced
                            val updatedDuty = localDuty.copy(
                                id = serverDutyId.toIntOrNull() ?: localDuty.id,
                                syncStatus = "SYNCED"
                            )
                            dutyDao.updateDuty(updatedDuty)
                            Log.d(TAG, "Successfully updated duty: $tempIdHash -> $serverDutyId")
                        } else {
                            Log.w(TAG, "Local duty not found for temp ID: $tempDutyId")
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error updating local duty during reconciliation", e)
                    }
                    
                    // Mark command as reconciled
                    commandQueueDao.updateCommandReconciliation(command.id, serverDutyId)
                    
                    // Delete command after successful reconciliation
                    commandQueueDao.deleteCommand(command.id)
                }
            }
            // Add more reconciliation logic for other command types
            else -> {
                Log.d(TAG, "No specific reconciliation logic for ${command.type}")
            }
        }
    }
    
    /**
     * Get commands that need reconciliation
     */
    fun getCommandsNeedingReconciliation(): Flow<List<QueuedCommand>> {
        return commandQueueDao.getCommandsNeedingReconciliation()
    }
    
    /**
     * Reconcile command with server entity ID
     */
    suspend fun reconcileCommand(commandId: String, serverEntityId: String) {
        try {
            commandQueueDao.updateCommandReconciliation(commandId, serverEntityId)
            Log.d(TAG, "Command $commandId reconciled with server ID: $serverEntityId")
        } catch (e: Exception) {
            Log.e(TAG, "Error reconciling command $commandId", e)
        }
    }
    
    /**
     * Get command reconciliation status
     */
    suspend fun getReconciliationStatus(): ReconciliationStatus {
        val unreconciledCommands = commandQueueDao.getUnreconciledCommands()
        val totalCommands = commandQueueDao.getAllCommandsFlow().first().size
        
        return ReconciliationStatus(
            totalCommands = totalCommands,
            unreconciledCount = unreconciledCommands.size,
            needsReconciliation = unreconciledCommands.isNotEmpty()
        )
    }
}