package com.plstravels.driver.data.repository

import com.plstravels.driver.data.local.CommandQueueDao
import com.plstravels.driver.data.local.DutyDao
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.network.ApiService
import com.plstravels.driver.utils.ProdLogger
import com.plstravels.driver.utils.CrashReportingManager
import com.google.gson.Gson
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
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
    private val dutyDao: DutyDao,
    private val logger: ProdLogger,
    private val crashReportingManager: CrashReportingManager
) {
    private val gson = Gson()
    
    companion object {
        private const val TAG = "CommandQueueRepository"
        private const val MAX_EXECUTION_TIME_MS = 30_000L // 30 seconds
        private const val CLEANUP_OLDER_THAN_DAYS = 7
    }
    
    /**
     * Initialize the repository and clean up any stuck commands
     * Should be called on app startup to handle restart robustness
     */
    suspend fun initialize() {
        logger.logOperation(TAG, "command_queue_initialization") {
            try {
                logger.d(TAG, "Initializing CommandQueueRepository")
                
                // Clean up any commands stuck in executing state after app restart
                val stuckCommands = commandQueueDao.getExecutingCommands()
                stuckCommands.forEach { command ->
                    commandQueueDao.updateCommandExecutionStatus(command.id, false)
                    logger.w(TAG, "Reset stuck command after app restart: ${command.type}",
                        mapOf("command_id" to command.id.toString(), "command_type" to command.type))
                }
                
                logger.logDatabaseOperation(TAG, "reset_stuck_commands", "queued_commands", stuckCommands.size)
                logger.i(TAG, "CommandQueueRepository initialized - reset ${stuckCommands.size} stuck commands")
                
                crashReportingManager.setSyncStatus("queue_initialized", 0)
            } catch (e: Exception) {
                logger.e(TAG, "Error during CommandQueueRepository initialization", throwable = e)
                crashReportingManager.recordDatabaseError("initialization", "queued_commands", e)
                throw e
            }
        }
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
                        // Max retries reached or shouldn't retry - move to dead letter queue
                        Log.e(TAG, "Command failed permanently: ${queuedCommand.type}")
                        moveToDeadLetterQueue(queuedCommand, result.error)
                    }
                    return false
                }
                
                is CommandResult.Conflict -> {
                    Log.w(TAG, "Command conflict: ${queuedCommand.type}, server data: ${result.serverData}")
                    handleConflictResolution(queuedCommand, result.serverData)
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
                // Max retries reached for exception - move to dead letter queue
                moveToDeadLetterQueue(queuedCommand, e.message ?: "Unknown exception")
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
                            // Never mutate primary keys - use proper reconciliation
                            val updatedDuty = localDuty.copy(
                                syncStatus = "SYNCED"
                                // TODO: Add serverId field for safe reconciliation
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
    
    /**
     * Handle conflict resolution based on command type and server data
     */
    private suspend fun handleConflictResolution(command: QueuedCommand, serverData: String) {
        Log.d(TAG, "Handling conflict for command: ${command.type}")
        
        try {
            when (command.type) {
                CommandType.START_DUTY -> handleStartDutyConflict(command, serverData)
                CommandType.END_DUTY -> handleEndDutyConflict(command, serverData)
                CommandType.UPDATE_LOCATION -> {
                    // Location conflicts are usually not critical - accept server state
                    Log.d(TAG, "Location update conflict - accepting server state")
                    commandQueueDao.deleteCommand(command.id)
                }
                CommandType.UPLOAD_PHOTO -> {
                    // NOTE: This path is currently unreachable since parseCommand returns null for UPLOAD_PHOTO
                    // Photo uploads are delegated to PhotoUploadService - this is here for completeness
                    Log.w(TAG, "UPLOAD_PHOTO conflict handling - may be unreachable due to delegation")
                    handlePhotoUploadConflict(command, serverData)
                }
                else -> {
                    // Default conflict resolution - move to dead letter queue for manual review
                    Log.w(TAG, "Unknown conflict type for ${command.type} - moving to dead letter queue")
                    moveToDeadLetterQueue(command, "Conflict: $serverData")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error handling conflict for command ${command.id}", e)
            moveToDeadLetterQueue(command, "Conflict resolution error: ${e.message}")
        }
    }
    
    /**
     * Handle START_DUTY command conflicts
     */
    private suspend fun handleStartDutyConflict(command: QueuedCommand, serverData: String) {
        try {
            // Parse server duty state
            val serverDutyData = gson.fromJson(serverData, Map::class.java) as Map<String, Any>
            val serverDutyId = serverDutyData["dutyId"] as? String
            val serverStatus = serverDutyData["status"] as? String
            
            when (serverStatus) {
                "ACTIVE" -> {
                    // Server already has an active duty - update local state to match
                    Log.d(TAG, "Server already has active duty $serverDutyId - syncing local state")
                    
                    // Update local duty to match server state if possible
                    command.tempEntityId?.let { tempId ->
                        val tempIdHash = tempId.hashCode()
                        val localDuty = dutyDao.getDutyById(tempIdHash)
                        if (localDuty != null && serverDutyId != null) {
                            // Never mutate primary keys - use serverId field instead
                            val syncedDuty = localDuty.copy(
                                syncStatus = "SYNCED"
                                // TODO: Add serverId field to Duty entity for proper reconciliation
                            )
                            dutyDao.updateDuty(syncedDuty)
                            
                            // Mark as reconciled and delete command
                            commandQueueDao.updateCommandReconciliation(command.id, serverDutyId)
                            commandQueueDao.deleteCommand(command.id)
                            Log.d(TAG, "Successfully reconciled conflicted duty: $tempId -> $serverDutyId")
                        } else {
                            // Cannot reconcile - move to dead letter queue
                            moveToDeadLetterQueue(command, "Cannot reconcile duty - server duty $serverDutyId conflicts with local $tempId")
                        }
                    }
                }
                "REJECTED", "DENIED" -> {
                    // Server rejected the duty start - rollback local state
                    Log.w(TAG, "Server rejected duty start - rolling back local duty")
                    rollbackLocalDuty(command)
                    commandQueueDao.deleteCommand(command.id)
                }
                else -> {
                    // Unknown server state - move to dead letter queue for manual review
                    moveToDeadLetterQueue(command, "Unknown server duty status: $serverStatus")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing START_DUTY conflict", e)
            moveToDeadLetterQueue(command, "START_DUTY conflict processing error: ${e.message}")
        }
    }
    
    /**
     * Handle END_DUTY command conflicts
     */
    private suspend fun handleEndDutyConflict(command: QueuedCommand, serverData: String) {
        try {
            // Parse server response
            val serverResponse = gson.fromJson(serverData, Map::class.java) as Map<String, Any>
            val conflictType = serverResponse["conflictType"] as? String
            
            when (conflictType) {
                "DUTY_NOT_FOUND" -> {
                    // Server doesn't have this duty - local state may be stale
                    Log.w(TAG, "Server doesn't have duty to end - cleaning up local state")
                    command.tempEntityId?.let { dutyId ->
                        dutyDao.deleteDutyById(dutyId.toIntOrNull() ?: dutyId.hashCode())
                    }
                    commandQueueDao.deleteCommand(command.id)
                }
                "DUTY_ALREADY_ENDED" -> {
                    // Duty already ended on server - sync the end time
                    Log.d(TAG, "Duty already ended on server - syncing local state")
                    val serverEndTime = (serverResponse["endTime"] as? Number)?.toLong()
                    syncLocalDutyEndTime(command, serverEndTime)
                    commandQueueDao.deleteCommand(command.id)
                }
                else -> {
                    moveToDeadLetterQueue(command, "END_DUTY conflict: $conflictType")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing END_DUTY conflict", e)
            moveToDeadLetterQueue(command, "END_DUTY conflict processing error: ${e.message}")
        }
    }
    
    /**
     * Handle photo upload conflicts
     */
    private suspend fun handlePhotoUploadConflict(command: QueuedCommand, serverData: String) {
        try {
            val conflictData = gson.fromJson(serverData, Map::class.java) as Map<String, Any>
            val conflictReason = conflictData["reason"] as? String
            
            when (conflictReason) {
                "DUPLICATE_PHOTO" -> {
                    // Photo already exists on server - consider it uploaded
                    Log.d(TAG, "Photo already exists on server - marking as completed")
                    commandQueueDao.deleteCommand(command.id)
                }
                "INVALID_DUTY" -> {
                    // Photo belongs to invalid duty - move to dead letter queue
                    moveToDeadLetterQueue(command, "Photo upload failed - invalid duty")
                }
                else -> {
                    // Unknown photo conflict - retry with different strategy or move to dead letter
                    moveToDeadLetterQueue(command, "Photo upload conflict: $conflictReason")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing photo upload conflict", e)
            moveToDeadLetterQueue(command, "Photo upload conflict processing error: ${e.message}")
        }
    }
    
    /**
     * Move command to dead letter queue for manual resolution
     */
    private suspend fun moveToDeadLetterQueue(command: QueuedCommand, reason: String) {
        try {
            // TODO: Add isDeadLetter boolean field to QueuedCommand for proper DLQ handling
            val deadLetterCommand = command.copy(
                id = "dlq_${command.id}", // Temporary solution - should use boolean field
                lastError = "DEAD_LETTER: $reason",
                isExecuting = false,
                retryCount = command.maxRetries + 1 // Mark as exceeded retries
            )
            
            // Insert into dead letter queue (using same table with different ID prefix)
            commandQueueDao.insertCommand(deadLetterCommand)
            
            // Delete original command
            commandQueueDao.deleteCommand(command.id)
            
            Log.w(TAG, "Moved command ${command.id} to dead letter queue: $reason")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error moving command to dead letter queue", e)
            // Last resort - just delete the command to prevent infinite loops
            commandQueueDao.deleteCommand(command.id)
        }
    }
    
    /**
     * Rollback local duty state when server rejects
     */
    private suspend fun rollbackLocalDuty(command: QueuedCommand) {
        try {
            command.tempEntityId?.let { tempId ->
                val tempIdHash = tempId.hashCode()
                val localDuty = dutyDao.getDutyById(tempIdHash)
                if (localDuty != null) {
                    // Mark duty as cancelled/failed instead of deleting to preserve history
                    val rolledBackDuty = localDuty.copy(
                        status = "CANCELLED",
                        syncStatus = "REJECTED",
                        endTime = System.currentTimeMillis()
                    )
                    dutyDao.updateDuty(rolledBackDuty)
                    Log.d(TAG, "Rolled back local duty $tempId to CANCELLED status")
                } else {
                    Log.w(TAG, "Could not find local duty to rollback: $tempId")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error rolling back local duty", e)
        }
    }
    
    /**
     * Sync local duty end time with server
     */
    private suspend fun syncLocalDutyEndTime(command: QueuedCommand, serverEndTime: Long?) {
        try {
            command.tempEntityId?.let { dutyId ->
                val localDuty = dutyDao.getDutyById(dutyId.toIntOrNull() ?: dutyId.hashCode())
                if (localDuty != null && serverEndTime != null) {
                    val syncedDuty = localDuty.copy(
                        endTime = serverEndTime,
                        status = "COMPLETED",
                        syncStatus = "SYNCED"
                    )
                    dutyDao.updateDuty(syncedDuty)
                    Log.d(TAG, "Synced local duty end time with server: $dutyId")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error syncing duty end time", e)
        }
    }
    
    /**
     * Get dead letter queue commands for admin review
     * TODO: This should use a proper isDeadLetter boolean field instead of ID prefix
     */
    fun getDeadLetterQueueCommands(): Flow<List<QueuedCommand>> {
        return commandQueueDao.getAllCommandsFlow().map { allCommands ->
            allCommands.filter { it.id.startsWith("dlq_") }
        }
    }
    
    /**
     * Get dead letter queue statistics for admin dashboard
     */
    suspend fun getDeadLetterQueueStats(): DeadLetterQueueStats {
        val dlqCommands = commandQueueDao.getAllCommandsFlow().first().filter { it.id.startsWith("dlq_") }
        
        return DeadLetterQueueStats(
            totalCount = dlqCommands.size,
            byCommandType = dlqCommands.groupBy { it.type }.mapValues { it.value.size },
            oldestTimestamp = dlqCommands.minOfOrNull { it.timestamp },
            newestTimestamp = dlqCommands.maxOfOrNull { it.timestamp }
        )
    }
    
    /**
     * Retry command from dead letter queue
     */
    suspend fun retryFromDeadLetterQueue(deadLetterCommandId: String): Result<String> {
        return try {
            val dlqCommand = commandQueueDao.getCommandById(deadLetterCommandId)
            if (dlqCommand != null && dlqCommand.id.startsWith("dlq_")) {
                // Create new command with original ID and reset retry count
                val originalId = dlqCommand.id.removePrefix("dlq_")
                val retryCommand = dlqCommand.copy(
                    id = originalId,
                    retryCount = 0,
                    lastError = null,
                    isExecuting = false
                )
                
                // Insert retry command and delete dead letter entry
                commandQueueDao.insertCommand(retryCommand)
                commandQueueDao.deleteCommand(deadLetterCommandId)
                
                Log.d(TAG, "Retrying command from dead letter queue: $originalId")
                Result.success("Command moved back to active queue")
            } else {
                Result.failure(Exception("Dead letter command not found"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error retrying command from dead letter queue", e)
            Result.failure(e)
        }
    }
}

/**
 * Statistics for dead letter queue monitoring
 */
data class DeadLetterQueueStats(
    val totalCount: Int,
    val byCommandType: Map<CommandType, Int>,
    val oldestTimestamp: Long?,
    val newestTimestamp: Long?
)

/**
 * Reconciliation status for commands
 */
data class ReconciliationStatus(
    val totalCommands: Int,
    val unreconciledCount: Int,
    val needsReconciliation: Boolean
)