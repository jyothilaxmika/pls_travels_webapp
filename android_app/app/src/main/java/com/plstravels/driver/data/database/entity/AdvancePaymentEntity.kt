package com.plstravels.driver.data.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room entity for advance payment requests
 */
@Entity(tableName = "advance_payments")
data class AdvancePaymentEntity(
    @PrimaryKey
    val id: String,
    val dutyId: Int,
    val amountRequested: Double,
    val amountApproved: Double?,
    val purpose: String,
    val notes: String?,
    val status: String, // "PENDING", "APPROVED", "REJECTED"
    val latitude: Double?,
    val longitude: Double?,
    val createdAt: Long,
    val respondedAt: Long?,
    val responseNotes: String?,
    val isSynced: Boolean = false
)