package com.plstravels.driver.data.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room entity for user data
 */
@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey
    val id: Int,
    val username: String,
    val fullName: String,
    val phone: String,
    val email: String?,
    val branchId: Int?,
    val branchName: String?,
    val status: String,
    val licenseNumber: String?,
    val aadharNumber: String?,
    val address: String?,
    val profilePhotoUrl: String?,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)