package com.plstravels.driver.data.local

import androidx.room.*
import com.plstravels.driver.data.models.Notification
import com.plstravels.driver.data.models.NotificationType
import com.plstravels.driver.data.models.NotificationPriority
import kotlinx.coroutines.flow.Flow

/**
 * Room DAO for notification management
 */
@Dao
interface NotificationDao {
    
    @Query("SELECT * FROM notifications ORDER BY timestamp DESC")
    fun getAllNotifications(): Flow<List<Notification>>
    
    @Query("SELECT * FROM notifications WHERE isRead = 0 ORDER BY priority DESC, timestamp DESC")
    fun getUnreadNotifications(): Flow<List<Notification>>
    
    @Query("SELECT * FROM notifications WHERE type = :type ORDER BY timestamp DESC LIMIT :limit")
    fun getNotificationsByType(type: NotificationType, limit: Int = 50): Flow<List<Notification>>
    
    @Query("SELECT * FROM notifications WHERE dutyId = :dutyId ORDER BY timestamp DESC")
    fun getNotificationsForDuty(dutyId: Int): Flow<List<Notification>>
    
    @Query("SELECT * FROM notifications WHERE priority = :priority AND isRead = 0 ORDER BY timestamp DESC")
    fun getNotificationsByPriority(priority: NotificationPriority): Flow<List<Notification>>
    
    @Query("SELECT COUNT(*) FROM notifications WHERE isRead = 0")
    suspend fun getUnreadCount(): Int
    
    @Query("SELECT COUNT(*) FROM notifications WHERE isRead = 0 AND priority IN (:priorities)")
    suspend fun getUnreadCountByPriority(priorities: List<NotificationPriority>): Int
    
    @Query("SELECT * FROM notifications WHERE id = :notificationId")
    suspend fun getNotificationById(notificationId: Long): Notification?
    
    @Query("SELECT * FROM notifications WHERE notificationId = :notificationId")
    suspend fun getNotificationByExternalId(notificationId: String): Notification?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertNotification(notification: Notification): Long
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertNotifications(notifications: List<Notification>)
    
    @Update
    suspend fun updateNotification(notification: Notification)
    
    @Query("UPDATE notifications SET isRead = 1, readAt = :readAt WHERE id = :notificationId")
    suspend fun markAsRead(notificationId: Long, readAt: Long = System.currentTimeMillis())
    
    @Query("UPDATE notifications SET isRead = 1, readAt = :readAt WHERE id IN (:notificationIds)")
    suspend fun markMultipleAsRead(notificationIds: List<Long>, readAt: Long = System.currentTimeMillis())
    
    @Query("UPDATE notifications SET isRead = 1, readAt = :readAt")
    suspend fun markAllAsRead(readAt: Long = System.currentTimeMillis())
    
    @Query("UPDATE notifications SET isDisplayed = 1 WHERE id = :notificationId")
    suspend fun markAsDisplayed(notificationId: Long)
    
    @Delete
    suspend fun deleteNotification(notification: Notification)
    
    @Query("DELETE FROM notifications WHERE id = :notificationId")
    suspend fun deleteNotificationById(notificationId: Long)
    
    @Query("DELETE FROM notifications WHERE expiresAt IS NOT NULL AND expiresAt < :currentTime")
    suspend fun deleteExpiredNotifications(currentTime: Long = System.currentTimeMillis())
    
    @Query("DELETE FROM notifications WHERE timestamp < :cutoffTime AND isRead = 1")
    suspend fun deleteOldReadNotifications(cutoffTime: Long)
    
    @Query("DELETE FROM notifications WHERE type = :type")
    suspend fun deleteNotificationsByType(type: NotificationType)
    
    // Statistics and reporting queries
    @Query("SELECT COUNT(*) FROM notifications WHERE timestamp >= :startTime AND timestamp <= :endTime")
    suspend fun getNotificationCountByDateRange(startTime: Long, endTime: Long): Int
    
    @Query("SELECT type, COUNT(*) as count FROM notifications WHERE timestamp >= :startTime GROUP BY type")
    suspend fun getNotificationCountsByType(startTime: Long): Map<NotificationType, Int>
    
    @Query("SELECT * FROM notifications WHERE timestamp >= :startTime ORDER BY timestamp DESC")
    fun getNotificationsSince(startTime: Long): Flow<List<Notification>>
    
    @Query("SELECT DISTINCT senderId, senderName FROM notifications WHERE senderId IS NOT NULL ORDER BY senderName")
    suspend fun getUniqueSenders(): List<Pair<Int, String>>
}