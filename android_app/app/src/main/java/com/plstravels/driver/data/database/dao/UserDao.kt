package com.plstravels.driver.data.database.dao

import androidx.room.*
import com.plstravels.driver.data.database.entity.UserEntity

/**
 * Room DAO for user operations
 */
@Dao
interface UserDao {
    
    @Query("SELECT * FROM users WHERE id = :userId")
    suspend fun getUserById(userId: Int): UserEntity?
    
    @Query("SELECT * FROM users WHERE username = :username")
    suspend fun getUserByUsername(username: String): UserEntity?
    
    @Query("SELECT * FROM users WHERE phone = :phone")
    suspend fun getUserByPhone(phone: String): UserEntity?
    
    @Query("SELECT * FROM users")
    suspend fun getAllUsers(): List<UserEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertUser(user: UserEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertUsers(users: List<UserEntity>)
    
    @Update
    suspend fun updateUser(user: UserEntity)
    
    @Delete
    suspend fun deleteUser(user: UserEntity)
    
    @Query("DELETE FROM users WHERE id = :userId")
    suspend fun deleteUserById(userId: Int)
    
    @Query("DELETE FROM users")
    suspend fun deleteAllUsers()
    
    @Query("UPDATE users SET updatedAt = :timestamp WHERE id = :userId")
    suspend fun updateTimestamp(userId: Int, timestamp: Long = System.currentTimeMillis())
}