package com.plstravels.driver.data.local

import androidx.room.*
import com.plstravels.driver.data.models.QueuedCommand
import com.plstravels.driver.data.models.CommandType
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for offline command queue operations
 */
@Dao
interface CommandQueueDao {
    
    /**
     * Insert a new command into the queue
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCommand(command: QueuedCommand)
    
    /**
     * Get all pending commands ordered by timestamp (oldest first)
     */
    @Query("SELECT * FROM command_queue WHERE isExecuting = 0 ORDER BY timestamp ASC")
    suspend fun getPendingCommands(): List<QueuedCommand>
    
    /**
     * Get pending commands by type
     */
    @Query("SELECT * FROM command_queue WHERE type = :type AND isExecuting = 0 ORDER BY timestamp ASC")
    suspend fun getPendingCommandsByType(type: CommandType): List<QueuedCommand>
    
    /**
     * Get commands that are currently executing
     */
    @Query("SELECT * FROM command_queue WHERE isExecuting = 1")
    suspend fun getExecutingCommands(): List<QueuedCommand>
    
    /**
     * Get total count of pending commands
     */
    @Query("SELECT COUNT(*) FROM command_queue WHERE isExecuting = 0")
    fun getPendingCommandCount(): Flow<Int>
    
    /**
     * Update command execution status
     */
    @Query("UPDATE command_queue SET isExecuting = :isExecuting WHERE id = :commandId")
    suspend fun updateCommandExecutionStatus(commandId: String, isExecuting: Boolean)
    
    /**
     * Update command retry count and last error
     */
    @Query("UPDATE command_queue SET retryCount = :retryCount, lastError = :lastError WHERE id = :commandId")
    suspend fun updateCommandRetry(commandId: String, retryCount: Int, lastError: String?)
    
    /**
     * Update command reconciliation info
     */
    @Query("UPDATE command_queue SET serverEntityId = :serverId, isReconciled = 1 WHERE id = :commandId")
    suspend fun updateCommandReconciliation(commandId: String, serverId: String)
    
    /**
     * Get commands by idempotency key to prevent duplicates
     */
    @Query("SELECT * FROM command_queue WHERE idempotencyKey = :key LIMIT 1")
    suspend fun getCommandByIdempotencyKey(key: String): QueuedCommand?
    
    /**
     * Get unreconciled commands for ID mapping
     */
    @Query("SELECT * FROM command_queue WHERE isReconciled = 0 AND serverEntityId IS NULL AND tempEntityId IS NOT NULL")
    suspend fun getUnreconciledCommands(): List<QueuedCommand>
    
    /**
     * Delete a command from the queue
     */
    @Query("DELETE FROM command_queue WHERE id = :commandId")
    suspend fun deleteCommand(commandId: String)
    
    /**
     * Delete commands that have exceeded max retries
     */
    @Query("DELETE FROM command_queue WHERE retryCount >= maxRetries")
    suspend fun deleteFailedCommands()
    
    /**
     * Delete all commands older than specified timestamp
     */
    @Query("DELETE FROM command_queue WHERE timestamp < :timestamp")
    suspend fun deleteOldCommands(timestamp: Long)
    
    /**
     * Clear all commands (for testing or reset)
     */
    @Query("DELETE FROM command_queue")
    suspend fun clearAllCommands()
    
    /**
     * Get commands by execution status for monitoring
     */
    @Query("SELECT * FROM command_queue ORDER BY timestamp DESC")
    fun getAllCommandsFlow(): Flow<List<QueuedCommand>>
    
    /**
     * Get commands that need reconciliation mapping
     */
    @Query("SELECT * FROM command_queue WHERE tempEntityId IS NOT NULL AND serverEntityId IS NULL")
    fun getCommandsNeedingReconciliation(): Flow<List<QueuedCommand>>
}